from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.partner_registration import PartnerRegistration
from app.schemas.partner_registration import DOCUMENT_FIELDS, ONBOARDING_STEPS, OnboardingStepOut, PartnerRegistrationOut
from app.services.file_service import to_public_upload_path

PARTNER_ADMIN_ROLES = frozenset({"admin", "incool", "indcool", "sub_admin"})
PARTNER_INVITE_ROLES = PARTNER_ADMIN_ROLES | frozenset({"sales"})

FORM_STATUSES = ("Invite Sent", "In Progress", "Submitted")

FORM_STEP_DEFINITIONS = (
    {"step": 1, "title": "Partner Category", "fields": ("partner_type", "business_type")},
    {"step": 2, "title": "Firm Details", "fields": ("name",)},
    {"step": 3, "title": "Contact Person", "fields": ("contact_person_name", "contact_designation", "mobile", "email")},
    {"step": 4, "title": "Address", "fields": ("firm_address", "city", "state", "pincode")},
    {"step": 5, "title": "Tax Registration", "fields": ("gst_no", "pan_no", "aadhaar_no")},
    {"step": 6, "title": "Bank Details", "fields": ("bank_name", "account_holder_name", "account_number", "ifsc_code")},
    {"step": 7, "title": "Operations", "fields": ("operating_states", "product_categories")},
    {
        "step": 8,
        "title": "Documents",
        "fields": (
            "gst_certificate_path",
            "pan_card_path",
            "cancelled_cheque_path",
            "address_proof_path",
            "aadhaar_card_path",
            "shop_photo_1_path",
        ),
    },
)

DOCUMENT_KEYS = (
    "gst_certificate",
    "pan_card",
    "cancelled_cheque",
    "address_proof",
    "aadhaar_card",
    "msme_certificate",
    "incorporation_certificate",
    "photo",
    "shop_photo_1",
    "shop_photo_2",
    "shop_photo_3",
    "shop_photo_4",
    "shop_photo_5",
)

REQUIRED_DOCUMENT_KEYS = frozenset({
    "gst_certificate",
    "pan_card",
    "cancelled_cheque",
    "address_proof",
    "aadhaar_card",
})

COMPANY_BUSINESS_TYPES = frozenset({"Private Limited", "Public Limited", "LLP", "Partnership"})
CSD_PARTNER_TYPE = "CSD Dealer"
SHOP_PHOTO_FIELDS = (
    "shop_photo_1",
    "shop_photo_2",
    "shop_photo_3",
    "shop_photo_4",
    "shop_photo_5",
)
CSD_REQUIRED_SHOP_PHOTO_COUNT = 5
DEFAULT_REQUIRED_SHOP_PHOTO_COUNT = 1
GEM_SELLER_ID_REQUIRED_FOR = frozenset({"Gem Partner"})


def required_shop_photo_count(partner_type: str | None) -> int:
    if (partner_type or "").strip() == CSD_PARTNER_TYPE:
        return CSD_REQUIRED_SHOP_PHOTO_COUNT
    return DEFAULT_REQUIRED_SHOP_PHOTO_COUNT


def gem_seller_id_required(partner_type: str | None) -> bool:
    normalized = (partner_type or "").strip().casefold()
    return normalized in {partner_type.casefold() for partner_type in GEM_SELLER_ID_REQUIRED_FOR}


def is_partner_admin(role: str | None) -> bool:
    return (role or "").strip().lower() in PARTNER_ADMIN_ROLES


def can_invite_partner(role: str | None) -> bool:
    return (role or "").strip().lower() in PARTNER_INVITE_ROLES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_optional_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("Year of Establishment must be a valid date") from exc
    raise ValueError("Year of Establishment must be a valid date")


