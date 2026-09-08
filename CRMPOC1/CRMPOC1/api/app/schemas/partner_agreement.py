from datetime import datetime

from pydantic import BaseModel, Field


class AgreementContext(BaseModel):
    """What the public signing page needs to render."""

    agreement_no: str
    agreement_version: str
    agreement_title: str
    agreement_effective: str
    agreement_text: str
    registration_no: str
    partner_name: str | None = None
    # Masked for display; the OTP always goes to the registration email on file.
    email: str
    is_signed: bool
    signed_at: datetime | None = None
    resend_wait_seconds: int = 0


class AgreementSendOtpOut(BaseModel):
    success: bool = True
    message: str
    resend_wait_seconds: int


class AgreementVerifyOtpIn(BaseModel):
    otp: str = Field(min_length=4, max_length=10)


class AgreementSignedOut(BaseModel):
    success: bool = True
    agreement_no: str
    agreement_version: str
    email: str
    signed_at: datetime
    ip_address: str | None = None
    method: str = "Email OTP"


class PartnerAgreementAdminOut(BaseModel):
    id: int
    agreement_no: str
    agreement_version: str
    email: str
    agreement_url: str
    is_signed: bool
    signed_at: datetime | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
