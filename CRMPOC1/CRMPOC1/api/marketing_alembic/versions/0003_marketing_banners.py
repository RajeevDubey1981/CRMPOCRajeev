"""marketing festive banners: shown at the top of outgoing CRM emails while active

Revision ID: 0003_marketing_banners
Revises: 0002_marketing_channels
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_marketing_banners"
down_revision: Union[str, Sequence[str], None] = "0002_marketing_channels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_banner",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("theme", sa.String(length=20), nullable=False),
        sa.Column("greeting", sa.String(length=60), nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=False),
        sa.Column("pill1", sa.String(length=40), nullable=False),
        sa.Column("pill2", sa.String(length=40), nullable=False),
        sa.Column("cta_text", sa.String(length=40), nullable=False),
        sa.Column("cta_link", sa.String(length=500), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mk_banner")
