"""Marketing: the role "marketing" and the user tick "Can manage marketing".

The Marketing module keeps its data in a separate database. The CRM database gets no Marketing table: only a role
row, a tick on users (like Can manage bids), and the permission rows the role needs to log in and see the dashboard.

Revision ID: 0067_marketing_menu
Revises: 0066_user_vendor_types
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0067_marketing_menu"
down_revision: Union[str, None] = "0066_user_vendor_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("description", sa.Text),
                 sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime))
PERMS = sa.table(
    "permissions",
    sa.column("role_id", sa.Integer), sa.column("module", sa.String), sa.column("sub_module", sa.String),
    sa.column("can_view", sa.Boolean), sa.column("can_create", sa.Boolean), sa.column("can_edit", sa.Boolean),
    sa.column("can_delete", sa.Boolean), sa.column("can_export", sa.Boolean),
)


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "can_manage_marketing" not in cols:
        op.add_column("users", sa.Column("can_manage_marketing", sa.Boolean(), nullable=False, server_default="0"))
    rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing")).scalar()
    if rid is None:
        now = sa.func.now()
        bind.execute(ROLES.insert().values(name="marketing", description="Marketing: audiences, campaigns and channels in the Marketing menu", created_at=now, updated_at=now))
        rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing")).scalar()
        bind.execute(PERMS.insert().values(role_id=rid, module="dashboard", sub_module=None, can_view=True, can_create=False, can_edit=False, can_delete=False, can_export=False))


def downgrade() -> None:
    bind = op.get_bind()
    rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing")).scalar()
    if rid is not None:
        in_use = bind.execute(sa.text("SELECT COUNT(*) FROM users WHERE role = 'marketing'")).scalar() or 0
        if not in_use:
            bind.execute(sa.text("DELETE FROM permissions WHERE role_id = :r"), {"r": rid})
            bind.execute(ROLES.delete().where(ROLES.c.id == rid))
    cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "can_manage_marketing" in cols:
        op.drop_column("users", "can_manage_marketing")
