from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    order_no: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Processing", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ifsc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    admin_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who the claim is actually with -- one of "manufacturer" | "courier" | "insurance" | "company"
    # (the business itself, no external party), set when it's raised.
    routed_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manufacturer_id: Mapped[int | None] = mapped_column(ForeignKey("manufacturers.id"), nullable=True)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    insurance_id: Mapped[int | None] = mapped_column(ForeignKey("insurance_companies.id"), nullable=True)


class ClaimPhoto(Base):
    __tablename__ = "claim_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
