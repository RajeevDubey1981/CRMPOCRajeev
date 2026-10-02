import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vendor import Vendor
from app.models.partner_registration import PartnerRegistration
from app.security import hash_password


PARTNER_ACCOUNT_RULES = {
    "gem partner": {"role": "vendor", "prefix": "ven"},
    "csd dealer": {"role": "vendor", "prefix": "csd"},
    "distributor": {"role": "vendor", "prefix": "dis"},
    "service partner": {"role": "engineer", "prefix": "ser"},
    "retailer": {"role": "vendor", "prefix": "ret"},
    "partner": {"role": "vendor", "prefix": "par"},
}


def _next_vendor_code(db: Session) -> str:
    rows = db.scalars(
        select(Vendor.vendor_code).order_by(Vendor.id.desc())
    ).all()
    max_num = 0
    for code in rows:
        suffix = (code or "").strip().upper().removeprefix("VEND")
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"VEND{max_num + 1:03d}"


def _partner_account_rule(registration: PartnerRegistration) -> dict[str, str]:
    partner_type = (registration.partner_type or "").strip().lower()
    return PARTNER_ACCOUNT_RULES.get(partner_type, PARTNER_ACCOUNT_RULES["partner"])


def _next_partner_code(db: Session, prefix: str) -> str:
    code_prefix = f"{prefix.lower()}-"
    rows = db.scalars(
        select(Vendor.vendor_code).where(Vendor.vendor_code.ilike(f"{code_prefix}%"))
    ).all()
    max_num = 0
    for code in rows:
        suffix = (code or "").strip().lower().removeprefix(code_prefix)
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{code_prefix}{max_num + 1:03d}"


def _normalized_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _vendor_by_email(db: Session, email: str | None) -> Vendor | None:
    normalized = _normalized_email(email)
    if not normalized:
        return None
    return db.scalar(
        select(Vendor)
        .where(func.lower(func.trim(Vendor.email)) == normalized)
        .order_by(Vendor.deleted_at.is_(None).desc(), Vendor.id.desc())
    )


def _touch_vendor_from_user(vendor: Vendor, user: User) -> Vendor:
    vendor.deleted_at = None
    if not vendor.is_active:
        vendor.is_active = True
    if not vendor.contact_name:
        vendor.contact_name = user.name
    return vendor


def ensure_vendor_for_user(db: Session, user: User, *, create_if_missing: bool = True) -> Vendor | None:
    """Ensure a vendor master row exists for a vendor-role user (create path only)."""
    if (user.role or "").lower() != "vendor":
        return None

    vendor = _vendor_by_email(db, user.email)
    if vendor is not None:
        return _touch_vendor_from_user(vendor, user)

    if not create_if_missing:
        return None

    vendor = Vendor(
        vendor_code=_next_vendor_code(db),
        name_of_firm=user.name or user.email,
        contact_name=user.name,
        contact_mobile=user.phone,
        email=user.email,
        is_active=True,
    )
    db.add(vendor)
    db.flush()
    return vendor


def vendor_master_for_user(db: Session, user: User) -> Vendor | None:
    if (user.role or "").lower() != "vendor":
        return None
    return _vendor_by_email(db, user.email)


def sync_vendor_for_user_email_update(
    db: Session,
    user: User,
    previous_email: str | None,
) -> Vendor | None:
    """Keep vendor master in sync when an existing vendor user's email changes.

    Never creates a new vendor row. Updates the vendor that matched the previous
    email, or reuses an existing vendor that already has the new email.
    """
    if (user.role or "").lower() != "vendor":
        return None

    new_email = (user.email or "").strip()
    if not new_email:
        return None

    old_norm = _normalized_email(previous_email)
    new_norm = _normalized_email(new_email)
    if old_norm == new_norm:
        vendor = _vendor_by_email(db, new_email)
        return _touch_vendor_from_user(vendor, user) if vendor else None

    vendor_at_new = _vendor_by_email(db, new_email)
    vendor_at_old = _vendor_by_email(db, previous_email) if old_norm else None

    if vendor_at_old is not None and vendor_at_new is not None and vendor_at_old.id != vendor_at_new.id:
        return _touch_vendor_from_user(vendor_at_new, user)

    if vendor_at_old is not None:
        vendor_at_old.email = new_email
        return _touch_vendor_from_user(vendor_at_old, user)

    if vendor_at_new is not None:
        return _touch_vendor_from_user(vendor_at_new, user)

    return None


def ensure_partner_account(db: Session, registration: PartnerRegistration) -> Vendor:
    email = registration.email.strip().lower()
    account_rule = _partner_account_rule(registration)
    role = account_rule["role"]
    code_prefix = account_rule["prefix"]

    # Email is globally unique, including for soft-deleted users. Reuse and
    # reactivate an existing row instead of attempting a duplicate insert.
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            name=registration.name or registration.contact_person_name or email,
            email=email,
            # The partner sets a password through the admin password-reset workflow.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=role,
            phone=registration.mobile,
            is_active=True,
        )
        db.add(user)
        db.flush()
    elif (user.role or "").lower() not in {"vendor", "engineer", role}:
        raise ValueError(f"A user with incompatible role already exists for {email}")
    else:
        user.role = role
        user.deleted_at = None
        user.is_active = True

    vendor = db.scalar(select(Vendor).where(Vendor.email == email))
    if vendor is None:
        vendor = Vendor(
            vendor_code=_next_partner_code(db, code_prefix),
            name_of_firm=registration.name or registration.contact_person_name or email,
            contact_name=registration.contact_person_name,
            contact_mobile=registration.mobile,
            email=email,
            is_active=True,
        )
        db.add(vendor)
        db.flush()
    else:
        vendor.deleted_at = None

    vendor.name_of_firm = registration.name or vendor.name_of_firm or email
    vendor.contact_name = registration.contact_person_name or vendor.contact_name
    vendor.contact_mobile = registration.mobile or vendor.contact_mobile
    vendor.email = email
    vendor.gst_no = registration.gst_no or vendor.gst_no
    vendor.address = registration.firm_address or vendor.address
    vendor.state = registration.state or vendor.state
    vendor.district = registration.district or vendor.district
    vendor.pincode = registration.pincode or vendor.pincode
    vendor.is_active = True
    db.flush()
    return vendor
