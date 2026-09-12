from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PARTNER_TYPES = ("Gem Partner", "Distributor", "Service Partner", "Retailer", "Partner")
BUSINESS_TYPES = (
    "Proprietorship",
    "Partnership",
    "LLP",
    "Private Limited",
    "Public Limited",
    "Trust / Society",
    "Other",
)
FORM_STATUSES = ("Invite Sent", "In Progress", "Submitted", "Cancelled")
ONBOARDING_STATUSES = (
    "Invite Sent",
    "In Progress",
    "Registration Submitted",
    "Documents Verification",
    "Admin Review",
    "Onboarding Approved",
    "Partner Active",
    "Rejected",
    "Cancelled",
)
ONBOARDING_STEPS = (
    "Registration Submitted",
    "Documents Verification",
    "Admin Review",
    "Onboarding Approved",
    "Partner Active",
)

DOCUMENT_FIELDS = (
    "gst_certificate_path",
    "pan_card_path",
    "cancelled_cheque_path",
    "msme_certificate_path",
    "address_proof_path",
    "incorporation_certificate_path",
    "aadhaar_card_path",
    "photo_path",
)

FORM_STEPS = (
    {"step": 1, "title": "Partner Category"},
    {"step": 2, "title": "Firm Details"},
    {"step": 3, "title": "Contact Person"},
    {"step": 4, "title": "Address"},
    {"step": 5, "title": "Tax Registration"},
    {"step": 6, "title": "Bank Details"},
    {"step": 7, "title": "Operations"},
    {"step": 8, "title": "Documents"},
    {"step": 9, "title": "Declaration"},
)


class PartnerInviteCreate(BaseModel):
    partner_type: Literal["Gem Partner", "Partner", "Distributor", "Service Partner", "Retailer"]
    email: EmailStr
    contact_person_name: str | None = Field(default=None, max_length=255)
    mobile: str = Field(min_length=10, max_length=20)
    name: str | None = Field(default=None, max_length=255)


class PartnerInviteOut(BaseModel):
    id: int
    registration_no: str
    access_token: str
    registration_url: str
    partner_type: str
    email: str
    form_status: str
    completion_percent: int

    model_config = {"from_attributes": True}


class PartnerRegistrationUpdate(BaseModel):
    onboarding_status: Literal[
        "Registration Submitted",
        "Documents Verification",
        "Admin Review",
        "Onboarding Approved",
        "Partner Active",
        "Rejected",
        "Cancelled",
    ] | None = None
    admin_remark: str | None = None


class PartnerPublicStepSave(BaseModel):
    step: int = Field(ge=1, le=8)
    data: dict


class PartnerPublicSubmit(BaseModel):
    declaration_accepted: bool


class OnboardingStepOut(BaseModel):
    label: str
    done: bool
    current: bool


class PartnerRegistrationOut(BaseModel):
    id: int
    registration_no: str
    access_token: str
    registration_url: str | None = None
    partner_type: str
    business_type: str | None = None
    name: str | None = None
    mobile: str | None = None
    alternate_mobile: str | None = None
    email: EmailStr
    website: str | None = None
    contact_person_name: str | None = None
    contact_designation: str | None = None
    form_status: str
    current_form_step: int
    completion_percent: int
    onboarding_status: str
    email_resend_used: bool = False
    firm_address: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    gst_no: str | None = None
    pan_no: str | None = None
    udyam_no: str | None = None
    cin_no: str | None = None
    aadhaar_no: str | None = None
    gem_seller_id: str | None = None
    year_of_establishment: int | None = None
    annual_turnover: Decimal | None = None
    operating_states: str | None = None
    product_categories: str | None = None
    bank_name: str | None = None
    bank_branch: str | None = None
    account_holder_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    remarks: str | None = None
    declaration_accepted: bool = False
    admin_remark: str | None = None
    gst_certificate_path: str | None = None
    pan_card_path: str | None = None
    cancelled_cheque_path: str | None = None
    msme_certificate_path: str | None = None
    address_proof_path: str | None = None
    incorporation_certificate_path: str | None = None
    aadhaar_card_path: str | None = None
    photo_path: str | None = None
    invited_at: datetime | None = None
    form_started_at: datetime | None = None
    form_submitted_at: datetime | None = None
    submitted_at: datetime
    status_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    onboarding_steps: list[OnboardingStepOut] = []

    model_config = {"from_attributes": True}


class PartnerRegistrationListItem(BaseModel):
    id: int
    registration_no: str
    partner_type: str
    business_type: str | None = None
    name: str | None = None
    mobile: str | None = None
    email: str
    contact_person_name: str | None = None
    form_status: str
    completion_percent: int
    current_form_step: int
    onboarding_status: str
    email_resend_used: bool = False
    registration_url: str | None = None
    invited_at: datetime | None = None
    form_started_at: datetime | None = None
    form_submitted_at: datetime | None = None
    submitted_at: datetime
    status_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PartnerRegistrationListResponse(BaseModel):
    items: list[PartnerRegistrationListItem]
    total: int
    page: int
    per_page: int


class PartnerPublicContext(BaseModel):
    registration_no: str
    partner_type: str
    email: str
    form_status: str
    current_form_step: int
    completion_percent: int
    is_submitted: bool
    form_steps: list[dict]
    partner_types: list[str]
    business_types: list[str]
    data: PartnerRegistrationOut
