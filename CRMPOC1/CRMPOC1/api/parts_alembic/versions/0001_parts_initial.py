"""parts initial: spare parts catalogue, fitments, the unified item-request/approval queue with its photos and
timeline, and the part warranty-swap log

Revision ID: 0001_parts_initial
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_parts_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parts_spare_part",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("part_code", sa.String(length=100), nullable=False),
        sa.Column("part_name", sa.String(length=255), nullable=False),
        sa.Column("part_ean", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("engineer_visible", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("crm_created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_spare_part_part_code"), "parts_spare_part", ["part_code"], unique=True)
    op.create_index(op.f("ix_parts_spare_part_part_ean"), "parts_spare_part", ["part_ean"], unique=False)

    op.create_table(
        "parts_fitment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spare_part_id", sa.Integer(), nullable=False),
        sa.Column("crm_item_code", sa.String(length=100), nullable=False),
        sa.Column("crm_item_name_cache", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["spare_part_id"], ["parts_spare_part.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spare_part_id", "crm_item_code", name="uq_parts_fitment"),
    )
    op.create_index(op.f("ix_parts_fitment_spare_part_id"), "parts_fitment", ["spare_part_id"], unique=False)
    op.create_index(op.f("ix_parts_fitment_crm_item_code"), "parts_fitment", ["crm_item_code"], unique=False)

    op.create_table(
        "parts_item_request",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_no", sa.String(length=30), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("crm_service_request_id", sa.Integer(), nullable=True),
        sa.Column("crm_service_request_no", sa.String(length=100), nullable=True),
        sa.Column("crm_installation_request_id", sa.Integer(), nullable=True),
        sa.Column("crm_installation_request_no", sa.String(length=100), nullable=True),
        sa.Column("crm_item_code", sa.String(length=100), nullable=True),
        sa.Column("crm_item_name_cache", sa.String(length=255), nullable=True),
        sa.Column("crm_serial_no", sa.String(length=100), nullable=True),
        sa.Column("spare_part_id", sa.Integer(), nullable=True),
        sa.Column("part_name_cache", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("stage", sa.String(length=10), nullable=False),
        sa.Column("crm_query_id", sa.Integer(), nullable=True),
        sa.Column("crm_raised_by_user_id", sa.Integer(), nullable=False),
        sa.Column("crm_raised_by_name", sa.String(length=255), nullable=False),
        sa.Column("crm_raised_by_role", sa.String(length=50), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decided_by_name", sa.String(length=255), nullable=True),
        sa.Column("request_date", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["spare_part_id"], ["parts_spare_part.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_item_request_request_no"), "parts_item_request", ["request_no"], unique=True)
    op.create_index(op.f("ix_parts_item_request_kind"), "parts_item_request", ["kind"], unique=False)
    op.create_index(op.f("ix_parts_item_request_crm_service_request_id"), "parts_item_request", ["crm_service_request_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_crm_installation_request_id"), "parts_item_request", ["crm_installation_request_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_crm_item_code"), "parts_item_request", ["crm_item_code"], unique=False)
    op.create_index(op.f("ix_parts_item_request_spare_part_id"), "parts_item_request", ["spare_part_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_stage"), "parts_item_request", ["stage"], unique=False)
    op.create_index(op.f("ix_parts_item_request_crm_query_id"), "parts_item_request", ["crm_query_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_crm_raised_by_user_id"), "parts_item_request", ["crm_raised_by_user_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_request_date"), "parts_item_request", ["request_date"], unique=False)

    op.create_table(
        "parts_item_request_photo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_request_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_request_id"], ["parts_item_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_item_request_photo_item_request_id"), "parts_item_request_photo", ["item_request_id"], unique=False)

    op.create_table(
        "parts_item_request_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_request_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("crm_by_user_id", sa.Integer(), nullable=True),
        sa.Column("crm_by_name", sa.String(length=255), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_request_id"], ["parts_item_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_item_request_event_item_request_id"), "parts_item_request_event", ["item_request_id"], unique=False)
    op.create_index(op.f("ix_parts_item_request_event_at"), "parts_item_request_event", ["at"], unique=False)

    op.create_table(
        "parts_warranty_swap",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_request_id", sa.Integer(), nullable=True),
        sa.Column("crm_service_request_id", sa.Integer(), nullable=True),
        sa.Column("crm_item_code", sa.String(length=100), nullable=True),
        sa.Column("old_serial_no", sa.String(length=100), nullable=True),
        sa.Column("new_serial_no", sa.String(length=100), nullable=True),
        sa.Column("installed_on", sa.Date(), nullable=True),
        sa.Column("original_warranty_months", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("carried_months", sa.Integer(), nullable=True),
        sa.Column("swapped_on", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("recorded_by_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_request_id"], ["parts_item_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_warranty_swap_item_request_id"), "parts_warranty_swap", ["item_request_id"], unique=False)
    op.create_index(op.f("ix_parts_warranty_swap_crm_service_request_id"), "parts_warranty_swap", ["crm_service_request_id"], unique=False)


def downgrade() -> None:
    op.drop_table("parts_warranty_swap")
    op.drop_table("parts_item_request_event")
    op.drop_table("parts_item_request_photo")
    op.drop_table("parts_item_request")
    op.drop_table("parts_fitment")
    op.drop_table("parts_spare_part")
