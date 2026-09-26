from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class PartnerRegistration(Base, TimestampMixin):
    __tablename__ = "partner_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    access_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    partner_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    business_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    alternate_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    form_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Invite Sent", index=True)
    current_form_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    onboarding_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Invite Sent", index=True)
    firm_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gst_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    udyam_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cin_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    aadhaar_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gem_seller_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_of_establishment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_turnover: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    operating_states: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bank_branch: Mapped[str | None] = mapped_column(String(150), nullable=True)
    account_holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ifsc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gst_certificate_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pan_card_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancelled_cheque_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    msme_certificate_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_proof_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    incorporation_certificate_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    aadhaar_card_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_photo_1_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_photo_2_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_photo_3_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_photo_4_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_photo_5_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_resend_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    form_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    form_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
