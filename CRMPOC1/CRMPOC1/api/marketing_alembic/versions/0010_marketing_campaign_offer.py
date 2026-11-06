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
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mk_campaign")}
    if "offer_name" not in columns:
        op.add_column("mk_campaign", sa.Column("offer_name", sa.String(length=255), nullable=False, server_default=""))
    if "offer_price" not in columns:
        op.add_column("mk_campaign", sa.Column("offer_price", sa.String(length=30), nullable=False, server_default=""))
    if "offer_mrp" not in columns:
        op.add_column("mk_campaign", sa.Column("offer_mrp", sa.String(length=30), nullable=False, server_default=""))
    if "offer_image_path" not in columns:
        op.add_column("mk_campaign", sa.Column("offer_image_path", sa.String(length=500), nullable=True))
    if "offer_link" not in columns:
        op.add_column("mk_campaign", sa.Column("offer_link", sa.String(length=500), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("mk_campaign", "offer_link")
    op.drop_column("mk_campaign", "offer_image_path")
    op.drop_column("mk_campaign", "offer_mrp")
    op.drop_column("mk_campaign", "offer_price")
    op.drop_column("mk_campaign", "offer_name")
