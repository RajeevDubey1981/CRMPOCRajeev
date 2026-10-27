"""A plain Dr/Cr ledger shared by vendors and engineers. "Credit" is an amount INDcool owes the party
(an OEM bill, a service/installation payout); "Debit" is an amount already paid to them (a bank
statement line, a manual entry, a return). Balance = sum(credit) - sum(debit): positive means INDcool
still owes the party.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

PARTY_TYPES = ("vendor", "engineer")
ENTRY_TYPES = ("credit", "debit")
# Where an entry came from: "opening" (set once per party), "oem_bill" (auto, from an order's bill
# amount), "bank_statement" (Accounts' upload/match), "manual" (a one-off entry), "return" (Accounts
# processing a returned/cancelled order), "job_payout" (auto, from an existing service/installation
# payment approval), "vendor_approved_expense" (an extra-expense approval the vendor themselves accepted).
SOURCE_TYPES = ("opening", "oem_bill", "bank_statement", "manual", "return", "job_payout", "vendor_approved_expense")


class AccountLedgerEntry(Base):
    __tablename__ = "account_ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # vendor | engineer
    party_id: Mapped[int] = mapped_column(nullable=False, index=True)  # Vendor.id or User.id, by party_type
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)  # credit | debit
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Free-form reference, not a real FK (it points at different tables depending on source_type):
    # an Order id for oem_bill/return, a ServicePaymentRequest/installation payment id for job_payout, etc.
    source_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Set on the handful of debit entries that go through Audit (manual entries, returns, bank statement
    # confirmations): which PendingLedgerPayment Audit approved to produce this row.
    pending_payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pending_ledger_payments.id"), nullable=True)
    # True only when an Admin posted one of those same debit kinds directly, skipping Audit. Never set
    # for credits or for flows Audit was never part of (OEM bill, job payout, vendor-approved expense).
    audit_bypassed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
