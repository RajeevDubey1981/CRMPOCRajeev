"""Historical installation completion audit and permission.

Revision ID: 0073_historical_installation_completion
Revises: 0072_query_drop_manual_serial_date
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0073_historical_installation_completion"
down_revision: Union[str, None] = "0072_query_drop_manual_serial_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "historical_installation_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation_key", sa.String(100), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("performed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("performed_role", sa.String(100), nullable=True),
        sa.Column("installation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payment_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("payment_transaction_id", sa.Integer(), sa.ForeignKey("payment_transactions.id"), nullable=True),
        sa.Column("proof_file_path", sa.String(500), nullable=True),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incomplete_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_historical_installation_completions_operation_key", "historical_installation_completions", ["operation_key"], unique=True)
    op.create_index("ix_historical_installation_completions_order_id", "historical_installation_completions", ["order_id"])
    op.execute(sa.text("INSERT INTO permissions (role_id, module, sub_module, can_view, can_create, can_edit, can_delete, can_export) SELECT id, 'historical_installations', NULL, 1, 0, 1, 0, 0 FROM roles WHERE LOWER(name) = 'admin' AND NOT EXISTS (SELECT 1 FROM permissions p WHERE p.role_id = roles.id AND p.module = 'historical_installations' AND p.sub_module IS NULL)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE module = 'historical_installations'"))
    op.drop_index("ix_historical_installation_completions_order_id", table_name="historical_installation_completions")
    op.drop_index("ix_historical_installation_completions_operation_key", table_name="historical_installation_completions")
    op.drop_table("historical_installation_completions")
