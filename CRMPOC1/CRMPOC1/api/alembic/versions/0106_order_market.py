"""orders: which market the sale came through (gem, csd, retail, service, dealer), for Marketing Audiences

Revision ID: 0106_order_market
Revises: 0105_installation_doc_link_expiry
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0106_order_market"
down_revision: Union[str, Sequence[str], None] = "0105_installation_doc_link_expiry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("market", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_orders_market"), "orders", ["market"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_market"), table_name="orders")
    op.drop_column("orders", "market")
