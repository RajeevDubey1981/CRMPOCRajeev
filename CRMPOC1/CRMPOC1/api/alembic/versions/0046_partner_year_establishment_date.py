"""store partner establishment as date

Revision ID: 0046_partner_year_establishment_date
Revises: 0045_payment_approval_workflow
Create Date: 2026-10-02 21:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0046_partner_year_establishment_date"
down_revision = "0045_payment_approval_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("partner_registrations", sa.Column("year_of_establishment_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE partner_registrations
        SET year_of_establishment_date = STR_TO_DATE(CONCAT(year_of_establishment, '-01-01'), '%Y-%m-%d')
        WHERE year_of_establishment IS NOT NULL
        """
    )
    op.drop_column("partner_registrations", "year_of_establishment")
    op.alter_column(
        "partner_registrations",
        "year_of_establishment_date",
        new_column_name="year_of_establishment",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    op.add_column("partner_registrations", sa.Column("year_of_establishment_int", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE partner_registrations
        SET year_of_establishment_int = YEAR(year_of_establishment)
        WHERE year_of_establishment IS NOT NULL
        """
    )
    op.drop_column("partner_registrations", "year_of_establishment")
    op.alter_column(
        "partner_registrations",
        "year_of_establishment_int",
        new_column_name="year_of_establishment",
        existing_type=sa.Integer(),
        nullable=True,
    )
