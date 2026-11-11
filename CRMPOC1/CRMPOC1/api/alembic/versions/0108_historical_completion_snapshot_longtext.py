"""Allow large historical completion audit snapshots.

Revision ID: 0108_historical_completion_snapshot_longtext
Revises: 0107_order_csd_tier
"""

from alembic import op
from sqlalchemy.dialects import mysql


revision = "0108_historical_completion_snapshot_longtext"
down_revision = "0107_order_csd_tier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "historical_installation_completions",
        "before_json",
        existing_type=mysql.TEXT(),
        type_=mysql.LONGTEXT(),
        existing_nullable=False,
    )
    op.alter_column(
        "historical_installation_completions",
        "after_json",
        existing_type=mysql.TEXT(),
        type_=mysql.LONGTEXT(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "historical_installation_completions",
        "after_json",
        existing_type=mysql.LONGTEXT(),
        type_=mysql.TEXT(),
        existing_nullable=False,
    )
    op.alter_column(
        "historical_installation_completions",
        "before_json",
        existing_type=mysql.LONGTEXT(),
        type_=mysql.TEXT(),
        existing_nullable=False,
    )
