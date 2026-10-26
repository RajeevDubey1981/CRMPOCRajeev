"""Phase 2 of the vendor/engineer Dr-Cr account system: the Accounts-driven order return/cancellation
workflow (material-receipt gate), the vendor-approved extra-expense flow, and bank statement upload.

Revision ID: 0086_ledger_phase2
Revises: 0085_account_ledger
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0086_ledger_phase2"
down_revision: Union[str, None] = "0085_account_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("material_receipt_confirmed_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("material_receipt_confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("accounts_return_processed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "vendor_expense_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("raised_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("raised_by_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vendor_expense_approvals_order_id", "vendor_expense_approvals", ["order_id"])
    op.create_index("ix_vendor_expense_approvals_vendor_id", "vendor_expense_approvals", ["vendor_id"])
    op.create_index("ix_vendor_expense_approvals_status", "vendor_expense_approvals", ["status"])

    op.create_table(
        "bank_statement_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "bank_statement_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("bank_statement_imports.id"), nullable=False),
        sa.Column("line_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("matched_party_type", sa.String(length=10), nullable=True),
        sa.Column("matched_party_id", sa.Integer(), nullable=True),
        sa.Column("match_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("match_reason", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unmatched"),
        sa.Column("ledger_entry_id", sa.Integer(), sa.ForeignKey("account_ledger_entries.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bank_statement_lines_import_id", "bank_statement_lines", ["import_id"])
    op.create_index("ix_bank_statement_lines_status", "bank_statement_lines", ["status"])


def downgrade() -> None:
    op.drop_index("ix_bank_statement_lines_status", table_name="bank_statement_lines")
    op.drop_index("ix_bank_statement_lines_import_id", table_name="bank_statement_lines")
    op.drop_table("bank_statement_lines")
    op.drop_table("bank_statement_imports")

    op.drop_index("ix_vendor_expense_approvals_status", table_name="vendor_expense_approvals")
    op.drop_index("ix_vendor_expense_approvals_vendor_id", table_name="vendor_expense_approvals")
    op.drop_index("ix_vendor_expense_approvals_order_id", table_name="vendor_expense_approvals")
    op.drop_table("vendor_expense_approvals")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("accounts_return_processed_at")
        batch_op.drop_column("material_receipt_confirmed_at")
        batch_op.drop_column("material_receipt_confirmed_by_user_id")
