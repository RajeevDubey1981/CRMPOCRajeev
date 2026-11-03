"""Add orders.boxes_per_unit -- how many physical boxes make up 1 unit of oem_bill_qty (e.g. 2 for a
Split AC: indoor + outdoor). Data only for now; a later return-side feature uses it.

Revision ID: 0101_order_boxes_per_unit
Revises: 0100_order_bill_line_no
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0101_order_boxes_per_unit"
down_revision = "0100_order_bill_line_no"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("boxes_per_unit", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "boxes_per_unit")
