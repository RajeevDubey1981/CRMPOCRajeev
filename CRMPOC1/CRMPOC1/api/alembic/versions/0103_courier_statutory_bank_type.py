"""Add courier statutory/bank details and courier_type (parcel vs truck/LTL, no rate card).

Revision ID: 0103_courier_statutory_bank_type
Revises: 0102_order_return_freight
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0103_courier_statutory_bank_type"
down_revision = "0102_order_return_freight"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("couriers", sa.Column("courier_type", sa.String(20), nullable=False, server_default="parcel"))
    op.add_column("couriers", sa.Column("gst_number", sa.String(20), nullable=True))
    op.add_column("couriers", sa.Column("pan_number", sa.String(20), nullable=True))
    op.add_column("couriers", sa.Column("cin", sa.String(30), nullable=True))
    op.add_column("couriers", sa.Column("registered_state", sa.String(100), nullable=True))
    op.add_column("couriers", sa.Column("bank_account_holder", sa.String(255), nullable=True))
    op.add_column("couriers", sa.Column("bank_name", sa.String(255), nullable=True))
    op.add_column("couriers", sa.Column("bank_account_number", sa.String(50), nullable=True))
    op.add_column("couriers", sa.Column("bank_ifsc", sa.String(20), nullable=True))
    op.add_column("couriers", sa.Column("bank_branch", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("couriers", "bank_branch")
    op.drop_column("couriers", "bank_ifsc")
    op.drop_column("couriers", "bank_account_number")
    op.drop_column("couriers", "bank_name")
    op.drop_column("couriers", "bank_account_holder")
    op.drop_column("couriers", "registered_state")
    op.drop_column("couriers", "cin")
    op.drop_column("couriers", "pan_number")
    op.drop_column("couriers", "gst_number")
    op.drop_column("couriers", "courier_type")
