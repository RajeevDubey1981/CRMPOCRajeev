"""Remove the Store and Accounts preview work: tables, extra columns, permissions and their roles.

Those screens were only ever meant as a preview and went live by mistake. Migrations 0048 to 0050 stay in the
history because some databases are already at 0050; this one takes everything they added away again. It checks
before every step, so it is safe on a database that never had them.

Revision ID: 0052_remove_store_accounts
Revises: 0051_merge_installation_service_user_and_accounts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052_remove_store_accounts"
down_revision: Union[str, None] = "0051_merge_installation_service_user_and_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# children first, so no foreign key is left pointing at a dropped table
TABLES = [
    "store_ledger",
    "store_stock",
    "store_dispatches",
    "store_grn_lines",
    "store_grns",
    "assembly_parts",
    "assembly_orders",
    "bom_lines",
    "boms",
    "purchase_order_lines",
    "purchase_orders",
    "suppliers",
]

COLUMNS = [
    ("orders", "fulfilment"),
    ("item_masters", "gst_rate"),
    ("item_masters", "item_type"),
    ("item_masters", "source"),
]

MODULES = [
    "store_receiving", "store_approval", "store_stock", "store_dispatch",
    "acc_items", "acc_purchase", "acc_po_approval", "acc_assembly",
]

# role name and the start of the description it was created with, so a role someone made by hand is left alone
ROLES = [
    ("store_keeper", "Store Keeper - "),
    ("store_manager", "Store Manager - "),
    ("accounts_manager", "Accounts Manager - "),
    ("accounts_executive", "Accounts Executive - "),
    ("purchase_officer", "Purchase Officer - "),
    ("auditor", "Auditor - "),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "permissions" in tables:
        bind.execute(
            sa.text("DELETE FROM permissions WHERE module IN :mods").bindparams(sa.bindparam("mods", expanding=True)),
            {"mods": MODULES},
        )
    if "roles" in tables:
        for name, prefix in ROLES:
            row = bind.execute(sa.text("SELECT id, description FROM roles WHERE name = :n"), {"n": name}).first()
            if row is None or not (row[1] or "").startswith(prefix):
                continue
            in_use = 0
            if "users" in tables:
                in_use = bind.execute(sa.text("SELECT COUNT(*) FROM users WHERE role = :n"), {"n": name}).scalar() or 0
            if in_use:
                continue  # somebody was given this role, so it stays until they are moved
            bind.execute(sa.text("DELETE FROM permissions WHERE role_id = :i"), {"i": row[0]})
            bind.execute(sa.text("DELETE FROM roles WHERE id = :i"), {"i": row[0]})

    for table in TABLES:
        if table in tables:
            op.drop_table(table)

    for table, column in COLUMNS:
        if table in tables and column in {c["name"] for c in sa.inspect(bind).get_columns(table)}:
            with op.batch_alter_table(table) as batch:
                batch.drop_column(column)


def downgrade() -> None:
    # The removed data cannot be brought back. Restore a database backup if it is ever needed.
    pass
