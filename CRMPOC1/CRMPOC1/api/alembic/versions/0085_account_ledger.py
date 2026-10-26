"""Phase 1 of the vendor/engineer Dr-Cr account system: the shared ledger table, a payment-cycle
field on vendors and engineers (users), and the OEM bill amount on orders that auto-credits it.

Revision ID: 0085_account_ledger
Revises: 0084_installation_return_direct_release
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0085_account_ledger"
down_revision: Union[str, None] = "0084_return_direct_release"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("party_type", sa.String(length=10), nullable=False),
        sa.Column("party_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_account_ledger_entries_party_type", "account_ledger_entries", ["party_type"])
    op.create_index("ix_account_ledger_entries_party_id", "account_ledger_entries", ["party_id"])

    with op.batch_alter_table("vendors") as batch_op:
        batch_op.add_column(sa.Column("payment_cycle_days", sa.Integer(), nullable=True))

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("payment_cycle_days", sa.Integer(), nullable=True))

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("oem_bill_amount", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("oem_bill_amount")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("payment_cycle_days")
    with op.batch_alter_table("vendors") as batch_op:
        batch_op.drop_column("payment_cycle_days")
    op.drop_index("ix_account_ledger_entries_party_id", table_name="account_ledger_entries")
    op.drop_index("ix_account_ledger_entries_party_type", table_name="account_ledger_entries")
    op.drop_table("account_ledger_entries")
