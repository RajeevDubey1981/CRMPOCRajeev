"""Make account_ledger_entries.pending_payment_id unique: a second entry for the same approved pending
payment means it got posted twice. The row-level locks added in account_ledger.py (same security review,
2026-10-27) are the primary fix for the race that allowed that; this constraint is the backstop.

Checks for existing duplicates first and fails loudly (instead of a bare DB error) if it finds any --
that would mean the double-posting bug already happened for real and the extra entries need manual
review (which vendor/engineer, which entries, whether a correcting credit is owed) before this index can
go on.

Revision ID: 0091_ledger_entry_pending_payment_unique
Revises: 0090_login_lockout
Create Date: 2026-10-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0091_ledger_entry_pending_payment_unique"
down_revision: Union[str, Sequence[str], None] = "0090_login_lockout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dupes = conn.exec_driver_sql(
        """
        SELECT pending_payment_id, COUNT(*) AS n
        FROM account_ledger_entries
        WHERE pending_payment_id IS NOT NULL
        GROUP BY pending_payment_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    if dupes:
        ids = ", ".join(str(row[0]) for row in dupes)
        raise RuntimeError(
            f"account_ledger_entries already has duplicate pending_payment_id values ({ids}) -- "
            "the double-posting bug this migration guards against already happened for these. "
            "Review and correct those entries by hand before re-running this migration."
        )
    op.create_unique_constraint(
        "uq_account_ledger_entries_pending_payment_id",
        "account_ledger_entries",
        ["pending_payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_account_ledger_entries_pending_payment_id",
        "account_ledger_entries",
        type_="unique",
    )
