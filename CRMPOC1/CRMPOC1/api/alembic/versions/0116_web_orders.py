"""web_orders: orders placed on the website, synced into the CRM, with the web_orders permission for admin

Revision ID: 0116_web_orders
Revises: 0115_whatsapp_knowledge
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import LONGTEXT

revision = "0116_web_orders"
down_revision = "0115_whatsapp_knowledge"
branch_labels = None
depends_on = None


def _has(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _dt(name: str, **kw) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has("web_orders"):
        op.create_table(
            "web_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("site_order_id", sa.Integer(), nullable=False),
            sa.Column("order_number", sa.String(100)),
            sa.Column("site_user_id", sa.Integer()),
            sa.Column("customer_name", sa.String(255)),
            sa.Column("email", sa.String(255)),
            sa.Column("mobile", sa.String(30)),
            sa.Column("mobile10", sa.String(10)),
            sa.Column("company_name", sa.String(255)),
            sa.Column("gst_number", sa.String(50)),
            sa.Column("shipping_address", sa.Text()),
            sa.Column("billing_address", sa.Text()),
            sa.Column("coupon_code", sa.String(100)),
            sa.Column("discount_amount", sa.Numeric(12, 2)),
            sa.Column("subtotal", sa.Numeric(12, 2)),
            sa.Column("shipping", sa.Numeric(12, 2)),
            sa.Column("tax", sa.String(100)),
            sa.Column("total", sa.Numeric(12, 2)),
            sa.Column("status", sa.String(50)),
            sa.Column("payment_status", sa.String(50)),
            sa.Column("payment_method", sa.String(50)),
            sa.Column("razorpay_order_id", sa.String(100)),
            sa.Column("payment_id", sa.String(100)),
            _dt("stock_deducted_at"),
            _dt("site_created_at"),
            _dt("site_updated_at"),
            sa.Column("extra_json", sa.Text().with_variant(LONGTEXT(), "mysql")),
            _dt("first_synced_at", nullable=False),
            _dt("last_synced_at", nullable=False),
        )
        op.create_index("ix_web_orders_site_order_id", "web_orders", ["site_order_id"], unique=True)
        for col in ("order_number", "customer_name", "mobile", "mobile10", "status", "payment_status", "site_created_at", "last_synced_at"):
            op.create_index(f"ix_web_orders_{col}", "web_orders", [col])
    fk = lambda: sa.Column("web_order_id", sa.Integer(), sa.ForeignKey("web_orders.id", ondelete="CASCADE"), nullable=False)  # noqa: E731
    if not _has("web_order_items"):
        op.create_table(
            "web_order_items",
            sa.Column("id", sa.Integer(), primary_key=True), fk(),
            sa.Column("site_item_id", sa.Integer()), sa.Column("product_id", sa.String(100)), sa.Column("product_name", sa.String(255)),
            sa.Column("product_info", sa.Text()), sa.Column("price", sa.Numeric(12, 2)), sa.Column("quantity", sa.Integer()),
            sa.Column("delivery_date", sa.String(100)), sa.Column("time_slot", sa.String(100)),
        )
        op.create_index("ix_web_order_items_web_order_id", "web_order_items", ["web_order_id"])
    if not _has("web_order_addresses"):
        op.create_table(
            "web_order_addresses",
            sa.Column("id", sa.Integer(), primary_key=True), fk(),
            sa.Column("kind", sa.String(20)), sa.Column("title", sa.String(100)), sa.Column("full_name", sa.String(255)),
            sa.Column("email", sa.String(255)), sa.Column("mobile", sa.String(30)), sa.Column("address_line1", sa.String(255)),
            sa.Column("address_line2", sa.String(255)), sa.Column("city", sa.String(100)), sa.Column("state", sa.String(100)),
            sa.Column("pincode", sa.String(20)), sa.Column("country", sa.String(100)),
        )
        op.create_index("ix_web_order_addresses_web_order_id", "web_order_addresses", ["web_order_id"])
    if not _has("web_order_payments"):
        op.create_table(
            "web_order_payments",
            sa.Column("id", sa.Integer(), primary_key=True), fk(),
            sa.Column("site_payment_log_id", sa.Integer()), sa.Column("razorpay_order_id", sa.String(100)), sa.Column("payment_id", sa.String(100)),
            sa.Column("status", sa.String(50)), sa.Column("amount", sa.Numeric(12, 2)), sa.Column("currency", sa.String(10)),
            _dt("attempted_at"), sa.Column("response", sa.Text()),
        )
        op.create_index("ix_web_order_payments_web_order_id", "web_order_payments", ["web_order_id"])
    if not _has("web_order_events"):
        op.create_table(
            "web_order_events",
            sa.Column("id", sa.Integer(), primary_key=True), fk(),
            sa.Column("kind", sa.String(30), nullable=False), sa.Column("old_value", sa.String(100)), sa.Column("new_value", sa.String(100)),
            _dt("happened_at", nullable=False), _dt("seen_at", nullable=False),
        )
        op.create_index("ix_web_order_events_web_order_id", "web_order_events", ["web_order_id"])
        op.create_index("ix_web_order_events_happened_at", "web_order_events", ["happened_at"])

    # Role card: admin gets the web_orders module. Other roles are switched on from the Permissions page.
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
    perms = sa.table(
        "permissions",
        sa.column("role_id", sa.Integer), sa.column("module", sa.String), sa.column("sub_module", sa.String),
        sa.column("can_view", sa.Boolean), sa.column("can_create", sa.Boolean), sa.column("can_edit", sa.Boolean),
        sa.column("can_delete", sa.Boolean), sa.column("can_export", sa.Boolean),
    )
    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for module in ("web_orders",):
        if role_id is not None and not bind.execute(
            sa.select(perms.c.role_id).where(perms.c.role_id == role_id, perms.c.module == module, perms.c.sub_module.is_(None))
        ).first():
            op.bulk_insert(perms, [{"role_id": role_id, "module": module, "sub_module": None,
                                    "can_view": True, "can_create": False, "can_edit": False, "can_delete": False, "can_export": True}])


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'web_orders'"))
    for table in ("web_order_events", "web_order_payments", "web_order_addresses", "web_order_items", "web_orders"):
        if _has(table):
            op.drop_table(table)
