"""marketing banners: an optional uploaded image, shown in place of the drawn design

Revision ID: 0005_marketing_banner_image
Revises: 0004_marketing_audiences
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_marketing_banner_image"
down_revision: Union[str, Sequence[str], None] = "0004_marketing_audiences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mk_banner", sa.Column("image_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("mk_banner", "image_path")
