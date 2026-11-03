"""Add orders.oem_bill_qty -- kept only so the migration chain matches what's already stamped on
production from an earlier deploy; the column is unused (we now derive qty from Line Items instead).

Revision ID: 0099_order_oem_bill_qty
Revises: 0098_order_freight_amount
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0099_order_oem_bill_qty"
down_revision = "0098_order_freight_amount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("oem_bill_qty", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "oem_bill_qty")
