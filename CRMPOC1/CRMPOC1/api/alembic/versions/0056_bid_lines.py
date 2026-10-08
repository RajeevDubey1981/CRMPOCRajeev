"""Bid lines: several items with a quantity each on one bid.

Revision ID: 0056_bid_lines
Revises: 0055_field_photos
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_bid_lines"
down_revision: Union[str, None] = "0055_field_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "bid_lines" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "bid_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bid_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("item", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["bid_id"], ["bids.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bid_lines_bid_id", "bid_lines", ["bid_id"])


def downgrade() -> None:
    if "bid_lines" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("bid_lines")
