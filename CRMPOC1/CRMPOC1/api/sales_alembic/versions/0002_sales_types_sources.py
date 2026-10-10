"""Sales: editable lead types, connections (sources), what they already brought in, and export-market company lists.

Revision ID: 0002_sales_types_sources
Revises: 0001_sales_initial
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_sales_types_sources"
down_revision: Union[str, Sequence[str], None] = "0001_sales_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUILTIN = [
    ("gem", "GeM", "#1d4ed8"), ("csd", "CSD", "#0e7490"), ("retail", "Retail", "#047857"), ("spare", "Spare parts", "#b45309"),
    ("dealer", "Dealer", "#7c3aed"), ("tender", "State tender", "#be185d"), ("corp", "Corporate / project", "#475569"), ("export", "Export", "#0369a1"),
]


def upgrade() -> None:
    types = op.create_table(
        "sales_lead_type",
        sa.Column("key", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=9), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(types, [
        {"key": k, "label": label, "color": color, "sort_order": (i + 1) * 10, "is_active": True, "is_builtin": True}
        for i, (k, label, color) in enumerate(BUILTIN)
    ])
    op.create_table(
        "sales_source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("default_lead_type", sa.String(length=30), nullable=True),
        sa.Column("default_owner_user_id", sa.Integer(), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ok_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("received_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_table(
        "sales_inbound",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("crm_ref", sa.String(length=80), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sales_source.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_sales_inbound"),
    )
    op.create_index(op.f("ix_sales_inbound_source_id"), "sales_inbound", ["source_id"], unique=False)
    op.create_table(
        "sales_prospect",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=True),
        sa.Column("products", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("batch", sa.String(length=60), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_prospect_country"), "sales_prospect", ["country"], unique=False)
    op.create_index(op.f("ix_sales_prospect_phone"), "sales_prospect", ["phone"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_prospect_phone"), table_name="sales_prospect")
    op.drop_index(op.f("ix_sales_prospect_country"), table_name="sales_prospect")
    op.drop_table("sales_prospect")
    op.drop_index(op.f("ix_sales_inbound_source_id"), table_name="sales_inbound")
    op.drop_table("sales_inbound")
    op.drop_table("sales_source")
    op.drop_table("sales_lead_type")
