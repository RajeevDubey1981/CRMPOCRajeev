"""marketing: a per-recipient interest form link that writes onto their existing Sales lead

Revision ID: 0012_campaign_interest_form
Revises: 0011_campaign_batching
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_campaign_interest_form"
down_revision: Union[str, Sequence[str], None] = "0011_campaign_batching"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mk_campaign")}
    if "collect_interest" not in columns:
        op.add_column("mk_campaign", sa.Column("collect_interest", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not sa.inspect(bind).has_table("mk_lead_interest_token"):
        op.create_table(
            "mk_lead_interest_token",
            sa.Column("token", sa.String(length=64), primary_key=True),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("lead_id", sa.Integer(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_interest", sa.String(length=10), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_mk_lead_interest_token_campaign_id", "mk_lead_interest_token", ["campaign_id"])
        op.create_index("ix_mk_lead_interest_token_lead_id", "mk_lead_interest_token", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_mk_lead_interest_token_lead_id", table_name="mk_lead_interest_token")
    op.drop_index("ix_mk_lead_interest_token_campaign_id", table_name="mk_lead_interest_token")
    op.drop_table("mk_lead_interest_token")
    op.drop_column("mk_campaign", "collect_interest")
