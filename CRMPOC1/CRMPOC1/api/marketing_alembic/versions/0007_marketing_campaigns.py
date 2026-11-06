"""marketing: campaigns -- the actual send to a saved audience

Revision ID: 0007_marketing_campaigns
Revises: 0006_marketing_consent
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_marketing_campaigns"
down_revision: Union[str, Sequence[str], None] = "0006_marketing_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_campaign",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("audience_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="draft"),
        sa.Column("reject_reason", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mk_campaign_audience_id", "mk_campaign", ["audience_id"])
    op.create_index("ix_mk_campaign_status", "mk_campaign", ["status"])

    op.create_table(
        "mk_campaign_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("contact_key", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("contact_address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mk_campaign_log_campaign_id", "mk_campaign_log", ["campaign_id"])

    op.create_table(
        "mk_contact_touch",
        sa.Column("contact_key", sa.String(length=255), primary_key=True),
        sa.Column("last_campaign_id", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mk_contact_touch")
    op.drop_index("ix_mk_campaign_log_campaign_id", table_name="mk_campaign_log")
    op.drop_table("mk_campaign_log")
    op.drop_index("ix_mk_campaign_status", table_name="mk_campaign")
    op.drop_index("ix_mk_campaign_audience_id", table_name="mk_campaign")
    op.drop_table("mk_campaign")
