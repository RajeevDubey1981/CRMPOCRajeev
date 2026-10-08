"""Users: pin code, state and district (where an engineer works).

Revision ID: 0058_user_location
Revises: 0057_hide_override_remarks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058_user_location"
down_revision: Union[str, None] = "0057_hide_override_remarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "pincode" not in cols:
        op.add_column("users", sa.Column("pincode", sa.String(length=10), nullable=True))
        op.create_index("ix_users_pincode", "users", ["pincode"])
    if "state" not in cols:
        op.add_column("users", sa.Column("state", sa.String(length=100), nullable=True))
    if "district" not in cols:
        op.add_column("users", sa.Column("district", sa.String(length=100), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "pincode" in cols:
        op.drop_index("ix_users_pincode", table_name="users")
        op.drop_column("users", "pincode")
    if "state" in cols:
        op.drop_column("users", "state")
    if "district" in cols:
        op.drop_column("users", "district")
