"""Lead operations of the Sales module. Works on the Sales database, and reaches the CRM only through crm_link."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from app.models.user import User
from app.sales import crm_link
from app.sales import types as T
from app.sales.models import SalesLead, SalesLeadActivity, SalesProfile, SalesSetting
from app.sales.rules import (
    CLOSED_STATUSES, CRM_ONLY_DISPOSALS, DISPOSALS, GOOD_DISPOSALS, PRIORITIES,
    detect_lead_type, heat_from_text, suggest_heat, suggest_priority,
)

FIRST_CALL_HOURS = 2
STATUS_LABEL = {"new": "New", "con": "Contacted", "int": "Interested", "quo": "Quote sent", "neg": "Negotiation", "won": "Won", "dis": "Disposed", "rev": "Waiting for the manager"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def bad(msg: str, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(code, msg)


# ---------------- settings ----------------
SETTING_DEFAULTS = {
    "fx_rate": "88", "discount_limit": "10", "home_state": "Uttar Pradesh", "company_name": "INDcool",
    "company_address": "OC528, Gaur City, Greater Noida West, Uttar Pradesh", "company_gstin": "",
}


def get_setting(sdb: Session, key: str, default: str | None = None) -> str:
    row = sdb.get(SalesSetting, key)
    if row is not None:
        return row.value
    return SETTING_DEFAULTS.get(key, default if default is not None else "")


def set_setting(sdb: Session, key: str, value: str) -> None:
    row = sdb.get(SalesSetting, key)
    if row is None:
        sdb.add(SalesSetting(key=key, value=str(value)))
    else:
        row.value = str(value)


# ---------------- small helpers ----------------
def norm_phone(value: str | None) -> str:
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+") or raw.startswith("00"):
        full = digits[2:] if raw.startswith("00") else digits
        # an Indian number written with +91 is the same person as the 10 digit number
        return full[-10:] if full.startswith("91") and len(full) == 12 else "+" + full
    return digits[-10:] if len(digits) > 10 else digits


def jdump(items) -> str:
    return json.dumps(items, ensure_ascii=False)


def jload(text: str | None) -> list:
    try:
        return json.loads(text) if text else []
    except (TypeError, ValueError):
        return []


# What the person who has the lead does about it. Any of these marks the lead as attended.
ATTEND_KINDS = frozenset({"call", "note", "rating", "stage", "quotation", "priority", "disposal"})
STAGE_ORDER = {"new": 0, "con": 1, "int": 2, "quo": 3, "neg": 4}
MANUAL_STAGES = ("con", "int", "quo", "neg")
# what a call outcome means for the stage (a stage only moves forward by a call)
OUTCOME_STAGE = {
    "Spoke: interested": "int", "Spoke: needs a quote": "int", "Spoke: will think and call back": "con",
    "No answer": "con", "Phone switched off": "con", "Sent a WhatsApp or mail": "con", "Visit done": "con", "Sent a WhatsApp": "con", "Sent a mail": "con",
}
NO_ANSWER = ("No answer", "Phone switched off")


def log(sdb: Session, lead: SalesLead, kind: str, text: str, user: User | None = None) -> None:
    sdb.add(SalesLeadActivity(
        lead_id=lead.id, kind=kind, text=text, by_user_id=user.id if user else None, by_name=user.name if user else "automatic",
    ))
    if user is not None and kind in ATTEND_KINDS and user.id == lead.owner_user_id:
        lead.last_action_at = now()
        lead.last_action_by = user.id


def set_follow_up(sdb: Session, lead: SalesLead, *, day: date, user: User) -> None:
    """Move the follow-up date of a lead (from the calendar). Written in the history; it counts as attending only for the owner."""
    if is_closed(lead):
        raise HTTPException(400, "This lead is closed")
    old = lead.follow_up_on
    lead.follow_up_on = day
    log(sdb, lead, "note", f"Follow-up moved from {old.strftime('%d %b %Y') if old else 'no date'} to {day.strftime('%d %b %Y')}", user)


def is_closed(lead: SalesLead) -> bool:
    return lead.status in CLOSED_STATUSES


# ---------------- profiles ----------------
def ensure_profile(sdb: Session, user: User) -> SalesProfile:
    p = sdb.scalar(select(SalesProfile).where(SalesProfile.crm_user_id == user.id))
    if p is None:
        p = SalesProfile(crm_user_id=user.id, name_cache=user.name, role_cache=user.role, phone=user.phone)
        sdb.add(p)
        sdb.flush()
    else:
        p.name_cache = user.name
        p.role_cache = user.role
        p.is_active = bool(user.is_active) and user.deleted_at is None
    return p


def sync_profiles(main_db: Session, sdb: Session) -> list[SalesProfile]:
    out = [ensure_profile(sdb, u) for u in crm_link.sales_users(main_db)]
    sdb.flush()
    return out


def csv_list(text: str | None) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def pick_owner(sdb: Session, lead: SalesLead) -> int | None:
    """The team member who handles this lead type and covers the place; the one with the fewest open leads wins a tie."""
    members = [
        p for p in sdb.scalars(select(SalesProfile).where(SalesProfile.is_active.is_(True)))
        if (p.role_cache or "").strip().lower() == "sales"
    ]
    if not members:
        return None
    open_counts = dict(sdb.execute(
        select(SalesLead.owner_user_id, func.count()).where(SalesLead.status.notin_(tuple(CLOSED_STATUSES))).group_by(SalesLead.owner_user_id)
    ).all())
    place_keys = {x.lower() for x in (lead.state, lead.country, lead.district) if x}

    def score(p: SalesProfile):
        types = csv_list(p.types_handled)
        type_match = 2 if lead.lead_type in types else (1 if not types else 0)
        areas = {a.lower() for a in csv_list(p.areas)} | ({p.state.lower()} if p.state else set())
        area_match = 1 if place_keys & areas else 0
        return (type_match, area_match, -open_counts.get(p.crm_user_id, 0))

    best = max(members, key=score)
    if score(best)[0] == 0:
        return None
    return best.crm_user_id


# ---------------- creating a lead ----------------
def _apply_scores(lead: SalesLead, answers: dict | None = None, *, forced_heat: tuple[str, list[str]] | None = None) -> None:
    if forced_heat:
        lead.heat, why = forced_heat
        lead.heat_why = jdump(why)
        lead.heat_by = "Suggested by the rules"
    else:
        level, why, _ = suggest_heat(answers or {})
        lead.heat = level
        lead.heat_why = jdump(why or ["New enquiry, nothing known yet"])
        lead.heat_by = "Suggested by the rules"
    refresh_priority(lead, force=True)


def refresh_priority(lead: SalesLead, *, force: bool = False) -> None:
    manual = bool(lead.priority_by) and not lead.priority_by.startswith("Suggested")
    if manual and not force:
        return
    late = bool(lead.follow_up_on and lead.follow_up_on < date.today() and not is_closed(lead))
    level, why, _ = suggest_priority(
        value_lakh=float(lead.value_lakh or 0), closes_on=lead.closes_on, lead_type=lead.lead_type, heat=lead.heat,
        follow_up_late=late, source=lead.source,
    )
    lead.priority = level
    lead.priority_why = jdump(why)
    lead.priority_by = "Suggested by the rules"


def find_open_duplicate(sdb: Session, phone: str) -> SalesLead | None:
    key = norm_phone(phone)
    if not key:
        return None
    cutoff = now() - timedelta(days=30)
    for lead in sdb.scalars(select(SalesLead).where(SalesLead.phone == key, SalesLead.status.notin_(tuple(CLOSED_STATUSES))).order_by(SalesLead.id.desc())):
        if aware(lead.created_at) is None or aware(lead.created_at) >= cutoff:
            return lead
    return None


def create_lead(main_db: Session | None, sdb: Session, data: dict, created_by: User | None = None) -> tuple[SalesLead, bool]:
    name = (data.get("name") or "").strip()
    phone = norm_phone(data.get("phone"))
    if not name:
        bad("Write the name")
    if len(phone) < 7:
        bad("Write a phone number")
    text = " ".join(str(data.get(k) or "") for k in ("item", "message", "details"))
    source = data.get("source") or "Typed in"

    dup = find_open_duplicate(sdb, phone)
    if dup is not None and data.get("crm_kind") != "partner":
        dup.asked_again_at = now()
        log(sdb, dup, "system", f"Asked again from {source}" + (f" ({data.get('crm_ref')})" if data.get("crm_ref") else "") + (f": {data.get('message')}" if data.get("message") else ""))
        if main_db is not None and dup.owner_user_id:
            crm_link.push_card(
                main_db, user_id=dup.owner_user_id, lead_id=dup.id, lead_no=dup.lead_no or "", action_type="sales_asked_again",
                title="A lead asked again", message=f"{dup.name} asked again from {source}.", label="Open the lead", status=dup.status,
            )
        return dup, False

    lead_type = T.usable_type(sdb, data.get("lead_type") if T.valid_type(sdb, data.get("lead_type")) else detect_lead_type(text, data.get("channel", "")))
    lead = SalesLead(
        name=name, phone=phone, email=(data.get("email") or None), item=(data.get("item") or "")[:500], place=data.get("place"),
        state=data.get("state"), district=data.get("district"), pincode=data.get("pincode"), country=data.get("country"),
        source=source, channel=data.get("channel") or "hand", lead_type=lead_type, details=data.get("details"),
        message=data.get("message"), value_lakh=data.get("value_lakh"), value_usd=data.get("value_usd"),
        price_basis=data.get("price_basis"), closes_on=data.get("closes_on"), is_prospect=bool(data.get("is_prospect")),
        crm_kind=data.get("crm_kind"), crm_ref=data.get("crm_ref"), crm_id=data.get("crm_id"),
        created_by=created_by.id if created_by else None, status="new", first_call_due_at=now() + timedelta(hours=FIRST_CALL_HOURS),
    )
    sdb.add(lead)
    sdb.flush()
    lead.lead_no = f"SL-{now().year}-{lead.id:05d}"
    if data.get("heat") in ("hot", "warm", "cold"):
        _apply_scores(lead, forced_heat=(data["heat"], data.get("heat_why") or ["Suggested by the source"]))
    else:
        _apply_scores(lead, heat_from_text(text))
    owner = data.get("owner_user_id") or pick_owner(sdb, lead)
    lead.owner_user_id = owner
    if data.get("crm_ref"):
        log(sdb, lead, "system", f"Lead made by itself from {source}, registered in the CRM as {data['crm_ref']}")
    else:
        log(sdb, lead, "system", f"Lead added by hand ({source})", created_by)
    if owner:
        log(sdb, lead, "give", "Given by the rules (lead type, then place)" if not data.get("owner_user_id") else "Given to the owner")
        if main_db is not None:
            crm_link.push_card(
                main_db, user_id=owner, lead_id=lead.id, lead_no=lead.lead_no, action_type="sales_new_lead",
                title="New lead", message=f"{lead.name}: {lead.item or T.label_of(sdb, lead.lead_type)}. First call due in {FIRST_CALL_HOURS} hours.",
                label="Open the lead", status="new", due_at=lead.first_call_due_at,
            )
    return lead, True


# ---------------- working a lead ----------------
def give(main_db: Session | None, sdb: Session, lead: SalesLead, owner_id: int | None, by: User, owner_name: str = "") -> None:
    if is_closed(lead):
        bad("A closed lead cannot be given")
    old = lead.owner_user_id
    lead.owner_user_id = owner_id
    log(sdb, lead, "give", f"Given to {owner_name or owner_id}" if owner_id else "Taken back", by)
    if main_db is not None:
        if old and old != owner_id:
            crm_link.resolve_cards(main_db, lead.id, ["sales_new_lead", "sales_asked_again"])
        if owner_id:
            crm_link.push_card(
                main_db, user_id=owner_id, lead_id=lead.id, lead_no=lead.lead_no or "", action_type="sales_new_lead",
                title="A lead was given to you", message=f"{lead.name}: {lead.item}", label="Open the lead", status=lead.status,
                due_at=lead.first_call_due_at if not lead.first_called_at else None,
            )


def log_call(main_db: Session | None, sdb: Session, lead: SalesLead, *, outcome: str, note: str, next_follow_up: date | None, user: User) -> None:
    if is_closed(lead):
        bad("This lead is closed")
    outcome = (outcome or "Call").strip()
    text = outcome + (f". {note.strip()}" if (note or "").strip() else "")
    lead.attempts = (lead.attempts or 0) + 1
    if outcome in NO_ANSWER and not next_follow_up:
        next_follow_up = date.today() + timedelta(days=1)  # nobody picked up: try again tomorrow unless told otherwise
    log(sdb, lead, "call", text, user)
    lead.last_contact_at = now()
    if lead.first_called_at is None:
        lead.first_called_at = now()
        if main_db is not None:
            crm_link.resolve_cards(main_db, lead.id, ["sales_new_lead"])
    if lead.crm_kind != "partner":  # a partner registration lead follows the CRM, not the call
        target = OUTCOME_STAGE.get(outcome, "con")
        if lead.status == "new" or (lead.status in STAGE_ORDER and STAGE_ORDER[target] > STAGE_ORDER[lead.status]):
            lead.status = target
    lead.follow_up_on = next_follow_up or lead.follow_up_on
    refresh_priority(lead)


def set_stage(sdb: Session, lead: SalesLead, *, stage: str, note: str, user: User) -> None:
    """The person moves the lead along the workflow by hand: Contacted, Interested, Quote sent, Negotiation."""
    if lead.crm_kind == "partner":
        bad("A partner registration lead follows the CRM: its stage is set there")
    if is_closed(lead):
        bad("This lead is closed")
    if stage not in MANUAL_STAGES:
        bad("Choose a stage: Contacted, Interested, Quote sent or Negotiation")
    if stage == lead.status:
        bad("The lead is already at this stage")
    before = STATUS_LABEL.get(lead.status, lead.status)
    lead.status = stage
    if lead.first_called_at is None:
        lead.first_called_at = now()  # moving a new lead along counts as the first attention
    log(sdb, lead, "stage", f"Stage: {before} to {STATUS_LABEL[stage]}" + (f". {note.strip()}" if (note or "").strip() else ""), user)


def rate_lead(sdb: Session, lead: SalesLead, *, answers: dict, heat: str | None, why: str, user: User) -> None:
    level, reasons, _ = suggest_heat(answers)
    pick = heat if heat in ("hot", "warm", "cold") else level
    if pick != level and pick != lead.heat and len((why or "").strip()) < 5:
        bad("Write why you changed the suggestion")
    before = lead.heat
    lead.heat = pick
    lead.heat_why = jdump(reasons)
    lead.heat_by = "Suggested by the rules" if pick == level else f"Changed by {user.name}: {(why or '').strip() or 'kept as before'}"
    lead.rating_answers = jdump(answers)
    log(sdb, lead, "rating", f"Rated {pick.title()}" + (" (as suggested)" if pick == level else f" (the rules said {level.title()}; {(why or '').strip()})") + ("" if before != pick else " - unchanged"), user)
    refresh_priority(lead)


def set_priority(sdb: Session, lead: SalesLead, *, level: str, why: str, user: User, flag: bool) -> None:
    if level not in PRIORITIES:
        bad("Unknown priority")
    if flag and level != "high":
        bad("A team member can only flag a lead High")
    suggested, _w, _s = suggest_priority(
        value_lakh=float(lead.value_lakh or 0), closes_on=lead.closes_on, lead_type=lead.lead_type, heat=lead.heat,
        follow_up_late=bool(lead.follow_up_on and lead.follow_up_on < date.today()), source=lead.source,
    )
    if level != suggested and level != lead.priority and len((why or "").strip()) < 5:
        bad("Write why you changed the suggestion")
    before = lead.priority
    lead.priority = level
    lead.priority_why = jdump(_w)
    lead.priority_by = "Suggested by the rules" if level == suggested else f"{'Flagged High' if flag else 'Changed'} by {user.name}: {(why or '').strip() or 'kept as before'}"
    log(sdb, lead, "priority", f"Priority {before.title()} to {level.title()}" + (" (as suggested)" if level == suggested else f" ({(why or '').strip()})"), user)


# ---------------- disposal ----------------
def dispose(main_db: Session | None, sdb: Session, lead: SalesLead, *, reason: str, note: str, order_no: str | None, user: User, can_approve: bool) -> str:
    """Returns the new status. A partner registration lead is closed only by the CRM."""
    if lead.crm_kind == "partner":
        bad("This lead follows a partner registration. Approve, reject or cancel it in the CRM: the lead then closes by itself.")
    if is_closed(lead):
        bad("This lead is already closed")
    if reason not in DISPOSALS or reason in CRM_ONLY_DISPOSALS:
        bad("Choose the reason first")
    if len((note or "").strip()) < 10:
        bad("Write a short note, at least 10 letters")
    needs_review = DISPOSALS[reason][1]
    lead.disposal_reason = reason
    lead.disposal_note = note.strip()
    lead.disposal_by = user.id
    lead.disposal_at = now()
    lead.order_no = (order_no or None) if reason == "won" else None
    lead.follow_up_on = None
    if needs_review and not can_approve:
        lead.status = "rev"
        log(sdb, lead, "disposal", f"Sent to the manager to approve: {DISPOSALS[reason][0]}. {lead.disposal_note}", user)
        return lead.status
    _close(main_db, sdb, lead, user, reason)
    log(sdb, lead, "disposal", f"Disposed: {DISPOSALS[reason][0]}. {lead.disposal_note}", user)
    return lead.status


def _close(main_db: Session | None, sdb: Session, lead: SalesLead, user: User, reason: str) -> None:
    lead.status = "won" if reason in GOOD_DISPOSALS else "dis"
    lead.closed_at = now()
    if main_db is not None:
        crm_link.resolve_cards(main_db, lead.id)
        if lead.crm_kind == "complaint" and lead.crm_ref:
            ok = False
            try:
                ok = crm_link.close_complaint(main_db, lead.crm_ref, won=reason in GOOD_DISPOSALS, note=lead.disposal_note or "", by=user)
            except Exception:
                ok = False
            lead.crm_close_pending = None if ok else ("won" if reason in GOOD_DISPOSALS else "lost")
            if not ok:
                log(sdb, lead, "crm", "The CRM did not take the close yet. It will be sent again.", None)


def approve_disposal(main_db: Session | None, sdb: Session, lead: SalesLead, user: User) -> None:
    if lead.status != "rev":
        bad("This lead is not waiting for approval")
    _close(main_db, sdb, lead, user, lead.disposal_reason or "dup")
    log(sdb, lead, "disposal", "Disposal approved, the lead is closed", user)


def reopen(sdb: Session, lead: SalesLead, user: User) -> None:
    if lead.crm_kind == "partner":
        bad("A partner registration lead is reopened in the CRM")
    if lead.status not in ("rev", "dis", "won"):
        bad("This lead is open")
    lead.status = "int"
    lead.disposal_reason = None
    lead.disposal_note = None
    lead.closed_at = None
    lead.follow_up_on = date.today()
    log(sdb, lead, "disposal", "Reopened", user)


# ---------------- partner registration leads: status and papers come from the CRM ----------------
def refresh_partner_lead(main_db: Session, sdb: Session, lead: SalesLead) -> dict | None:
    if lead.crm_kind != "partner" or not lead.crm_ref:
        return None
    reg = crm_link.get_partner(main_db, lead.crm_ref)
    if reg is None:
        return None
    new_status = crm_link.PARTNER_LEAD_STATUS.get(reg.onboarding_status, lead.status)
    was = lead.status
    if new_status != lead.status:
        lead.status = new_status
        log(sdb, lead, "crm", f"CRM: {reg.onboarding_status}" + (f". {reg.admin_remark}" if reg.admin_remark and reg.onboarding_status in ("Rejected", "Cancelled") else ""))
    if new_status == "won":
        lead.disposal_reason = "pr_won"
        lead.disposal_note = "Approved in the CRM. The agreement and the partner account follow there."
        lead.closed_at = lead.closed_at or now()
        lead.follow_up_on = None
    elif new_status == "dis":
        lead.disposal_reason = "pr_can"
        lead.disposal_note = (reg.admin_remark or "Cancelled in the CRM.")
        lead.closed_at = lead.closed_at or now()
        lead.follow_up_on = None
    else:
        if was in ("won", "dis"):  # the CRM reopened it
            lead.closed_at = None
            lead.disposal_reason = None
            lead.disposal_note = None
        lead.heat = "hot" if reg.onboarding_status in ("Registration Submitted", "Documents Verification", "Admin Review") else "warm"
        lead.heat_why = jdump(["Sent back by the CRM admin: the partner must correct"] if reg.onboarding_status == "Rejected" else ["Filled in the long partner form"])
        lead.heat_by = "Follows the CRM registration"
    if new_status in ("won", "dis") and was not in ("won", "dis"):
        crm_link.resolve_cards(main_db, lead.id)
    return crm_link.partner_summary(reg)


# ---------------- output ----------------
def lead_out(lead: SalesLead, names: dict[int, str] | None = None) -> dict:
    names = names or {}
    fc = None
    if lead.status == "new" and lead.first_call_due_at is not None:
        fc = int((aware(lead.first_call_due_at) - now()).total_seconds() // 60)
    late = bool(lead.follow_up_on and lead.follow_up_on < date.today() and not is_closed(lead))
    return {
        "id": lead.id, "lead_no": lead.lead_no, "name": lead.name, "phone": lead.phone, "email": lead.email, "item": lead.item,
        "place": lead.place, "state": lead.state, "district": lead.district, "pincode": lead.pincode, "country": lead.country,
        "source": lead.source, "channel": lead.channel, "lead_type": lead.lead_type, "lead_type_label": T.label_of(object_session(lead), lead.lead_type), "lead_type_color": T.color_of(object_session(lead), lead.lead_type),
        "details": lead.details, "message": lead.message, "status": lead.status,
        "owner_user_id": lead.owner_user_id, "owner_name": names.get(lead.owner_user_id) if lead.owner_user_id else None,
        "follow_up_on": lead.follow_up_on.isoformat() if lead.follow_up_on else None, "follow_up_late": late,
        "heat": lead.heat, "heat_why": jload(lead.heat_why), "heat_by": lead.heat_by, "rating_answers": (json.loads(lead.rating_answers) if lead.rating_answers else {}),
        "priority": lead.priority, "priority_why": jload(lead.priority_why), "priority_by": lead.priority_by,
        "value_lakh": float(lead.value_lakh) if lead.value_lakh is not None else None,
        "value_usd": float(lead.value_usd) if lead.value_usd is not None else None,
        "price_basis": lead.price_basis, "closes_on": lead.closes_on.isoformat() if lead.closes_on else None,
        "is_prospect": lead.is_prospect, "attended": lead.last_action_at is not None, "last_action_at": aware(lead.last_action_at).isoformat() if lead.last_action_at else None, "attempts": lead.attempts or 0, "first_called": lead.first_called_at is not None, "first_call_minutes": fc, "crm_kind": lead.crm_kind, "crm_ref": lead.crm_ref,
        "crm_close_pending": lead.crm_close_pending, "disposal_reason": lead.disposal_reason, "disposal_note": lead.disposal_note,
        "order_no": lead.order_no, "created_at": aware(lead.created_at).isoformat() if lead.created_at else None,
        "closed_at": aware(lead.closed_at).isoformat() if lead.closed_at else None,
        "asked_again_at": aware(lead.asked_again_at).isoformat() if lead.asked_again_at else None,
        "closed": is_closed(lead),
    }
