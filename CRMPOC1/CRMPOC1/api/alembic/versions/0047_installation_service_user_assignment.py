"""Add service user assignment to installation requests.

Revision ID: 0047_installation_service_user_assignment
Revises: 0046_partner_year_establishment_date
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0047_installation_service_user_assignment"
down_revision = "0046_partner_year_establishment_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "installation_requests",
        sa.Column("assigned_service_user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_installation_requests_assigned_service_user_id",
        "installation_requests",
        ["assigned_service_user_id"],
    )
    op.create_foreign_key(
        "fk_installation_requests_assigned_service_user_id_users",
        "installation_requests",
        "users",
        ["assigned_service_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_installation_requests_assigned_service_user_id_users",
        "installation_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_installation_requests_assigned_service_user_id",
        table_name="installation_requests",
    )
    op.drop_column("installation_requests", "assigned_service_user_id")
