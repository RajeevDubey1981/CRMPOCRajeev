"""marketing campaigns: send to everyone (not just one audience), and an uploaded hero image

Revision ID: 0009_campaign_all_and_image
Revises: 0008_banner_audience_target
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_campaign_all_and_image"
down_revision: Union[str, Sequence[str], None] = "0008_banner_audience_target"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mk_campaign", sa.Column("send_to_all", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("mk_campaign", sa.Column("image_path", sa.String(length=500), nullable=True))
    with op.batch_alter_table("mk_campaign") as batch_op:
        batch_op.alter_column("audience_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("mk_campaign") as batch_op:
        batch_op.alter_column("audience_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("mk_campaign", "image_path")
    op.drop_column("mk_campaign", "send_to_all")
