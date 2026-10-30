"""Add payment_reference and payment_paid_on to service payment requests -- same two fields
0094 added to installation requests, so a pooled payment (same engineer or vendor, several
payments, one bank transfer) can record one shared reference and date across both modules.

Revision ID: 0095_service_payment_reference
Revises: 0094_installation_payment_reference
Create Date: 2026-10-30
"""

from alembic import op
import sqlalchemy as sa


revision = "0095_service_payment_reference"
down_revision = "0094_installation_payment_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_payment_requests",
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "service_payment_requests",
        sa.Column("payment_paid_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_payment_requests", "payment_paid_on")
    op.drop_column("service_payment_requests", "payment_reference")
