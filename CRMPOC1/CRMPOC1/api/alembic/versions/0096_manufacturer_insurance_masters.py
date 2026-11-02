"""Add Manufacturer and Insurance masters (same shape as couriers), and let a claim say which
one -- or the courier, or the company itself -- it's routed to.

Revision ID: 0096_manufacturer_insurance_masters
Revises: 0095_service_payment_reference
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0096_manufacturer_insurance_masters"
down_revision = "0095_service_payment_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "insurance_companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("claims", sa.Column("routed_to", sa.String(length=20), nullable=True))
    op.add_column("claims", sa.Column("manufacturer_id", sa.Integer(), sa.ForeignKey("manufacturers.id"), nullable=True))
    op.add_column("claims", sa.Column("courier_id", sa.Integer(), sa.ForeignKey("couriers.id"), nullable=True))
    op.add_column("claims", sa.Column("insurance_id", sa.Integer(), sa.ForeignKey("insurance_companies.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "insurance_id")
    op.drop_column("claims", "courier_id")
    op.drop_column("claims", "manufacturer_id")
    op.drop_column("claims", "routed_to")
    op.drop_table("insurance_companies")
    op.drop_table("manufacturers")
