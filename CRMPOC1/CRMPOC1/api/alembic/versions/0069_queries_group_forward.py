"""Queries: forward, CC and group conversations, priority, history and the 24 hour alarm.

A query keeps its owner (who raised it) and now also a holder (who has to answer it, empty means the Admin team), a
priority, and the time since which it waits for an answer. The people in a conversation are rows with a joined and a left
time, so someone can be taken out for a private talk and added back. Every step is written in the history.

Revision ID: 0069_queries_group_forward
Revises: 0068_marketing_manager_role
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0069_queries_group_forward"
down_revision: Union[str, None] = "0068_marketing_manager_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_queries", sa.Column("priority", sa.String(10), nullable=False, server_default="normal"))
    op.add_column("user_queries", sa.Column("holder_id", sa.Integer(), sa.ForeignKey("users.id", name="fk_user_queries_holder"), nullable=True))
    op.add_column("user_queries", sa.Column("awaiting_since", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_queries", sa.Column("alarm_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("user_queries", sa.Column("last_alarm_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_user_queries_holder_id", "user_queries", ["holder_id"])

    op.add_column("user_query_messages", sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "user_query_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("user_queries.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False, server_default="member"),  # owner | member | cc
        sa.Column("share_history", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_user_query_members_query_id", "user_query_members", ["query_id"])
    op.create_index("ix_user_query_members_user_id", "user_query_members", ["user_id"])

    op.create_table(
        "user_query_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("user_queries.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_query_events_query_id", "user_query_events", ["query_id"])

    # the people who raised the queries that exist now stay in them; the clock of an open one starts today
    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO user_query_members (query_id, user_id, kind, share_history, joined_at) "
        "SELECT id, owner_id, 'owner', 1, created_at FROM user_queries"
    ))
    bind.execute(sa.text("UPDATE user_queries SET awaiting_since = CURRENT_TIMESTAMP WHERE status = 'Open'"))


def downgrade() -> None:
    op.drop_index("ix_user_query_events_query_id", table_name="user_query_events")
    op.drop_table("user_query_events")
    op.drop_index("ix_user_query_members_user_id", table_name="user_query_members")
    op.drop_index("ix_user_query_members_query_id", table_name="user_query_members")
    op.drop_table("user_query_members")
    op.drop_column("user_query_messages", "is_private")
    op.drop_constraint("fk_user_queries_holder", "user_queries", type_="foreignkey")
    op.drop_index("ix_user_queries_holder_id", table_name="user_queries")
    for col in ("last_alarm_at", "alarm_count", "awaiting_since", "holder_id", "priority"):
        op.drop_column("user_queries", col)
