"""calls.purpose: what the call was about (service complaint, sales enquiry, business enquiry ...)

Revision ID: 0111_call_purpose
Revises: 0110_call_recording_url
"""
import sqlalchemy as sa
from alembic import op

revision = "0111_call_purpose"
down_revision = "0110_call_recording_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "purpose" not in {c["name"] for c in insp.get_columns("calls")}:
        op.add_column("calls", sa.Column("purpose", sa.String(length=40), nullable=True))
    if "ix_calls_purpose" not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("calls")}:
        op.create_index("ix_calls_purpose", "calls", ["purpose"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ix_calls_purpose" in {i["name"] for i in insp.get_indexes("calls")}:
        op.drop_index("ix_calls_purpose", table_name="calls")
    if "purpose" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("calls")}:
        op.drop_column("calls", "purpose")
