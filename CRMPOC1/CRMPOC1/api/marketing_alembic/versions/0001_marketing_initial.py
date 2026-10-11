"""marketing initial: who may use Marketing (people, ticks, history) and the settings

Revision ID: 0001_marketing_initial
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_marketing_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crm_user_id", sa.Integer(), nullable=False),
        sa.Column("name_cache", sa.String(length=255), nullable=False),
        sa.Column("role_cache", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mk_profile_crm_user_id"), "mk_profile", ["crm_user_id"], unique=True)
    op.create_table(
        "mk_role_tick",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_key", sa.String(length=20), nullable=False),
        sa.Column("tick_key", sa.String(length=60), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_key", "tick_key", name="uq_mk_role_tick"),
    )
    op.create_table(
        "mk_user_tick",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crm_user_id", sa.Integer(), nullable=False),
        sa.Column("tick_key", sa.String(length=60), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crm_user_id", "tick_key", name="uq_mk_user_tick"),
    )
    op.create_index(op.f("ix_mk_user_tick_crm_user_id"), "mk_user_tick", ["crm_user_id"], unique=False)
    op.create_table(
        "mk_tick_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_key", sa.String(length=20), nullable=True),
        sa.Column("crm_user_id", sa.Integer(), nullable=True),
        sa.Column("tick_key", sa.String(length=60), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=True),
        sa.Column("by_user_id", sa.Integer(), nullable=False),
        sa.Column("by_name", sa.String(length=255), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mk_tick_history_crm_user_id"), "mk_tick_history", ["crm_user_id"], unique=False)
    op.create_table(
        "mk_setting",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("mk_setting")
    op.drop_index(op.f("ix_mk_tick_history_crm_user_id"), table_name="mk_tick_history")
    op.drop_table("mk_tick_history")
    op.drop_index(op.f("ix_mk_user_tick_crm_user_id"), table_name="mk_user_tick")
    op.drop_table("mk_user_tick")
    op.drop_table("mk_role_tick")
    op.drop_index(op.f("ix_mk_profile_crm_user_id"), table_name="mk_profile")
    op.drop_table("mk_profile")
