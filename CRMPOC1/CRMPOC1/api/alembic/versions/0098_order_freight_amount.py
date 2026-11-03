"""Add orders.freight_amount -- credits the courier's ledger automatically (AccountLedgerEntry,
party_type="courier", source_type="freight"), the same way oem_bill_amount credits the vendor.

Revision ID: 0098_order_freight_amount
Revises: 0097_courier_rate_profiles
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0098_order_freight_amount"
down_revision = "0097_courier_rate_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("freight_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("couriers", sa.Column("payment_cycle_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("couriers", "payment_cycle_days")
    op.drop_column("orders", "freight_amount")
