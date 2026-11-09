"""mk_campaign_log: unique (campaign_id, contact_key) -- backstop against double-send (security review)

Revision ID: 0015_campaign_log_unique_contact
Revises: 0014_audience_csd_tier
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_campaign_log_unique_contact"
down_revision: Union[str, Sequence[str], None] = "0014_audience_csd_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_unique_constraints("mk_campaign_log")}
    if "uq_mk_campaign_log_campaign_contact" not in existing:
        # A handful of pre-existing duplicate (campaign_id, contact_key) rows (from before this
        # lock existed) would otherwise fail the constraint add -- keep only the earliest of each.
        op.execute(
            """
            DELETE t1 FROM mk_campaign_log t1
            INNER JOIN mk_campaign_log t2
                ON t1.campaign_id = t2.campaign_id
                AND t1.contact_key = t2.contact_key
                AND t1.id > t2.id
            """
        )
        op.create_unique_constraint(
            "uq_mk_campaign_log_campaign_contact", "mk_campaign_log", ["campaign_id", "contact_key"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_mk_campaign_log_campaign_contact", "mk_campaign_log", type_="unique")
