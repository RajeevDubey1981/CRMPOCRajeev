"""A bank statement Accounts uploads (CSV) to reconcile against vendor/engineer ledgers. Each row is
matched against vendors and engineers by name/phone/code and amount, scored, and held for Accounts to
confirm or ignore before anything posts to a ledger.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models._mixins import TimestampMixin
from app.database import Base

LINE_STATUSES = ("unmatched", "matched", "pending_audit", "posted", "ignored")


class BankStatementImport(Base, TimestampMixin):
    __tablename__ = "bank_statement_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)


class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("bank_statement_imports.id"), nullable=False, index=True)
    line_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    matched_party_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    matched_party_id: Mapped[int | None] = mapped_column(nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    match_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmatched", index=True)
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("account_ledger_entries.id"), nullable=True)
    pending_payment_id: Mapped[int | None] = mapped_column(ForeignKey("pending_ledger_payments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
