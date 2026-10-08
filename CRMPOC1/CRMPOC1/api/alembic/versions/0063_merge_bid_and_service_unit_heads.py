"""Merge bid reminder and service unit quantity assignment heads.

Revision ID: 0063_merge_bid_and_service_unit_heads
Revises: 0062_bid_reminders, 0057_service_unit_quantity_assignment
"""

from typing import Sequence, Union

revision: str = "0063_merge_bid_and_service_unit_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0062_bid_reminders",
    "0057_service_unit_quantity_assignment",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
