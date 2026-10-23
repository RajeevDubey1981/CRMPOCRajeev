"""Let a Query message carry pasted pictures and files (screenshots and the like).

Revision ID: 0080_query_attachments
Revises: 0079_observation_misc_required
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0080_query_attachments"
down_revision: Union[str, None] = "0079_observation_misc_required"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_query_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("user_query_messages.id"), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_query_attachments_message_id", "user_query_attachments", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_user_query_attachments_message_id", table_name="user_query_attachments")
    op.drop_table("user_query_attachments")
