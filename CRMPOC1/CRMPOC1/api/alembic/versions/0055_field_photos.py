"""Field photos: a photo of the machine found in the field, against one serial, with the phone's location.

Revision ID: 0055_field_photos
Revises: 0054_clear_rejected_assignments_again
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0055_field_photos"
down_revision: Union[str, None] = "0054_clear_rejected_assignments_again"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "field_photos" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "field_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("service_request_unit_id", sa.Integer(), nullable=True),
        sa.Column("installation_engineer_serial_id", sa.Integer(), nullable=True),
        sa.Column("serial_no", sa.String(length=100), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(10, 1), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["service_request_unit_id"], ["service_request_units.id"]),
        sa.ForeignKeyConstraint(["installation_engineer_serial_id"], ["installation_engineer_serials.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_field_photos_source", "field_photos", ["source"])
    op.create_index("ix_field_photos_service_request_unit_id", "field_photos", ["service_request_unit_id"])
    op.create_index("ix_field_photos_installation_engineer_serial_id", "field_photos", ["installation_engineer_serial_id"])
    op.create_index("ix_field_photos_uploaded_by_user_id", "field_photos", ["uploaded_by_user_id"])


def downgrade() -> None:
    if "field_photos" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("field_photos")
