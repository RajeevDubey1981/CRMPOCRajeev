from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class Bid(Base, TimestampMixin):
    """One tender / bid INDcool wants to take part in. One bid has one bidder at a time."""

    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_number: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    bid_type: Mapped[str] = mapped_column(String(20), nullable=False, default="GeM")  # GeM | State govt
    portal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    product_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    emd_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    emd_mode: Mapped[str | None] = mapped_column(String(60), nullable=True)
    emd_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    epbg_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tender_fee: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # internal, never shown to vendors

    # Open | Allocated | Confirmed | Submitted | Won | Lost | Closed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Open", index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    is_self: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # INDcool bids itself
    allocated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirm_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    submit_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class BidEvent(Base):
    """History line of a bid. vendor_id is set when the line concerns one vendor, so that vendor may see it."""

    __tablename__ = "bid_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)


class BidRequest(Base):
    """A vendor asking the bid team for a bid. bid_id stays empty until that bid number is entered."""

    __tablename__ = "bid_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id", ondelete="SET NULL"), nullable=True, index=True)
    bid_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Requested | Allocated | Declined | Not available
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Requested", index=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BidReminder(Base):
    """One row per reminder sent, so a restart or a second server never sends the same day's reminder twice."""

    __tablename__ = "bid_reminders"
    __table_args__ = (UniqueConstraint("bid_id", "sent_on", name="uq_bid_reminders_bid_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    sent_on: Mapped[date] = mapped_column(Date, nullable=False)
    sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
