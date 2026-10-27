"""Maker-checker on the ledger: a debit (a payment) that Accounts/Accounts Manager generated, sitting
here until an Audit role approves or rejects it. Nothing changes a party's balance until approved.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models._mixins import TimestampMixin
from app.database import Base

STATUSES = ("Pending", "Approved", "Rejected")


class PendingLedgerPayment(Base, TimestampMixin):
    __tablename__ = "pending_ledger_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    party_id: Mapped[int] = mapped_column(nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[int | None] = mapped_column(nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    raised_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending", index=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_entry_id: Mapped[int | None] = mapped_column(ForeignKey("account_ledger_entries.id"), nullable=True)
