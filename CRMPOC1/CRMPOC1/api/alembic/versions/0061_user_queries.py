"""Queries: users raise questions to the Admin and Sub Admin and talk them through in a thread.

Revision ID: 0061_user_queries
Revises: 0060_engineer_extra_pincodes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0061_user_queries"
down_revision: Union[str, None] = "0060_engineer_extra_pincodes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "user_queries" not in tables:
        op.create_table(
            "user_queries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subject", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False, server_default="General"),
            sa.Column("related_to", sa.String(length=200), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Open"),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_user_queries_status", "user_queries", ["status"])
        op.create_index("ix_user_queries_owner_id", "user_queries", ["owner_id"])
        op.create_index("ix_user_queries_last_message_at", "user_queries", ["last_message_at"])
    if "user_query_messages" not in tables:
        op.create_table(
            "user_query_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("query_id", sa.Integer(), sa.ForeignKey("user_queries.id"), nullable=False),
            sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_user_query_messages_query_id", "user_query_messages", ["query_id"])
    if "user_query_reads" not in tables:
        op.create_table(
            "user_query_reads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("query_id", sa.Integer(), sa.ForeignKey("user_queries.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("last_read_message_id", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("query_id", "user_id", name="uq_user_query_reads"),
        )
        op.create_index("ix_user_query_reads_query_id", "user_query_reads", ["query_id"])
        op.create_index("ix_user_query_reads_user_id", "user_query_reads", ["user_id"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for name in ("user_query_reads", "user_query_messages", "user_queries"):
        if name in tables:
            op.drop_table(name)
