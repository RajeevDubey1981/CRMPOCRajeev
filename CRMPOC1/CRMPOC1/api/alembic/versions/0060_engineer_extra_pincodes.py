"""Users: the other pin codes an engineer also works in.

Revision ID: 0060_engineer_extra_pincodes
Revises: 0059_customer_location
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0060_engineer_extra_pincodes"
down_revision: Union[str, None] = "0059_customer_location"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "extra_pincodes" not in cols:
        op.add_column("users", sa.Column("extra_pincodes", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "extra_pincodes" in cols:
        op.drop_column("users", "extra_pincodes")
