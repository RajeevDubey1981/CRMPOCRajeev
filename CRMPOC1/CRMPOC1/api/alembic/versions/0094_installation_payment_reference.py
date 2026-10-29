"""Add payment_reference and payment_paid_on to installation requests -- Admin's final payment
step now records a transaction reference (UTR/bank ref) and the actual date money moved,
alongside the bank details fetched live from the engineer's own profile.

Revision ID: 0094_installation_payment_reference
Revises: 0093_clear_stale_serial_verification
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0094_installation_payment_reference"
down_revision = "0093_clear_stale_serial_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "installation_requests",
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "installation_requests",
        sa.Column("payment_paid_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("installation_requests", "payment_paid_on")
    op.drop_column("installation_requests", "payment_reference")
