"""Complaints, installation requests and service requests: the customer's pin code, state and district.

Revision ID: 0059_customer_location
Revises: 0058_user_location
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0059_customer_location"
down_revision: Union[str, None] = "0058_user_location"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("complaints", "installation_requests", "service_requests")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "pincode" not in cols:
            op.add_column(table, sa.Column("pincode", sa.String(length=10), nullable=True))
            op.create_index(f"ix_{table}_pincode", table, ["pincode"])
        if "state" not in cols:
            op.add_column(table, sa.Column("state", sa.String(length=100), nullable=True))
        if "district" not in cols:
            op.add_column(table, sa.Column("district", sa.String(length=100), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "pincode" in cols:
            op.drop_index(f"ix_{table}_pincode", table_name=table)
            op.drop_column(table, "pincode")
        if "state" in cols:
            op.drop_column(table, "state")
        if "district" in cols:
            op.drop_column(table, "district")
