"""Marketing: the role "marketing_manager" next to "marketing" (a Marketing user and a Marketing manager).

Revision ID: 0068_marketing_manager_role
Revises: 0067_marketing_menu
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0068_marketing_manager_role"
down_revision: Union[str, None] = "0067_marketing_menu"
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
    rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing_manager")).scalar()
    if rid is None:
        now = sa.func.now()
        bind.execute(ROLES.insert().values(name="marketing_manager", description="Marketing manager: approves, sees the cost, uploads lists and edits the opt-in list", created_at=now, updated_at=now))
        rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing_manager")).scalar()
        bind.execute(PERMS.insert().values(role_id=rid, module="dashboard", sub_module=None, can_view=True, can_create=False, can_edit=False, can_delete=False, can_export=False))
    # the marketing role is now the Marketing user
    bind.execute(ROLES.update().where(ROLES.c.name == "marketing").values(description="Marketing user: audiences and campaigns in the Marketing menu"))


def downgrade() -> None:
    bind = op.get_bind()
    rid = bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == "marketing_manager")).scalar()
    if rid is not None:
        in_use = bind.execute(sa.text("SELECT COUNT(*) FROM users WHERE role = 'marketing_manager'")).scalar() or 0
        if not in_use:
            bind.execute(sa.text("DELETE FROM permissions WHERE role_id = :r"), {"r": rid})
            bind.execute(ROLES.delete().where(ROLES.c.id == rid))
