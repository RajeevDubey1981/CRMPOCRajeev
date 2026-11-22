"""email_confirmations: emails typed by the caller from an SMS link

Revision ID: 0112_email_confirmations
Revises: 0111_call_purpose
"""
import sqlalchemy as sa
from alembic import op

revision = "0112_email_confirmations"
down_revision = "0111_call_purpose"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "email_confirmations" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "email_confirmations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("comp_no", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_confirmations_code", "email_confirmations", ["code"])
    op.create_index("ix_email_confirmations_mobile", "email_confirmations", ["mobile"])


def downgrade() -> None:
    if "email_confirmations" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("email_confirmations")
