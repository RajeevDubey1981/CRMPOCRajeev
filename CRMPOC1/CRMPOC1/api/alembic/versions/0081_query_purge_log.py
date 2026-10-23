"""Keep a bare record (number and dates, never the content) of each conversation deleted six months after it closed.

Revision ID: 0081_query_purge_log
Revises: 0080_query_attachments
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0081_query_purge_log"
down_revision: Union[str, None] = "0080_query_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_query_purges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_no", sa.String(20), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_user_query_purges_query_no", "user_query_purges", ["query_no"])


def downgrade() -> None:
    op.drop_index("ix_user_query_purges_query_no", table_name="user_query_purges")
    op.drop_table("user_query_purges")
