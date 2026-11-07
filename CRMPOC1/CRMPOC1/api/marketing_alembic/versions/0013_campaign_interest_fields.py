"""marketing campaigns: custom questions on the interest form, per campaign

Revision ID: 0013_campaign_interest_fields
Revises: 0012_campaign_interest_form
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_campaign_interest_fields"
down_revision: Union[str, Sequence[str], None] = "0012_campaign_interest_form"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mk_campaign")}
    if "interest_fields" not in columns:
        op.add_column("mk_campaign", sa.Column("interest_fields", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("mk_campaign", "interest_fields")
