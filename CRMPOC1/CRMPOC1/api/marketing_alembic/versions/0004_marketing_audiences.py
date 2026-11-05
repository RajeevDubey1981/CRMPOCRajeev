"""marketing audiences: saved filters over the CRM's own Sales leads and Orders

Revision ID: 0004_marketing_audiences
Revises: 0003_marketing_banners
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_marketing_audiences"
down_revision: Union[str, Sequence[str], None] = "0003_marketing_banners"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_audience",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=20), nullable=True),
        sa.Column("stage", sa.String(length=20), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("stale_days", sa.Integer(), nullable=True),
        sa.Column("heat", sa.String(length=10), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mk_audience")
