"""Users: where an engineer works as All India or states (whole state / districts / extra pin codes), and the skill categories.

Revision ID: 0065_user_coverage_skills
Revises: 0064_sales_menu
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_user_coverage_skills"
down_revision: Union[str, None] = "0064_sales_menu"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "coverage" not in cols:
        op.add_column("users", sa.Column("coverage", sa.Text(), nullable=True))
    if "skills" not in cols:
        op.add_column("users", sa.Column("skills", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "skills" in cols:
        op.drop_column("users", "skills")
    if "coverage" in cols:
        op.drop_column("users", "coverage")
