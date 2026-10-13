"""Partner agreement: the signed hard copy, uploaded by Admin or Sub Admin, with its history.

The file is kept on the agreement. When it is shared, the path is also put on the registration so it shows next to the
partner's other documents. The history of the hard copy (uploaded, replaced, removed, sharing changed) is a small table.

Revision ID: 0070_partner_agreement_hard_copy
Revises: 0069_queries_group_forward
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0070_partner_agreement_hard_copy"
down_revision: Union[str, None] = "0069_queries_group_forward"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("partner_agreements", sa.Column("hard_copy_path", sa.String(500), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_name", sa.String(255), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_received_on", sa.Date(), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_note", sa.String(500), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_by", sa.Integer(), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("partner_agreements", sa.Column("hard_copy_shared", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("partner_registrations", sa.Column("agreement_hard_copy_path", sa.String(500), nullable=True))
    op.create_table(
        "partner_agreement_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agreement_id", sa.Integer(), sa.ForeignKey("partner_agreements.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("by_user_id", sa.Integer(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_partner_agreement_events_agreement_id", "partner_agreement_events", ["agreement_id"])


def downgrade() -> None:
    op.drop_index("ix_partner_agreement_events_agreement_id", table_name="partner_agreement_events")
    op.drop_table("partner_agreement_events")
    op.drop_column("partner_registrations", "agreement_hard_copy_path")
    for col in ("hard_copy_shared", "hard_copy_at", "hard_copy_by", "hard_copy_note", "hard_copy_received_on", "hard_copy_name", "hard_copy_path"):
        op.drop_column("partner_agreements", col)
