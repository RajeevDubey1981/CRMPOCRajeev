"""Add document upload link expiry + reminder tracking to installation_requests.

Revision ID: 0105_installation_doc_link_expiry
Revises: 0104_courier_is_active
Create Date: 2026-11-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0105_installation_doc_link_expiry"
down_revision = "0104_courier_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("installation_requests", sa.Column("document_access_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("installation_requests", sa.Column("document_reminder_1_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("installation_requests", sa.Column("document_reminder_2_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("installation_requests", sa.Column("document_expired_notified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("installation_requests", "document_expired_notified_at")
    op.drop_column("installation_requests", "document_reminder_2_sent_at")
    op.drop_column("installation_requests", "document_reminder_1_sent_at")
    op.drop_column("installation_requests", "document_access_token_expires_at")
