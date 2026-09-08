"""add sub_module to permissions

Revision ID: 0002_submodule
Revises: 0001_initial
Create Date: 2026-05-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_submodule"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "permissions",
        sa.Column("sub_module", sa.String(100), nullable=True),
    )
    # MySQL doesn't support expressions directly in CREATE UNIQUE INDEX, so a
    # generated column is used to collapse NULL sub_module to '' before indexing.
    op.execute(
        "ALTER TABLE permissions "
        "ADD COLUMN sub_module_key VARCHAR(100) "
        "GENERATED ALWAYS AS (COALESCE(sub_module, '')) STORED"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_permissions_role_module_sub "
        "ON permissions (role_id, module, sub_module_key)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_permissions_role_module_sub ON permissions")
    op.execute("ALTER TABLE permissions DROP COLUMN sub_module_key")
    op.drop_column("permissions", "sub_module")
