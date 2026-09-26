import secrets

from sqlalchemy import select
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


def ensure_vendor_for_user(db: Session, user: User) -> Vendor | None:
    if (user.role or "").lower() != "vendor":
        return None

    vendor = db.scalar(
        select(Vendor).where(
            Vendor.email == user.email,
        )
    )
    if vendor is not None:
        vendor.deleted_at = None
        if not vendor.is_active:
            vendor.is_active = True
        if not vendor.contact_name:
            vendor.contact_name = user.name
        return vendor

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
