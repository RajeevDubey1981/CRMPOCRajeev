"""marketing channels: connected platform logins (Meta) and what they can use (ad accounts)

Revision ID: 0002_marketing_channels
Revises: 0001_marketing_initial
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_marketing_channels"
down_revision: Union[str, Sequence[str], None] = "0001_marketing_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_channel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("ext_user_id", sa.String(length=80), nullable=True),
        sa.Column("ext_name", sa.String(length=255), nullable=False),
        sa.Column("token_enc", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("connected_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mk_channel_platform"), "mk_channel", ["platform"], unique=False)
    op.create_table(
        "mk_channel_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("ext_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("in_use", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "kind", "ext_id", name="uq_mk_channel_asset"),
    )
    op.create_index(op.f("ix_mk_channel_asset_channel_id"), "mk_channel_asset", ["channel_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mk_channel_asset_channel_id"), table_name="mk_channel_asset")
    op.drop_table("mk_channel_asset")
    op.drop_index(op.f("ix_mk_channel_platform"), table_name="mk_channel")
    op.drop_table("mk_channel")
