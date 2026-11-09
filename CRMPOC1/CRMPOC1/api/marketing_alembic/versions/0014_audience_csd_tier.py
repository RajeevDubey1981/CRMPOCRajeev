"""marketing audiences: csd_tier filter (retailer/end on CSD, govt on GeM)

Revision ID: 0014_audience_csd_tier
Revises: 0013_campaign_interest_fields
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_audience_csd_tier"
down_revision: Union[str, Sequence[str], None] = "0013_campaign_interest_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mk_audience")}
    if "csd_tier" not in columns:
        op.add_column("mk_audience", sa.Column("csd_tier", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("mk_audience", "csd_tier")
