"""Allow service unit assignment before serials are known.

Revision ID: 0057_service_unit_quantity_assignment
Revises: 0056_service_unit_return_remarks
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057_service_unit_quantity_assignment"
down_revision: Union[str, Sequence[str], None] = "0056_service_unit_return_remarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "service_request_units",
        "order_item_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "service_request_units",
        "order_item_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
