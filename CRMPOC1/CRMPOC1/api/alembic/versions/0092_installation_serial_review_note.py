"""Add serial_review_note to installation requests -- flags a scanned serial the engineer entered
that doesn't belong to this order at all, instead of hard-rejecting the save (part of the serial
entry redesign: blank at assignment, engineer scans on site, Service Team reviews before it counts).

Revision ID: 0092_installation_serial_review_note
Revises: 0091_ledger_entry_pending_payment_unique
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0092_installation_serial_review_note"
down_revision = "0091_ledger_entry_pending_payment_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "installation_requests",
        sa.Column("serial_review_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("installation_requests", "serial_review_note")
