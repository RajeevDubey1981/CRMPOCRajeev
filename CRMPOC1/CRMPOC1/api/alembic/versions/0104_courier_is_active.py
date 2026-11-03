"""Add couriers.is_active -- deactivate hides a courier from the dropdown for new orders without
requiring every order on it to be Delivered first (unlike Delete).

Revision ID: 0104_courier_is_active
Revises: 0103_courier_statutory_bank_type
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0104_courier_is_active"
down_revision = "0103_courier_statutory_bank_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("couriers", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("couriers", "is_active")
