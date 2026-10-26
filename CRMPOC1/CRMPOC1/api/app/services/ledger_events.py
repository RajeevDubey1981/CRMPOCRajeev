"""DB-touching ledger hooks called from other routers (services, installations) so they don't need to
know the ledger's internals — just that a job payout happened.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.account_ledger import AccountLedgerEntry


def post_job_payout(db: Session, *, engineer_user_id: int | None, amount: float, description: str, source_id: int) -> None:
    """Record a completed engineer payout in the engineer's ledger.

    A service/installation payment request is approved AND paid in the same step (the admin uploads
    payment proof, or hands over cash, right there) — there's no "owed but unpaid" period to track like
    there is for an OEM bill. So this posts an already-settled credit+debit pair, same amount, same day:
    it nets to zero on the balance (correct — nothing is actually outstanding) but still shows up as a
    "Job payout" row in the engineer's ledger timeline per the merge the user asked for.
    """
    if not engineer_user_id or not amount or amount <= 0:
        return
    today = datetime.now(timezone.utc).date()
    for entry_type in ("credit", "debit"):
        db.add(AccountLedgerEntry(
            party_type="engineer",
            party_id=engineer_user_id,
            entry_type=entry_type,
            amount=amount,
            description=description,
            source_type="job_payout",
            source_id=source_id,
            entry_date=today,
            created_by_user_id=None,
        ))
