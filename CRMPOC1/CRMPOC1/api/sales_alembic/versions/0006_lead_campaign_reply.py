"""sales: mark a lead when it replies to a Marketing campaign's interest form

Revision ID: 0006_lead_campaign_reply
Revises: 0005_sales_party_role
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_lead_campaign_reply"
down_revision: Union[str, Sequence[str], None] = "0005_sales_party_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("sales_lead")}
    if "campaign_reply_at" not in columns:
        op.add_column("sales_lead", sa.Column("campaign_reply_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("ix_sales_lead_campaign_reply_at", "sales_lead", ["campaign_reply_at"])
    if "campaign_reply_text" not in columns:
        op.add_column("sales_lead", sa.Column("campaign_reply_text", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_lead", "campaign_reply_text")
    op.drop_index("ix_sales_lead_campaign_reply_at", table_name="sales_lead")
    op.drop_column("sales_lead", "campaign_reply_at")
