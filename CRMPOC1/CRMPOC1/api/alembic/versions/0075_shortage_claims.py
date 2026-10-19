"""Missing-item claims (copper, remote, gas ... missing from a new delivery), pinned on manufacturer,
transporter or insurance, with their photos and timeline.

Revision ID: 0075_shortage_claims
Revises: 0074_user_identity_files
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0075_shortage_claims"
down_revision: Union[str, None] = "0074_user_identity_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shortage_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_no", sa.String(length=30), nullable=False),
        sa.Column("flow", sa.String(length=20), nullable=False),
        sa.Column("service_request_id", sa.Integer(), nullable=True),
        sa.Column("installation_request_id", sa.Integer(), nullable=True),
        sa.Column("item_code", sa.String(length=100), nullable=True),
        sa.Column("serial_no", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(length=10), nullable=False),
        sa.Column("responsible_type", sa.String(length=10), nullable=True),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("courier_id", sa.Integer(), nullable=True),
        sa.Column("insurer_name", sa.String(length=255), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("raised_by_user_id", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"]),
        sa.ForeignKeyConstraint(["installation_request_id"], ["installation_requests.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.ForeignKeyConstraint(["courier_id"], ["couriers.id"]),
        sa.ForeignKeyConstraint(["raised_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shortage_claims_claim_no"), "shortage_claims", ["claim_no"], unique=True)
    op.create_index(op.f("ix_shortage_claims_flow"), "shortage_claims", ["flow"], unique=False)
    op.create_index(op.f("ix_shortage_claims_service_request_id"), "shortage_claims", ["service_request_id"], unique=False)
    op.create_index(op.f("ix_shortage_claims_installation_request_id"), "shortage_claims", ["installation_request_id"], unique=False)
    op.create_index(op.f("ix_shortage_claims_item_code"), "shortage_claims", ["item_code"], unique=False)
    op.create_index(op.f("ix_shortage_claims_stage"), "shortage_claims", ["stage"], unique=False)
    op.create_index(op.f("ix_shortage_claims_raised_by_user_id"), "shortage_claims", ["raised_by_user_id"], unique=False)

    op.create_table(
        "shortage_claim_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["shortage_claims.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shortage_claim_items_claim_id"), "shortage_claim_items", ["claim_id"], unique=False)

    op.create_table(
        "shortage_claim_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["shortage_claims.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shortage_claim_photos_claim_id"), "shortage_claim_photos", ["claim_id"], unique=False)

    op.create_table(
        "shortage_claim_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("by_user_id", sa.Integer(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["shortage_claims.id"]),
        sa.ForeignKeyConstraint(["by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shortage_claim_events_claim_id"), "shortage_claim_events", ["claim_id"], unique=False)
    op.create_index(op.f("ix_shortage_claim_events_at"), "shortage_claim_events", ["at"], unique=False)


def downgrade() -> None:
    op.drop_table("shortage_claim_events")
    op.drop_table("shortage_claim_photos")
    op.drop_table("shortage_claim_items")
    op.drop_table("shortage_claims")
