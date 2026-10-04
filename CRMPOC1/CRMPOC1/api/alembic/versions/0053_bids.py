"""Bid management: bids, history, vendor requests, reminder log, users.can_manage_bids, and the bids permission rows.

Revision ID: 0053_bids
Revises: 0052_remove_store_accounts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0053_bids"
down_revision: Union[str, None] = "0052_remove_store_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("CURRENT_TIMESTAMP")


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "can_manage_bids" not in user_cols:
        op.add_column("users", sa.Column("can_manage_bids", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    if not _has_table("bids"):
        op.create_table(
            "bids",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bid_number", sa.String(length=120), nullable=False),
            sa.Column("bid_type", sa.String(length=20), nullable=False, server_default="GeM"),
            sa.Column("portal", sa.String(length=120), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("department", sa.String(length=255), nullable=True),
            sa.Column("product_category", sa.String(length=100), nullable=True),
            sa.Column("product_type", sa.String(length=100), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("estimated_value", sa.Numeric(14, 2), nullable=True),
            sa.Column("publish_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("opening_date", sa.Date(), nullable=True),
            sa.Column("emd_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("emd_mode", sa.String(length=60), nullable=True),
            sa.Column("emd_exempt", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("epbg_details", sa.String(length=255), nullable=True),
            sa.Column("tender_fee", sa.Numeric(14, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Open"),
            sa.Column("vendor_id", sa.Integer(), nullable=True),
            sa.Column("is_self", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("confirm_by", sa.Date(), nullable=True),
            sa.Column("submit_by", sa.Date(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submission_ref", sa.String(length=160), nullable=True),
            sa.Column("result_note", sa.Text(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_bids_bid_number", "bids", ["bid_number"], unique=True)
        op.create_index("ix_bids_product_category", "bids", ["product_category"])
        op.create_index("ix_bids_end_date", "bids", ["end_date"])
        op.create_index("ix_bids_status", "bids", ["status"])
        op.create_index("ix_bids_vendor_id", "bids", ["vendor_id"])

    if not _has_table("bid_events"):
        op.create_table(
            "bid_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bid_id", sa.Integer(), nullable=False),
            sa.Column("at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
            sa.Column("actor_name", sa.String(length=255), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["bid_id"], ["bids.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_bid_events_bid_id", "bid_events", ["bid_id"])

    if not _has_table("bid_requests"):
        op.create_table(
            "bid_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bid_id", sa.Integer(), nullable=True),
            sa.Column("bid_number", sa.String(length=120), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Requested"),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("requested_by_id", sa.Integer(), nullable=True),
            sa.Column("decided_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["bid_id"], ["bids.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_bid_requests_bid_id", "bid_requests", ["bid_id"])
        op.create_index("ix_bid_requests_bid_number", "bid_requests", ["bid_number"])
        op.create_index("ix_bid_requests_vendor_id", "bid_requests", ["vendor_id"])
        op.create_index("ix_bid_requests_status", "bid_requests", ["status"])

    if not _has_table("bid_reminders"):
        op.create_table(
            "bid_reminders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bid_id", sa.Integer(), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=True),
            sa.Column("sent_on", sa.Date(), nullable=False),
            sa.Column("sent_to", sa.String(length=255), nullable=True),
            sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["bid_id"], ["bids.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("bid_id", "sent_on", name="uq_bid_reminders_bid_day"),
        )
        op.create_index("ix_bid_reminders_bid_id", "bid_reminders", ["bid_id"])

    # Role card rows: admin full access, vendor view / create / edit (their own bids and requests only).
    # Other roles never get a row: managers are decided by the user's tick, see services/bid_access.
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
    perms = sa.table(
        "permissions",
        sa.column("role_id", sa.Integer), sa.column("module", sa.String), sa.column("sub_module", sa.String),
        sa.column("can_view", sa.Boolean), sa.column("can_create", sa.Boolean), sa.column("can_edit", sa.Boolean),
        sa.column("can_delete", sa.Boolean), sa.column("can_export", sa.Boolean),
    )
    for role_name, flags in (("admin", (True, True, True, True, True)), ("vendor", (True, True, True, False, False))):
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
        if role_id is None:
            continue
        exists = bind.execute(
            sa.select(perms.c.role_id).where(perms.c.role_id == role_id, perms.c.module == "bids", perms.c.sub_module.is_(None))
        ).first()
        if exists:
            continue
        op.bulk_insert(perms, [{
            "role_id": role_id, "module": "bids", "sub_module": None,
            "can_view": flags[0], "can_create": flags[1], "can_edit": flags[2], "can_delete": flags[3], "can_export": flags[4],
        }])


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'bids'"))
    for table in ("bid_reminders", "bid_requests", "bid_events", "bids"):
        if _has_table(table):
            op.drop_table(table)
    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "can_manage_bids" in user_cols:
        op.drop_column("users", "can_manage_bids")
