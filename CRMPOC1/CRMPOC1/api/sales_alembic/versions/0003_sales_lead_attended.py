"""Sales: the 'attended' mark of the lead workflow (when the person who has the lead last acted, and how many calls).

Revision ID: 0003_sales_lead_attended
Revises: 0002_sales_types_sources
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sales_lead_attended"
down_revision: Union[str, Sequence[str], None] = "0002_sales_types_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales_lead", sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales_lead", sa.Column("last_action_by", sa.Integer(), nullable=True))
    op.add_column("sales_lead", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(op.f("ix_sales_lead_last_action_at"), "sales_lead", ["last_action_at"], unique=False)
    # leads that already had a call: mark them attended and count the calls
    op.execute("UPDATE sales_lead SET last_action_at = last_contact_at WHERE last_contact_at IS NOT NULL")
    op.execute("UPDATE sales_lead SET attempts = (SELECT COUNT(*) FROM sales_lead_activity a WHERE a.lead_id = sales_lead.id AND a.kind = 'call')")


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_lead_last_action_at"), table_name="sales_lead")
    op.drop_column("sales_lead", "attempts")
    op.drop_column("sales_lead", "last_action_by")
    op.drop_column("sales_lead", "last_action_at")
