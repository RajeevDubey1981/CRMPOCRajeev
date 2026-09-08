"""Add item_code to order_items and backfill from item_masters when available.

Revision ID: 0010_order_item_item_code
Revises: 0009_order_extend
Create Date: 2026-08-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_order_item_item_code"
down_revision: Union[str, None] = "0009_order_extend"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("item_code", sa.String(100), nullable=True))
    op.create_index(op.f("ix_order_items_item_code"), "order_items", ["item_code"], unique=False)

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE order_items AS oi
            JOIN item_masters AS im ON oi.item_id = im.id
            SET oi.item_code = im.item_code
            WHERE oi.item_id IS NOT NULL
              AND (oi.item_code IS NULL OR oi.item_code = '')
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_item_code"), table_name="order_items")
    op.drop_column("order_items", "item_code")
