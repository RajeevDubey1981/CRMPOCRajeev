"""Store: GRN, GRN lines, stock and ledger.

Revision ID: 0048_store_grn_stock
Revises: 0047_complaint_priority
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0048_store_grn_stock"
down_revision: Union[str, None] = "0047_complaint_priority"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_grns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grn_no", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("reference_no", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Draft"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_store_grns_grn_no", "store_grns", ["grn_no"], unique=True)
    op.create_index("ix_store_grns_status", "store_grns", ["status"])

    op.create_table(
        "store_grn_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grn_id", sa.Integer(), sa.ForeignKey("store_grns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("stock_type", sa.String(length=20), nullable=False, server_default="Fresh"),
        sa.Column("serial_no", sa.String(length=100), nullable=True),
        sa.Column("serial_no_2", sa.String(length=100), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("condition", sa.String(length=20), nullable=False, server_default="OK"),
        sa.Column("bin_location", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_store_grn_lines_grn_id", "store_grn_lines", ["grn_id"])
    op.create_index("ix_store_grn_lines_item_id", "store_grn_lines", ["item_id"])
    op.create_index("ix_store_grn_lines_serial_no", "store_grn_lines", ["serial_no"])
    op.create_index("ix_store_grn_lines_serial_no_2", "store_grn_lines", ["serial_no_2"])

    op.create_table(
        "store_stock",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("grn_line_id", sa.Integer(), sa.ForeignKey("store_grn_lines.id"), nullable=True),
        sa.Column("grn_id", sa.Integer(), sa.ForeignKey("store_grns.id"), nullable=True),
        sa.Column("serial_no", sa.String(length=100), nullable=True),
        sa.Column("serial_no_2", sa.String(length=100), nullable=True),
        sa.Column("stock_type", sa.String(length=20), nullable=False, server_default="Fresh"),
        sa.Column("condition", sa.String(length=20), nullable=False, server_default="OK"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Available"),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("bin_location", sa.String(length=50), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("serial_no", name="uq_store_stock_serial_no"),
        sa.UniqueConstraint("serial_no_2", name="uq_store_stock_serial_no_2"),
    )
    op.create_index("ix_store_stock_item_id", "store_stock", ["item_id"])
    op.create_index("ix_store_stock_grn_id", "store_stock", ["grn_id"])
    op.create_index("ix_store_stock_status", "store_stock", ["status"])
    op.create_index("ix_store_stock_received_at", "store_stock", ["received_at"])

    op.create_table(
        "store_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", sa.String(length=20), nullable=False),
        sa.Column("doc_no", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("store_stock.id"), nullable=True),
        sa.Column("serial_no", sa.String(length=100), nullable=True),
        sa.Column("qty_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_type", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_store_ledger_doc_no", "store_ledger", ["doc_no"])
    op.create_index("ix_store_ledger_item_id", "store_ledger", ["item_id"])
    op.create_index("ix_store_ledger_serial_no", "store_ledger", ["serial_no"])
    op.create_index("ix_store_ledger_created_at", "store_ledger", ["created_at"])


def downgrade() -> None:
    op.drop_table("store_ledger")
    op.drop_table("store_stock")
    op.drop_table("store_grn_lines")
    op.drop_table("store_grns")
