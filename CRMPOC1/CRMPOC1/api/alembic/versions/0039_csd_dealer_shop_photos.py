"""Add CSD dealer shop photo columns to partner_registrations.

Revision ID: 0039_csd_dealer_shop_photos
Revises: 0038_partner_agreement_signature_details
Create Date: 2026-09-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0039_csd_dealer_shop_photos"
down_revision: Union[str, None] = "0038_partner_agreement_signature_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "partner_registrations",
        sa.Column("shop_photo_1_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "partner_registrations",
        sa.Column("shop_photo_2_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "partner_registrations",
        sa.Column("shop_photo_3_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "partner_registrations",
        sa.Column("shop_photo_4_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "partner_registrations",
        sa.Column("shop_photo_5_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("partner_registrations", "shop_photo_5_path")
    op.drop_column("partner_registrations", "shop_photo_4_path")
    op.drop_column("partner_registrations", "shop_photo_3_path")
    op.drop_column("partner_registrations", "shop_photo_2_path")
    op.drop_column("partner_registrations", "shop_photo_1_path")
