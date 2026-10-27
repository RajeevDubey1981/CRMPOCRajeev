"""Login lockout: track consecutive failed password attempts per user and lock them out for a
cooldown once the threshold is hit, since login had no rate limiting at all (security review, 2026-10-27).

Revision ID: 0090_login_lockout
Revises: 0089_backfill_engineer_bank_from_partner
Create Date: 2026-10-27
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0090_login_lockout"
down_revision: Union[str, Sequence[str], None] = "0089_backfill_engineer_bank_from_partner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(timezone=False), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
