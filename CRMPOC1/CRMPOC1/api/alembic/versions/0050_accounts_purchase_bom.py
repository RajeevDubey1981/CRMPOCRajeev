"""Accounts A: suppliers, purchase orders, BOM, assembly orders, item make-or-buy and the GRN to PO link.

Revision ID: 0050_accounts_purchase_bom
Revises: 0049_store_dispatch
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0050_accounts_purchase_bom"
down_revision: Union[str, None] = "0049_store_dispatch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("item_masters", sa.Column("source", sa.String(length=10), nullable=False, server_default="Buy"))
    op.add_column("item_masters", sa.Column("item_type", sa.String(length=20), nullable=True))
    op.add_column("item_masters", sa.Column("gst_rate", sa.Numeric(5, 2), nullable=True))

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("state_code", sa.String(length=2), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_msme", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("msme_no", sa.String(length=50), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("bank_account", sa.String(length=40), nullable=True),
        sa.Column("bank_ifsc", sa.String(length=11), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        *_stamps(),
        sa.UniqueConstraint("gstin", name="uq_suppliers_gstin"),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])

    op.create_table(
        "boms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("labour_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("overhead_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("activated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        *_stamps(),
    )
    op.create_index("ix_boms_item_id", "boms", ["item_id"])
    op.create_index("ix_boms_status", "boms", ["status"])

    op.create_table(
        "bom_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bom_id", sa.Integer(), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("qty", sa.Numeric(10, 3), nullable=False, server_default="1"),
        sa.Column("scrap_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_bom_lines_bom_id", "bom_lines", ["bom_id"])
    op.create_index("ix_bom_lines_component_item_id", "bom_lines", ["component_item_id"])

    op.create_table(
        "assembly_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asm_no", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("bom_id", sa.Integer(), sa.ForeignKey("boms.id"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Planned"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_stamps(),
    )
    op.create_index("ix_assembly_orders_asm_no", "assembly_orders", ["asm_no"], unique=True)
    op.create_index("ix_assembly_orders_item_id", "assembly_orders", ["item_id"])
    op.create_index("ix_assembly_orders_status", "assembly_orders", ["status"])

    op.create_table(
        "assembly_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assembly_id", sa.Integer(), sa.ForeignKey("assembly_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finished_serial", sa.String(length=100), nullable=True),
        sa.Column("component_item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("component_serial", sa.String(length=100), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index("ix_assembly_parts_assembly_id", "assembly_parts", ["assembly_id"])
    op.create_index("ix_assembly_parts_finished_serial", "assembly_parts", ["finished_serial"])
    op.create_index("ix_assembly_parts_component_serial", "assembly_parts", ["component_serial"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("po_no", sa.String(length=30), nullable=False),
        sa.Column("po_date", sa.Date(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Draft"),
        sa.Column("place_of_supply", sa.String(length=100), nullable=True),
        sa.Column("intra_state", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("taxable_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("cgst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("sgst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("igst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_stamps(),
    )
    op.create_index("ix_purchase_orders_po_no", "purchase_orders", ["po_no"], unique=True)
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("po_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item_masters.id"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("hsn_code", sa.String(length=20), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(5, 2), nullable=False, server_default="18"),
        sa.Column("taxable", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("received_qty", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_purchase_order_lines_po_id", "purchase_order_lines", ["po_id"])
    op.create_index("ix_purchase_order_lines_item_id", "purchase_order_lines", ["item_id"])

    op.add_column("store_grns", sa.Column("po_id", sa.Integer(), sa.ForeignKey("purchase_orders.id"), nullable=True))
    op.create_index("ix_store_grns_po_id", "store_grns", ["po_id"])


def downgrade() -> None:
    op.drop_index("ix_store_grns_po_id", table_name="store_grns")
    op.drop_column("store_grns", "po_id")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("assembly_parts")
    op.drop_table("assembly_orders")
    op.drop_table("bom_lines")
    op.drop_table("boms")
    op.drop_table("suppliers")
    op.drop_column("item_masters", "gst_rate")
    op.drop_column("item_masters", "item_type")
    op.drop_column("item_masters", "source")
