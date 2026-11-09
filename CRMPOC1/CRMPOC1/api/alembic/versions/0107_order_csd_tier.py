"""orders: csd_tier -- on a CSD order, retailer (depot/URC/canteen) vs end (serving personnel); on a GeM
order, govt (an actual government buyer). Backfilled on existing orders by scripts/backfill_csd_tier.py.

Revision ID: 0107_order_csd_tier
Revises: 0106_order_market
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0107_order_csd_tier"
down_revision: Union[str, Sequence[str], None] = "0106_order_market"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("csd_tier", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "csd_tier")
