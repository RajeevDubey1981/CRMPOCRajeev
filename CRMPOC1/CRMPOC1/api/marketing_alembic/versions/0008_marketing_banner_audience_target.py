"""marketing banners: target a saved audience, not just everyone

Revision ID: 0008_banner_audience_target
Revises: 0007_marketing_campaigns
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_banner_audience_target"
down_revision: Union[str, Sequence[str], None] = "0007_marketing_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # the version table itself was created with MySQL's narrow default (VARCHAR(32)); widen it once so a
    # longer, more readable revision id (like this one, or a future one) never fails to record here again.
    op.execute("ALTER TABLE marketing_alembic_version MODIFY version_num VARCHAR(128) NOT NULL")
    op.add_column("mk_banner", sa.Column("target_audience_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("mk_banner", "target_audience_id")
