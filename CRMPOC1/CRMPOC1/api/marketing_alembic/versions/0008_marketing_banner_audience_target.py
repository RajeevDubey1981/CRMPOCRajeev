"""marketing banners: target a saved audience, not just everyone

Revision ID: 0008_marketing_banner_audience_target
Revises: 0007_marketing_campaigns
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_marketing_banner_audience_target"
down_revision: Union[str, Sequence[str], None] = "0007_marketing_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mk_banner", sa.Column("target_audience_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("mk_banner", "target_audience_id")
