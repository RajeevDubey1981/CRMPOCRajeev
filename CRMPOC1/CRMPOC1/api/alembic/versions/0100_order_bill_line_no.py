"""Add orders.oem_bill_line_no -- which line of a multi-line OEM bill this order is. oem_bill_qty's
column already exists (added by 0099); this just re-activates it in the app and adds the line number
alongside it.

Revision ID: 0100_order_bill_line_no
Revises: 0099_order_oem_bill_qty
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0100_order_bill_line_no"
down_revision = "0099_order_oem_bill_qty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("oem_bill_line_no", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "oem_bill_line_no")
