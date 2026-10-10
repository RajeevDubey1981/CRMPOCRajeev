"""Sales: the role Sales Manager, and the one role-card tick that shows the Sales menu.

The Sales module keeps its own data in a separate database. The CRM database gets no Sales table: only a role row
(Sales Manager, with the same CRM rights as the Sales role) and a "sales" view tick on four role cards. Everything
a person can do inside Sales is ticked inside the Sales database.

Revision ID: 0064_sales_menu
Revises: 0063_merge_bid_and_service_unit_heads
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064_sales_menu"
down_revision: Union[str, None] = "0063_merge_bid_and_service_unit_heads"
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


def _role_id(bind, name: str):
    return bind.execute(sa.select(ROLES.c.id).where(ROLES.c.name == name)).scalar()


def upgrade() -> None:
    bind = op.get_bind()
    now = sa.func.now()

    # Sales Manager: a role of its own, starting with the same CRM rights as Sales
    manager_id = _role_id(bind, "sales_manager")
    if manager_id is None:
        bind.execute(ROLES.insert().values(name="sales_manager", description="Sales Manager: sees the whole sales team in Sales", created_at=now, updated_at=now))
        manager_id = _role_id(bind, "sales_manager")
        sales_id = _role_id(bind, "sales")
        if sales_id is not None:
            rows = bind.execute(sa.select(PERMS).where(PERMS.c.role_id == sales_id, PERMS.c.module != "sales")).fetchall()
            for r in rows:
                bind.execute(PERMS.insert().values(
                    role_id=manager_id, module=r.module, sub_module=r.sub_module, can_view=r.can_view, can_create=r.can_create,
                    can_edit=r.can_edit, can_delete=r.can_delete, can_export=r.can_export,
                ))

    # the one tick that shows the Sales menu
    for name, flags in (
        ("admin", (True, True, True, True, True)), ("sub_admin", (True, False, False, False, False)),
        ("sales", (True, False, False, False, False)), ("sales_manager", (True, False, False, False, False)),
    ):
        rid = _role_id(bind, name)
        if rid is None:
            continue
        exists = bind.execute(sa.select(PERMS.c.role_id).where(PERMS.c.role_id == rid, PERMS.c.module == "sales", PERMS.c.sub_module.is_(None))).first()
        if exists:
            continue
        bind.execute(PERMS.insert().values(
            role_id=rid, module="sales", sub_module=None, can_view=flags[0], can_create=flags[1], can_edit=flags[2],
            can_delete=flags[3], can_export=flags[4],
        ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'sales'"))
    manager_id = _role_id(bind, "sales_manager")
    if manager_id is not None:
        in_use = bind.execute(sa.text("SELECT COUNT(*) FROM users WHERE role = 'sales_manager'")).scalar() or 0
        if not in_use:
            bind.execute(sa.text("DELETE FROM permissions WHERE role_id = :r"), {"r": manager_id})
            bind.execute(ROLES.delete().where(ROLES.c.id == manager_id))