def generate_registration_no(db: Session) -> str:
    # Continue from the highest number in use. Counting rows breaks as soon as a registration is deleted
    # (7 rows left, GEM-PART-00008 still exists, next number would collide).
    highest = 0
    for number in db.scalars(select(PartnerRegistration.registration_no)):
        try:
            highest = max(highest, int(str(number).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"GEM-PART-{highest + 1:05d}"


def generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def build_public_registration_url(token: str) -> str:
    base = (settings.app_public_url or "").strip()
    if not base:
        base = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:5173"
    return urljoin(base.rstrip("/") + "/", f"partner-registration/{token}")


def _is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _required_document_keys(row: PartnerRegistration) -> set[str]:
    keys = set(REQUIRED_DOCUMENT_KEYS)
    if row.business_type in COMPANY_BUSINESS_TYPES:
        keys.add("incorporation_certificate")
    return keys


def _shop_photo_uploaded_count(row: PartnerRegistration) -> int:
    count = 0
    for key in SHOP_PHOTO_FIELDS:
        if _is_filled(getattr(row, f"{key}_path", None)):
            count += 1
    return count


def _step_fields_required_fields(step: int, row: PartnerRegistration) -> list[str]:
    """Return the list of required fields for a given step considering partner type."""
    definition = next((item for item in FORM_STEP_DEFINITIONS if item["step"] == step), None)
    if definition is None:
        return []
    fields = list(definition["fields"])
    if step == 2 and gem_seller_id_required(row.partner_type):
        fields.append("gem_seller_id")
    return fields


# Public wizard has 9 steps (8 data steps + declaration).
TOTAL_FORM_STEPS = 9


def compute_form_progress(row: PartnerRegistration) -> tuple[int, int]:
    current_step = 1

    for definition in FORM_STEP_DEFINITIONS:
        step_filled = 0
        if definition["step"] == 8:
            required_keys = _required_document_keys(row)
            required_shop_photos = required_shop_photo_count(row.partner_type)
            step_total = len(required_keys) + required_shop_photos
            for key in required_keys:
                if _is_filled(getattr(row, f"{key}_path", None)):
                    step_filled += 1
            shop_uploaded = _shop_photo_uploaded_count(row)
            step_filled += min(shop_uploaded, required_shop_photos)
        elif definition["step"] == 2:
            step_fields = _step_fields_required_fields(2, row)
            step_total = len(step_fields)
            for field in step_fields:
                if _is_filled(getattr(row, field, None)):
                    step_filled += 1
        else:
            step_total = len(definition["fields"])
            for field in definition["fields"]:
                if _is_filled(getattr(row, field, None)):
                    step_filled += 1

        if step_filled == step_total and step_total > 0:
            current_step = min(definition["step"] + 1, TOTAL_FORM_STEPS)
        elif step_filled > 0:
            current_step = definition["step"]
            break

    if row.form_status == "Submitted":
        current_step = TOTAL_FORM_STEPS
        percent = 100
    else:
        percent = round((current_step / TOTAL_FORM_STEPS) * 100)

    return percent, current_step


def refresh_form_progress(row: PartnerRegistration) -> None:
    percent, current_step = compute_form_progress(row)
    row.completion_percent = percent
    row.current_form_step = current_step
    if row.form_status != "Submitted":
        if percent == 0 and row.form_started_at is None:
            row.form_status = "Invite Sent"
        else:
            row.form_status = "In Progress"


def build_onboarding_steps(status: str) -> list[OnboardingStepOut]:
    if status in {"Invite Sent", "In Progress"}:
        return [
            OnboardingStepOut(label="Partner Form", done=False, current=True),
            *[
                OnboardingStepOut(label=step, done=False, current=False)
                for step in ONBOARDING_STEPS
            ],
        ]

    if status == "Rejected":
        return [
            OnboardingStepOut(label=step, done=False, current=index == 0)
            for index, step in enumerate(ONBOARDING_STEPS)
        ]

    if status == "Partner Active":
        return [OnboardingStepOut(label=step, done=True, current=False) for step in ONBOARDING_STEPS]

    current_index = ONBOARDING_STEPS.index(status) if status in ONBOARDING_STEPS else 0
    return [
        OnboardingStepOut(
            label=label,
            done=index < current_index,
            current=index == current_index,
        )
        for index, label in enumerate(ONBOARDING_STEPS)
    ]


def hydrate_partner(row: PartnerRegistration) -> PartnerRegistrationOut:
    data = PartnerRegistrationOut.model_validate(row)
    for field in DOCUMENT_FIELDS:
        current = getattr(data, field, None)
        if current:
            setattr(data, field, to_public_upload_path(current))
    data.registration_url = build_public_registration_url(row.access_token)
    data.onboarding_steps = build_onboarding_steps(row.onboarding_status)
    return data


def get_by_token(db: Session, token: str) -> PartnerRegistration | None:
    return db.scalar(select(PartnerRegistration).where(PartnerRegistration.access_token == token))


def apply_step_fields(row: PartnerRegistration, step: int, data: dict) -> None:
    definition = next((item for item in FORM_STEP_DEFINITIONS if item["step"] == step), None)
    if definition is None:
        raise ValueError("Invalid form step")

    allowed = set(definition["fields"])
    if step == 1:
        allowed.update({"partner_type", "business_type"})
    elif step == 2:
        allowed.update({"name", "year_of_establishment", "annual_turnover", "gem_seller_id"})
    elif step == 3:
        allowed.update({
            "contact_person_name",
            "contact_designation",
            "mobile",
            "alternate_mobile",
            "email",
            "website",
        })
    elif step == 4:
        allowed.update({"firm_address", "city", "district", "state", "pincode"})
    elif step == 5:
        allowed.update({"gst_no", "pan_no", "aadhaar_no", "udyam_no", "cin_no"})
    elif step == 6:
        allowed.update({
            "bank_name",
            "bank_branch",
            "account_holder_name",
            "account_number",
            "ifsc_code",
        })
    elif step == 7:
        allowed.update({"operating_states", "product_categories", "remarks"})

    for field, value in data.items():
        if field not in allowed:
            continue
        if field == "gem_seller_id" and not gem_seller_id_required(row.partner_type):
            continue
        if field == "year_of_establishment":
            value = _parse_optional_date(value)
        if field == "email" and value is not None:
            value = str(value).strip().lower()
        if field == "gst_no" and value is not None:
            value = str(value).strip().upper()
            if value and len(value) != 15:
                raise ValueError("GSTIN must contain exactly 15 characters")
        if isinstance(value, str):
            value = value.strip() or None
        setattr(row, field, value)

    if step in {1, 2} and not gem_seller_id_required(row.partner_type):
        row.gem_seller_id = None

    if row.form_started_at is None:
        row.form_started_at = _now()
    refresh_form_progress(row)


def validate_submission(row: PartnerRegistration) -> list[str]:
    errors: list[str] = []
    for definition in FORM_STEP_DEFINITIONS:
        if definition["step"] == 8:
            for key in _required_document_keys(row):
                if not _is_filled(getattr(row, f"{key}_path", None)):
                    errors.append(f"Missing document: {key}")
            required_count = required_shop_photo_count(row.partner_type)
            uploaded_count = _shop_photo_uploaded_count(row)
            if uploaded_count < required_count:
                errors.append(
                    f"Upload at least {required_count} shop photo(s); "
                    f"{row.partner_type} requires {required_count}, you have uploaded {uploaded_count}"
                )
            continue
        step_fields = _step_fields_required_fields(definition["step"], row)
        for field in step_fields:
            if not _is_filled(getattr(row, field, None)):
                errors.append(f"Missing field: {field}")
    if not row.declaration_accepted:
        errors.append("Declaration must be accepted")
    return errors
