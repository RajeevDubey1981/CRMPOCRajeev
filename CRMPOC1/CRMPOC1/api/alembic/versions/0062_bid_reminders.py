"""Bids: accept-or-reject time in hours, its reminder marks; pending actions: a time limit.

Revision ID: 0062_bid_reminders
Revises: 0061_user_queries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062_bid_reminders"
down_revision: Union[str, None] = "0061_user_queries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add(table: str, name: str) -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    if name not in cols:
        op.add_column(table, sa.Column(name, sa.DateTime(timezone=True), nullable=True))


def upgrade() -> None:
    for name in ("confirm_due_at", "accept_remind_24_at", "accept_remind_2_at"):
        _add("bids", name)
    _add("user_pending_actions", "due_at")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, names in (("bids", ("confirm_due_at", "accept_remind_24_at", "accept_remind_2_at")), ("user_pending_actions", ("due_at",))):
        cols = {c["name"] for c in inspector.get_columns(table)}
        for name in names:
            if name in cols:
                op.drop_column(table, name)
