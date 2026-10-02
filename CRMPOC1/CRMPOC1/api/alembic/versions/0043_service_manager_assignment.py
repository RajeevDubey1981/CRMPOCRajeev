"""Assign service desk users on service requests.

Revision ID: 0043_service_manager_assignment
Revises: 0042_email_send_logs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0043_service_manager_assignment"
down_revision: Union[str, None] = "0042_email_send_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_requests",
        sa.Column("assigned_service_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_service_requests_assigned_service_user_id_users",
        "service_requests",
        "users",
        ["assigned_service_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_service_requests_assigned_service_user_id",
        "service_requests",
        ["assigned_service_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_requests_assigned_service_user_id", table_name="service_requests")
    op.drop_constraint(
        "fk_service_requests_assigned_service_user_id_users",
        "service_requests",
        type_="foreignkey",
    )
    op.drop_column("service_requests", "assigned_service_user_id")
