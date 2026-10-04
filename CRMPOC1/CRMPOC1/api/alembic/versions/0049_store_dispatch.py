"""Store: order reservation and dispatch, and the order fulfilment mode.

Revision ID: 0049_store_dispatch
Revises: 0048_store_grn_stock
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0049_store_dispatch"
down_revision: Union[str, None] = "0048_store_grn_stock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("fulfilment", sa.String(length=20), nullable=False, server_default="Vendor"))

    op.create_table(
        "store_dispatches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dispatch_no", sa.String(length=30), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("bill_no", sa.String(length=100), nullable=False),
        sa.Column("courier_id", sa.Integer(), sa.ForeignKey("couriers.id"), nullable=True),
        sa.Column("lrn_no", sa.String(length=100), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("dispatched_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_store_dispatches_dispatch_no", "store_dispatches", ["dispatch_no"], unique=True)
    op.create_index("ix_store_dispatches_order_id", "store_dispatches", ["order_id"])

    op.add_column("store_stock", sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id"), nullable=True))
    op.add_column("store_stock", sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("store_stock", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("store_stock", sa.Column("dispatch_id", sa.Integer(), sa.ForeignKey("store_dispatches.id"), nullable=True))
    op.create_index("ix_store_stock_order_item_id", "store_stock", ["order_item_id"])
    op.create_index("ix_store_stock_dispatch_id", "store_stock", ["dispatch_id"])


def downgrade() -> None:
    op.drop_index("ix_store_stock_dispatch_id", table_name="store_stock")
    op.drop_index("ix_store_stock_order_item_id", table_name="store_stock")
    op.drop_column("store_stock", "dispatch_id")
    op.drop_column("store_stock", "issued_at")
    op.drop_column("store_stock", "reserved_at")
    op.drop_column("store_stock", "order_item_id")
    op.drop_table("store_dispatches")
    op.drop_column("orders", "fulfilment")
