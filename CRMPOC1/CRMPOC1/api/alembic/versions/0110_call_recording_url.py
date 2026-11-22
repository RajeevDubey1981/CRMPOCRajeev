"""calls.recording_url: the Google Drive link of a call's recording

Revision ID: 0110_call_recording_url
Revises: 0109_call_recordings
"""
import sqlalchemy as sa
from alembic import op

revision = "0110_call_recording_url"
down_revision = "0109_call_recordings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("calls")}
    if "recording_url" not in cols:
        op.add_column("calls", sa.Column("recording_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("calls")}
    if "recording_url" in cols:
        op.drop_column("calls", "recording_url")
