"""A one-off extra expense (delivery/installation hold-up, courier, etc.) that Sales or the Service
Team raises against an order, for the order's own vendor to approve. Nothing debits the vendor's ledger
until the vendor approves it themselves.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models._mixins import TimestampMixin
from app.database import Base

RAISED_BY_TYPES = ("sales", "service_team")
STATUSES = ("Pending", "Approved", "Rejected")


class VendorExpenseApproval(Base, TimestampMixin):
    __tablename__ = "vendor_expense_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    raised_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    raised_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending", index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
