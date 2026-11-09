"""sales: csd_tier on the lead -- retailer/end on a CSD lead, govt on a GeM lead

Revision ID: 0007_lead_csd_tier
Revises: 0006_lead_campaign_reply
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_lead_csd_tier"
down_revision: Union[str, Sequence[str], None] = "0006_lead_campaign_reply"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("sales_lead")}
    if "csd_tier" not in columns:
        op.add_column("sales_lead", sa.Column("csd_tier", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_lead", "csd_tier")
