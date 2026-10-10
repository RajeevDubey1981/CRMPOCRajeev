"""The only place where the Sales module reads from, or writes to, the CRM database. Everything goes through
the application with a CRM session; nothing is joined across the two databases, and Sales keeps only reference
numbers (a user id, an enquiry number) and a copy of what it needs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatusLog
from app.models.item_master import ItemMaster
from app.models.partner_registration import PartnerRegistration
from app.models.user import User
from app.sales.rules import INCORPORATION_BUSINESS_TYPES
from app.services import pending_action_service as pas
from app.services.partner_registration import (
    CSD_PARTNER_TYPE,
    PARTNER_ADMIN_ROLES,
    gem_seller_id_required,
    required_shop_photo_count,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------- people ----------------
def sales_users(main_db: Session) -> list[User]:
    return list(
        main_db.scalars(
            select(User).where(
                User.deleted_at.is_(None),
                func.lower(func.trim(User.role)).in_(("sales", "sales_manager")),
            ).order_by(User.name)
        )
    )


def user_basics(main_db: Session, user_id: int | None) -> dict | None:
    if not user_id:
        return None
    u = main_db.get(User, user_id)
    if u is None:
        return None
    return {"id": u.id, "name": u.name, "role": u.role, "email": u.email, "phone": u.phone, "active": bool(u.is_active) and u.deleted_at is None}


def user_names(main_db: Session, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u.name for u in main_db.scalars(select(User).where(User.id.in_(ids)))}


def partner_admins(main_db: Session) -> list[User]:
    return pas.get_users_by_roles(main_db, set(PARTNER_ADMIN_ROLES))


# ---------------- enquiries ----------------
def max_complaint_id(main_db: Session) -> int:
    return main_db.scalar(select(func.max(Complaint.id))) or 0


def max_partner_id(main_db: Session) -> int:
    return main_db.scalar(select(func.max(PartnerRegistration.id))) or 0


def sales_complaints(main_db: Session, *, after_id: int = 0, since: datetime | None = None) -> list[Complaint]:
    stmt = select(Complaint).where(
        Complaint.deleted_at.is_(None), func.lower(func.trim(Complaint.query_type)) == "sales", Complaint.id > after_id
    )
    if since is not None:
        stmt = stmt.where(Complaint.created_at >= since)
    return list(main_db.scalars(stmt.order_by(Complaint.id)))


def partner_registrations(main_db: Session, *, after_id: int = 0, since: datetime | None = None) -> list[PartnerRegistration]:
    """Registrations the partner has started (an invite nobody opened yet is not a lead)."""
    stmt = select(PartnerRegistration).where(
        PartnerRegistration.id > after_id,
        PartnerRegistration.onboarding_status.notin_(("Invite Sent", "Cancelled")),
    )
    if since is not None:
        stmt = stmt.where(PartnerRegistration.created_at >= since)
    return list(main_db.scalars(stmt.order_by(PartnerRegistration.id)))


def get_partner(main_db: Session, registration_no: str) -> PartnerRegistration | None:
    return main_db.scalar(select(PartnerRegistration).where(PartnerRegistration.registration_no == registration_no))


def get_complaint(main_db: Session, comp_no: str) -> Complaint | None:
    return main_db.scalar(select(Complaint).where(Complaint.comp_no == comp_no))


def close_complaint(main_db: Session, comp_no: str, *, won: bool, note: str, by: User) -> bool:
    """Close the original enquiry with the same result. Returns False when the CRM did not take it."""
    c = get_complaint(main_db, comp_no)
    if c is None:
        return False
    old = c.status
    new = "Resolved" if won else "Rejected"
    if old != new:
        c.status = new
        c.status_date = _now()
        main_db.add(ComplaintStatusLog(
            complaint_id=c.id, old_status=old, new_status=new, changed_by=by.id,
            remark=(f"Closed from Sales: {note}" if note else "Closed from Sales"),
        ))
    main_db.flush()
    try:
        from app.services.pending_action_sync import sync_complaint_pending_actions
        sync_complaint_pending_actions(main_db, c)
    except Exception:  # the cards are a courtesy; the close itself must not fail because of them
        pass
    return True


# ---------------- partner registration papers: the CRM's own rules ----------------
def partner_papers(reg: PartnerRegistration) -> list[dict]:
    """The papers this registration needs, and which of them the CRM has. Read each time, never copied."""

    def have(field: str) -> bool:
        return bool((getattr(reg, field, None) or "").strip())

    items: list[dict] = []
    needs_deed = (reg.business_type or "") in INCORPORATION_BUSINESS_TYPES
    spec = (
        ("gst_certificate", "GST Registration Certificate", True, ""),
        ("pan_card", "PAN Card (entity or proprietor)", True, ""),
        ("cancelled_cheque", "Cancelled Cheque or Bank Statement", True, ""),
        ("address_proof", "Address Proof (utility bill or rent deed)", True, ""),
        ("aadhaar_card", "Aadhaar Card of the authorised signatory", True, ""),
        ("incorporation_certificate", "Incorporation or Partnership Deed", needs_deed, f"needed for a {reg.business_type}" if needs_deed else ""),
        ("msme_certificate", "MSME or Udyam Certificate", False, ""),
        ("photo", "Passport size photograph", False, ""),
    )
    for key, label, required, note in spec:
        items.append({"key": key, "label": label, "required": required, "ok": have(f"{key}_path"), "note": note})
    n = required_shop_photo_count(reg.partner_type)
    got = sum(1 for i in range(1, 6) if have(f"shop_photo_{i}_path"))
    items.append({
        "key": "shop_photos", "label": "Shop photographs", "required": True, "ok": got >= n,
        "note": f"{got} of {n} received" + (" (a CSD Dealer needs 5)" if n > 1 else ""),
    })
    if gem_seller_id_required(reg.partner_type):
        items.append({"key": "gem_seller_id", "label": "GeM Seller ID", "required": True, "ok": bool((reg.gem_seller_id or "").strip()), "note": "needed for a Gem Partner"})
    items.append({"key": "gstin", "label": "GSTIN given", "required": True, "ok": bool((reg.gst_no or "").strip()), "note": ""})
    items.append({"key": "bank", "label": "Bank details filled in", "required": True, "ok": bool(reg.bank_name and reg.account_number and reg.ifsc_code), "note": ""})
    items.append({"key": "declaration", "label": "Declaration accepted by the partner", "required": True, "ok": bool(reg.declaration_accepted), "note": ""})
    return items


PARTNER_STEPS = (
    "Invite Sent", "In Progress", "Registration Submitted", "Documents Verification", "Admin Review",
    "Onboarding Approved", "Partner Active",
)
PARTNER_LEAD_STATUS = {
    "Invite Sent": "new", "In Progress": "con", "Registration Submitted": "int", "Documents Verification": "int",
    "Admin Review": "int", "Onboarding Approved": "won", "Partner Active": "won", "Rejected": "con", "Cancelled": "dis",
}


def partner_summary(reg: PartnerRegistration) -> dict:
    items = partner_papers(reg)
    req = [i for i in items if i["required"]]
    return {
        "registration_no": reg.registration_no,
        "partner_type": reg.partner_type,
        "business_type": reg.business_type,
        "onboarding_status": reg.onboarding_status,
        "form_status": reg.form_status,
        "admin_remark": reg.admin_remark,
        "steps": list(PARTNER_STEPS),
        "papers": items,
        "required_total": len(req),
        "required_done": sum(1 for i in req if i["ok"]),
        "reminder_used": bool(reg.email_resend_used),
    }


def remind_partner(main_db: Session, reg: PartnerRegistration) -> tuple[bool, str]:
    """Use the CRM's own invite mail, once per registration (the CRM's rule)."""
    from app.services.email_service import send_partner_registration_invite_email
    from app.services.partner_registration import build_public_registration_url

    if reg.onboarding_status in {"Cancelled", "Onboarding Approved", "Partner Active"}:
        return False, "This registration is closed"
    if reg.email_resend_used:
        return False, "The CRM allows one reminder mail per registration. Please call the partner."
    send_partner_registration_invite_email(
        to=reg.email, contact_person_name=reg.contact_person_name, firm_name=reg.name,
        registration_no=reg.registration_no, registration_url=build_public_registration_url(reg.access_token),
    )
    reg.email_resend_used = True
    main_db.flush()
    return True, "Reminder sent through the CRM mail"


# ---------------- items for quotations ----------------
def item_search(main_db: Session, q: str = "", limit: int = 30) -> list[dict]:
    stmt = select(ItemMaster).where(ItemMaster.deleted_at.is_(None), ItemMaster.is_active.is_(True))
    q = (q or "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(ItemMaster.item_code.ilike(like), ItemMaster.item_name.ilike(like)))
    rows = main_db.scalars(stmt.order_by(ItemMaster.item_name).limit(limit))
    return [
        {"item_code": r.item_code, "item_name": r.item_name, "hsn": r.hsn_code, "mrp": float(r.mrp or 0), "category": r.category}
        for r in rows
    ]


def get_item(main_db: Session, item_code: str) -> dict | None:
    r = main_db.scalar(select(ItemMaster).where(ItemMaster.item_code == item_code))
    if r is None:
        return None
    return {"item_code": r.item_code, "item_name": r.item_name, "hsn": r.hsn_code, "mrp": float(r.mrp or 0), "category": r.category}


# ---------------- the login popup ----------------
def push_card(main_db: Session, *, user_id: int, lead_id: int, lead_no: str, action_type: str, title: str, message: str,
              label: str, status: str, due_at: datetime | None = None) -> None:
    pas.upsert_pending_action(
        main_db, recipient_user_id=user_id, module="sales", entity_id=lead_id, entity_ref=lead_no or "",
        action_type=action_type, title=title, message=message, action_label=label,
        href=f"/sales/leads/{lead_id}", entity_status=status, due_at=due_at,
    )


def resolve_cards(main_db: Session, lead_id: int, action_types: list[str] | None = None) -> None:
    pas.resolve_pending_actions(main_db, module="sales", entity_id=lead_id, action_types=action_types)


def notify_partner_admins(main_db: Session, *, lead_id: int, lead_no: str, title: str, message: str, action_type: str) -> int:
    admins = partner_admins(main_db)
    pas.notify_users(
        main_db, admins, module="sales", entity_id=lead_id, entity_ref=lead_no or "", action_type=action_type,
        title=title, message=message, action_label="Open the registration", href="/partner-registrations",
        entity_status="open",
    )
    return len(admins)


# ---------------- registering an enquiry that came from a connection ----------------
def register_enquiry(main_db: Session, *, name: str, mobile: str, email: str | None, message: str, address: str | None,
                     state: str | None, source_key: str, source_label: str) -> Complaint:
    """Registered first: an enquiry that comes in from IndiaMART, Meta or a web address is first registered in the CRM
    as a Sales enquiry (an IDC_ number, as for a website enquiry). No SMS or mail is sent to the customer."""
    import secrets
    import time
    from datetime import date

    n = int(time.time() * 1000)
    while main_db.scalar(select(Complaint.id).where(Complaint.comp_no == f"IDC_{n}")):
        n += 1
    c = Complaint(
        comp_no=f"IDC_{n}", comp_date=date.today(), customer_name=(name or "Unknown")[:255], customer_mobile=(mobile or "")[:20],
        customer_email=(email or None), customer_address=(address or None), state=((state or "")[:100] or None),
        problem_description=(message or "-"), query_type="Sales", send_sms=False, access_code=f"{secrets.randbelow(1_000_000):06d}",
        status="Pending", created_by=None, source=(source_key or "connection")[:50],
    )
    main_db.add(c)
    main_db.flush()
    main_db.add(ComplaintStatusLog(complaint_id=c.id, old_status=None, new_status="Pending", changed_by=None, remark=f"Registered from {source_label} (Sales)"))
    main_db.flush()
    return c
