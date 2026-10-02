"""Add email_bounces table (undeliverable recipient addresses).

Revision ID: 0044_email_bounces
Revises: 0043_service_manager_assignment
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0044_email_bounces"
down_revision: Union[str, None] = "0043_service_manager_assignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_bounces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status_code", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("message_key", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_key", name="uq_email_bounces_message_key"),
    )
    op.create_index("ix_email_bounces_to_email", "email_bounces", ["to_email"])
    op.create_index("ix_email_bounces_created_at", "email_bounces", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_email_bounces_created_at", table_name="email_bounces")
    op.drop_index("ix_email_bounces_to_email", table_name="email_bounces")
    op.drop_table("email_bounces")
