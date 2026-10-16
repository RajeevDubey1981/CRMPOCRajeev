"""Queries: the typed serial number and date are replaced by an automatic query number and the raised date.

Nobody had used the two typed columns (checked on the live server before dropping them).

Revision ID: 0072_query_drop_manual_serial_date
Revises: 0071_query_serial_date
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0072_query_drop_manual_serial_date"
down_revision: Union[str, None] = "0071_query_serial_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_user_queries_query_date", table_name="user_queries")
    op.drop_index("ix_user_queries_serial_no", table_name="user_queries")
    op.drop_column("user_queries", "query_date")
    op.drop_column("user_queries", "serial_no")


def downgrade() -> None:
    op.add_column("user_queries", sa.Column("serial_no", sa.String(100), nullable=True))
    op.add_column("user_queries", sa.Column("query_date", sa.Date(), nullable=True))
    op.create_index("ix_user_queries_serial_no", "user_queries", ["serial_no"])
    op.create_index("ix_user_queries_query_date", "user_queries", ["query_date"])
