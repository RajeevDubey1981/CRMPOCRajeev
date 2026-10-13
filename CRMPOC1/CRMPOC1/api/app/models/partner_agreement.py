from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, true
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class PartnerAgreement(Base, TimestampMixin):
    """A partner's digital signing of the service agreement, via email OTP.

    One row per registration. Created when an admin approves the registration
    and stays unsigned until the partner completes OTP verification; signing
    is what triggers vendor account creation and the welcome email.
    """

    __tablename__ = "partner_agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("partner_registrations.id"), nullable=False, index=True
    )
    agreement_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    agreement_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    access_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signed_destination: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Current outstanding OTP. Cleared once consumed so a code can't be reused.
    otp_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    otp_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


    # the signed paper copy, uploaded by Admin or Sub Admin
    hard_copy_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hard_copy_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hard_copy_received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    hard_copy_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hard_copy_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_copy_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hard_copy_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class PartnerAgreementEvent(Base):
    """What happened to the agreement's hard copy: uploaded, replaced, removed, shared or kept private."""

    __tablename__ = "partner_agreement_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("partner_agreements.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
