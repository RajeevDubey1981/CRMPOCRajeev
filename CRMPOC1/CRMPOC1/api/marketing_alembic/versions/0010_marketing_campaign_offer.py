"""marketing campaigns: an offer product card (image, name, price, link) shown under the hero banner

Revision ID: 0010_marketing_campaign_offer
Revises: 0009_campaign_all_and_image
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_marketing_campaign_offer"
down_revision: Union[str, Sequence[str], None] = "0009_campaign_all_and_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mk_campaign", sa.Column("offer_name", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("mk_campaign", sa.Column("offer_price", sa.String(length=30), nullable=False, server_default=""))
    op.add_column("mk_campaign", sa.Column("offer_mrp", sa.String(length=30), nullable=False, server_default=""))
    op.add_column("mk_campaign", sa.Column("offer_image_path", sa.String(length=500), nullable=True))
    op.add_column("mk_campaign", sa.Column("offer_link", sa.String(length=500), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("mk_campaign", "offer_link")
    op.drop_column("mk_campaign", "offer_image_path")
    op.drop_column("mk_campaign", "offer_mrp")
    op.drop_column("mk_campaign", "offer_price")
    op.drop_column("mk_campaign", "offer_name")
