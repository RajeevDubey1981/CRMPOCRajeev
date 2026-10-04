"""Add complaint priority (Normal / High) with who marked it and when.

Revision ID: 0047_complaint_priority
Revises: 0046_partner_year_establishment_date
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0047_complaint_priority"
down_revision: Union[str, None] = "0046_partner_year_establishment_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("complaints", sa.Column("priority", sa.String(length=10), nullable=False, server_default="Normal"))
    op.add_column("complaints", sa.Column("priority_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("complaints", sa.Column("priority_by", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_complaints_priority_by_users", "complaints", "users", ["priority_by"], ["id"])
    op.create_index("ix_complaints_priority", "complaints", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_complaints_priority", table_name="complaints")
    op.drop_constraint("fk_complaints_priority_by_users", "complaints", type_="foreignkey")
    op.drop_column("complaints", "priority_by")
    op.drop_column("complaints", "priority_at")
    op.drop_column("complaints", "priority")
