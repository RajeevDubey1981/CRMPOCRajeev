"""Add an amount to missing-item claims, so the same 2500 Service Manager approval cap used elsewhere
applies to them too.

Revision ID: 0077_shortage_claim_amount
Revises: 0076_shortage_claim_item_request
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0077_shortage_claim_amount"
down_revision: Union[str, None] = "0076_shortage_claim_item_request"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.add_column(sa.Column("amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shortage_claims") as batch_op:
        batch_op.drop_column("amount")
