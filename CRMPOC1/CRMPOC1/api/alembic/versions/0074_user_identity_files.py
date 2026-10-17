"""Protected user ID proof and profile picture files.

Revision ID: 0074_user_identity_files
Revises: 0073_historical_installation_completion
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0074_user_identity_files"
down_revision: Union[str, None] = "0073_historical_installation_completion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _blob_type():
    return sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql")


def upgrade() -> None:
    op.add_column("users", sa.Column("id_proof_blob", _blob_type(), nullable=True))
    op.add_column("users", sa.Column("id_proof_filename", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("id_proof_content_type", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("id_proof_size_bytes", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("profile_picture_blob", _blob_type(), nullable=True))
    op.add_column("users", sa.Column("profile_picture_filename", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("profile_picture_content_type", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("profile_picture_size_bytes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_picture_size_bytes")
    op.drop_column("users", "profile_picture_content_type")
    op.drop_column("users", "profile_picture_filename")
    op.drop_column("users", "profile_picture_blob")
    op.drop_column("users", "id_proof_size_bytes")
    op.drop_column("users", "id_proof_content_type")
    op.drop_column("users", "id_proof_filename")
    op.drop_column("users", "id_proof_blob")
