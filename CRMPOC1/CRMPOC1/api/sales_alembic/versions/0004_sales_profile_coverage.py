"""Sales: coverage on the profile (All India, or states with whole state / some districts / extra pin codes).

Revision ID: 0004_sales_profile_coverage
Revises: 0003_sales_lead_attended
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sales_profile_coverage"
down_revision: Union[str, Sequence[str], None] = "0003_sales_lead_attended"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales_profile", sa.Column("coverage", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_profile", "coverage")
