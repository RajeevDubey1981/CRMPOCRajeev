"""marketing: the STOP / consent list

Revision ID: 0006_marketing_consent
Revises: 0005_marketing_banner_image
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_marketing_consent"
down_revision: Union[str, Sequence[str], None] = "0005_marketing_banner_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mk_consent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_key", sa.String(length=255), nullable=False),
        sa.Column("contact_display", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("reason", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("contact_key", "channel", name="uq_mk_consent_contact_channel"),
    )
    op.create_index("ix_mk_consent_contact_key", "mk_consent", ["contact_key"])


def downgrade() -> None:
    op.drop_index("ix_mk_consent_contact_key", table_name="mk_consent")
    op.drop_table("mk_consent")
