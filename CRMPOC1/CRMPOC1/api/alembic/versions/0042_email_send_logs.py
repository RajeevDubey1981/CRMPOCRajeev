"""Add email_send_logs audit table.

Revision ID: 0042_email_send_logs
Revises: 0041_ensure_complaint_model_masters
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0042_email_send_logs"
down_revision: Union[str, None] = "0041_ensure_complaint_model_masters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_send_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("template", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("skip_reason", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_send_logs_to_email", "email_send_logs", ["to_email"])
    op.create_index("ix_email_send_logs_template", "email_send_logs", ["template"])
    op.create_index("ix_email_send_logs_status", "email_send_logs", ["status"])
    op.create_index("ix_email_send_logs_created_at", "email_send_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_email_send_logs_created_at", table_name="email_send_logs")
    op.drop_index("ix_email_send_logs_status", table_name="email_send_logs")
    op.drop_index("ix_email_send_logs_template", table_name="email_send_logs")
    op.drop_index("ix_email_send_logs_to_email", table_name="email_send_logs")
    op.drop_table("email_send_logs")
