"""Let a claim raised from a unit's serial verification skip the 4-photo requirement by pairing in the
photos the engineer already took there, instead of demanding a fresh set.

Revision ID: 0078_shortage_claim_photo_override
Revises: 0077_shortage_claim_amount
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0078_shortage_claim_photo_override"
down_revision: Union[str, None] = "0077_shortage_claim_amount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.add_column(sa.Column("required_photos_override", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.drop_column("required_photos_override")
