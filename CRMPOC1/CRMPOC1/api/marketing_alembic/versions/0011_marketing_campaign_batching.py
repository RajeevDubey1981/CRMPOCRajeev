"""marketing campaigns: send in batches (25 at a time, 20 minutes apart), not all at once

Revision ID: 0011_campaign_batching
Revises: 0010_marketing_campaign_offer
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_campaign_batching"
down_revision: Union[str, Sequence[str], None] = "0010_marketing_campaign_offer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mk_campaign")}
    if "next_batch_at" not in columns:
        op.add_column("mk_campaign", sa.Column("next_batch_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("ix_mk_campaign_next_batch_at", "mk_campaign", ["next_batch_at"])


def downgrade() -> None:
    op.drop_index("ix_mk_campaign_next_batch_at", table_name="mk_campaign")
    op.drop_column("mk_campaign", "next_batch_at")
