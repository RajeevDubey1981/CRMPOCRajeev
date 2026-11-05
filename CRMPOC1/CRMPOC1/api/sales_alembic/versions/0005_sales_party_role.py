"""Sales: party_role on the lead (dealer, distributor, customer, engineer, franchisee), and two new lead
types (service engineer, service franchisee) for the Marketing Audiences feature.

Revision ID: 0005_sales_party_role
Revises: 0004_sales_profile_coverage
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_sales_party_role"
down_revision: Union[str, Sequence[str], None] = "0004_sales_profile_coverage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_TYPES = [
    {"key": "service_engineer", "label": "Service Engineer", "color": "#0ea5e9", "sort_order": 90, "is_active": True, "is_builtin": True},
    {"key": "service_franchisee", "label": "Service Franchisee", "color": "#f97316", "sort_order": 91, "is_active": True, "is_builtin": True},
]


def upgrade() -> None:
    op.add_column("sales_lead", sa.Column("party_role", sa.String(length=20), nullable=True))
    sales_lead_type = sa.table(
        "sales_lead_type",
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("color", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("is_builtin", sa.Boolean),
    )
    op.bulk_insert(sales_lead_type, _NEW_TYPES)


def downgrade() -> None:
    conn = op.get_bind()
    for row in _NEW_TYPES:
        conn.execute(sa.text("DELETE FROM sales_lead_type WHERE `key` = :key"), {"key": row["key"]})
    op.drop_column("sales_lead", "party_role")
