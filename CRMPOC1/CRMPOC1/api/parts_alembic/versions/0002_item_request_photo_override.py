"""item requests: a per-request photo-requirement override, so a request raised by the system (e.g.
auto-raised from a service engineer's observation, which already documents the problem) doesn't inherit
the 4-photo mandate meant for a human manually raising a part request with no other evidence on file.

Revision ID: 0002_item_request_photo_override
Revises: 0001_parts_initial
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_item_request_photo_override"
down_revision: Union[str, Sequence[str], None] = "0001_parts_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("parts_item_request", sa.Column("required_photos_override", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("parts_item_request", "required_photos_override")
