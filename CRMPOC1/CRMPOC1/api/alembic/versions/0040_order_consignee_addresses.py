"""Add order_consignee_addresses for multi ship-to locations.

Revision ID: 0040_order_consignee_addresses
Revises: 0039_csd_dealer_shop_photos
Create Date: 2026-09-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0040_order_consignee_addresses"
down_revision: Union[str, None] = "0039_csd_dealer_shop_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_consignee_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("consignee_name", sa.String(length=255), nullable=True),
        sa.Column("contact", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_consignee_addresses_order_id",
        "order_consignee_addresses",
        ["order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_consignee_addresses_order_id", table_name="order_consignee_addresses")
    op.drop_table("order_consignee_addresses")
