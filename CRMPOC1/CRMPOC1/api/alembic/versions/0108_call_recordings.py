"""calls: Sarvam interaction id, and a call_recordings table for the call audio

Revision ID: 0108_call_recordings
Revises: 0107_order_csd_tier
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0108_call_recordings"
down_revision: Union[str, Sequence[str], None] = "0107_order_csd_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("calls")}
    if "sarvam_interaction_id" not in cols:
        op.add_column("calls", sa.Column("sarvam_interaction_id", sa.String(length=120), nullable=True))
        op.create_index("ix_calls_sarvam_interaction_id", "calls", ["sarvam_interaction_id"])
    if "call_recordings" not in insp.get_table_names():
        op.create_table(
            "call_recordings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("call_id", sa.Integer(), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("content_type", sa.String(length=100), nullable=False, server_default="audio/wav"),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("audio", sa.LargeBinary(length=4294967295), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("call_recordings")
    op.drop_index("ix_calls_sarvam_interaction_id", table_name="calls")
    op.drop_column("calls", "sarvam_interaction_id")
