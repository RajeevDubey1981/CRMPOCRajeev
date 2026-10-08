"""Store engineer return remarks on service request units.

Revision ID: 0056_service_unit_return_remarks
Revises: 0055_field_photos
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_service_unit_return_remarks"
down_revision: Union[str, Sequence[str], None] = "0055_field_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("service_request_units", "remarks"):
        op.add_column("service_request_units", sa.Column("remarks", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_column("service_request_units", "remarks"):
        op.drop_column("service_request_units", "remarks")
