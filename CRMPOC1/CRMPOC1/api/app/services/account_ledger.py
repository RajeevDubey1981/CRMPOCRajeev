"""Balance and overdue computation for the vendor/engineer ledger. Pure functions over a list of
entries, called by the router — nothing here touches the database directly."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.models.account_ledger import AccountLedgerEntry


def compute_balance(entries: list[AccountLedgerEntry]) -> Decimal:
    total = Decimal("0")
    for e in entries:
        amt = Decimal(str(e.amount))
        total += amt if e.entry_type == "credit" else -amt
    return total


def compute_oldest_unpaid_since(entries: list[AccountLedgerEntry]) -> date | None:
    """FIFO aging: walk entries oldest-first, settling each debit against the oldest still-open
    credit(s). What's left unsettled at the front of the queue is the oldest unpaid amount — its date
    is what a payment cycle is measured against. Returns None once nothing is outstanding."""
    ordered = sorted(entries, key=lambda e: (e.entry_date, e.id))
    open_credits: list[list] = []  # [entry_date, remaining_amount], oldest first
    for e in ordered:
        amt = Decimal(str(e.amount))
        if e.entry_type == "credit":
            open_credits.append([e.entry_date, amt])
        else:
            remaining = amt
            while remaining > 0 and open_credits:
                remaining -= open_credits[0][1]
                if remaining >= 0:
                    open_credits.pop(0)
                else:
                    open_credits[0][1] = -remaining
                    remaining = Decimal("0")
    return open_credits[0][0] if open_credits else None


def compute_overdue_days(oldest_unpaid_since: date | None, cycle_days: int | None, today: date | None = None) -> int:
    """0 when there's nothing outstanding, no cycle is set, or it's still within the cycle."""
    if oldest_unpaid_since is None or not cycle_days:
        return 0
    today = today or datetime.utcnow().date()
    age = (today - oldest_unpaid_since).days
    return max(0, age - cycle_days)
