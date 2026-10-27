"""Bank account details on a user's profile (engineer, GST or Non-GST), so Accounts always pays the one
account on file instead of whatever was given over the phone that day.

Revision ID: 0087_engineer_bank_details
Revises: 0086_ledger_phase2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0087_engineer_bank_details"
down_revision: Union[str, None] = "0086_ledger_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("bank_account_holder_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("bank_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("bank_account_number", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("bank_ifsc", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("bank_branch", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("bank_branch")
        batch_op.drop_column("bank_ifsc")
        batch_op.drop_column("bank_account_number")
        batch_op.drop_column("bank_name")
        batch_op.drop_column("bank_account_holder_name")
