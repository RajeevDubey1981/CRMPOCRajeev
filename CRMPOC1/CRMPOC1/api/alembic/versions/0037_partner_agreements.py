"""Add partner_agreements table for OTP-signed service agreements.

Revision ID: 0037_partner_agreements
Revises: 0036_partner_registration_email_controls
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0037_partner_agreements"
down_revision: Union[str, None] = "0036_partner_registration_email_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "partner_agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("agreement_no", sa.String(length=50), nullable=False),
        sa.Column("agreement_version", sa.String(length=10), nullable=False, server_default="1.0"),
        sa.Column("access_token", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("otp_code", sa.String(length=10), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("otp_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_send_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["registration_id"], ["partner_registrations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_partner_agreements_registration_id"), "partner_agreements", ["registration_id"])
    op.create_index(op.f("ix_partner_agreements_agreement_no"), "partner_agreements", ["agreement_no"], unique=True)
    op.create_index(op.f("ix_partner_agreements_access_token"), "partner_agreements", ["access_token"], unique=True)
    op.create_index(op.f("ix_partner_agreements_email"), "partner_agreements", ["email"])


def downgrade() -> None:
    op.drop_index(op.f("ix_partner_agreements_email"), table_name="partner_agreements")
    op.drop_index(op.f("ix_partner_agreements_access_token"), table_name="partner_agreements")
    op.drop_index(op.f("ix_partner_agreements_agreement_no"), table_name="partner_agreements")
    op.drop_index(op.f("ix_partner_agreements_registration_id"), table_name="partner_agreements")
    op.drop_table("partner_agreements")
