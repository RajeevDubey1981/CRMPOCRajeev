"""Let a missing-item claim be raised straight from a parts request's approval screen, not only from a
Service/Installation step.

Revision ID: 0076_shortage_claim_item_request
Revises: 0075_shortage_claims
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0076_shortage_claim_item_request"
down_revision: Union[str, None] = "0075_shortage_claims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.add_column(sa.Column("item_request_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_shortage_claims_item_request_id", ["item_request_id"])


def downgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.drop_index("ix_shortage_claims_item_request_id")
        batch_op.drop_column("item_request_id")
