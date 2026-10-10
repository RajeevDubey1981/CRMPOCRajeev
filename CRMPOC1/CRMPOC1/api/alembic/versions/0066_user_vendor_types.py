"""Users: the types of a vendor (GeM, CSD, Retail, SSD ...), several at once.

Revision ID: 0066_user_vendor_types
Revises: 0065_user_coverage_skills
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0066_user_vendor_types"
down_revision: Union[str, None] = "0065_user_coverage_skills"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "vendor_types" not in cols:
        op.add_column("users", sa.Column("vendor_types", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "vendor_types" in cols:
        op.drop_column("users", "vendor_types")
