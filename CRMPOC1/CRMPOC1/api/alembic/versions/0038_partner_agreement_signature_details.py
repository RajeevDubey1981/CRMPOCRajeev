"""Add partner agreement signature detail fields.

Revision ID: 0038_partner_agreement_signature_details
Revises: 0037_partner_agreements
Create Date: 2026-09-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0038_partner_agreement_signature_details"
down_revision: Union[str, None] = "0037_partner_agreements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("partner_agreements", sa.Column("signed_method", sa.String(length=50), nullable=True))
    op.add_column("partner_agreements", sa.Column("signed_destination", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("partner_agreements", "signed_destination")
    op.drop_column("partner_agreements", "signed_method")
