"""Maker-checker on the ledger: every debit (a payment Accounts/Accounts Manager generates) becomes a
pending row an Audit role approves or rejects, individually or as a batch, before it actually posts.
Admin can still post directly, same as before this change.

Revision ID: 0088_ledger_audit
Revises: 0087_engineer_bank_details
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0088_ledger_audit"
down_revision: Union[str, None] = "0087_engineer_bank_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_ledger_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("party_type", sa.String(length=10), nullable=False),
        sa.Column("party_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("raised_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("decided_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("posted_entry_id", sa.Integer(), sa.ForeignKey("account_ledger_entries.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pending_ledger_payments_party", "pending_ledger_payments", ["party_type", "party_id"])
    op.create_index("ix_pending_ledger_payments_status", "pending_ledger_payments", ["status"])

    with op.batch_alter_table("bank_statement_lines") as batch_op:
        batch_op.add_column(sa.Column("pending_payment_id", sa.Integer(), nullable=True))

    with op.batch_alter_table("account_ledger_entries") as batch_op:
        batch_op.add_column(sa.Column("pending_payment_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("audit_bypassed", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("account_ledger_entries") as batch_op:
        batch_op.drop_column("audit_bypassed")
        batch_op.drop_column("pending_payment_id")

    with op.batch_alter_table("bank_statement_lines") as batch_op:
        batch_op.drop_column("pending_payment_id")

    op.drop_index("ix_pending_ledger_payments_status", table_name="pending_ledger_payments")
    op.drop_index("ix_pending_ledger_payments_party", table_name="pending_ledger_payments")
    op.drop_table("pending_ledger_payments")
