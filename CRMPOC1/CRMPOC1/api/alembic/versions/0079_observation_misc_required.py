"""Let an engineer's observation list misc/other work (AC wash, gas top-up ...) separately from physical
parts, so it stops being wrongly raised as a "Spare part" request in the Parts approval queue.

Revision ID: 0079_observation_misc_required
Revises: 0078_shortage_claim_photo_override
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0079_observation_misc_required"
down_revision: Union[str, None] = "0078_shortage_claim_photo_override"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("service_observations") as batch_op:
        batch_op.add_column(sa.Column("misc_required_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("service_observations") as batch_op:
        batch_op.drop_column("misc_required_json")
