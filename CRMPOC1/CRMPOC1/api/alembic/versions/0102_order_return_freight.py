"""Add orders.return_lrn_no and orders.return_freight_amount -- the RTO leg has its own waybill and
its own cost, credited to the courier's ledger as a separate entry from the outbound freight.

Revision ID: 0102_order_return_freight
Revises: 0101_order_boxes_per_unit
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0102_order_return_freight"
down_revision = "0101_order_boxes_per_unit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("return_lrn_no", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("return_freight_amount", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "return_freight_amount")
    op.drop_column("orders", "return_lrn_no")
