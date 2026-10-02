"""Add staged payment approval workflow.

Revision ID: 0045_payment_approval_workflow
Revises: 0044_email_bounces
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0045_payment_approval_workflow"
down_revision: Union[str, None] = "0044_email_bounces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("service_payment_requests",):
        op.add_column(table, sa.Column("payment_proof_file_path", sa.String(length=500), nullable=True))
        op.add_column(table, sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="Pending"))
        op.add_column(table, sa.Column("approval_stage", sa.String(length=50), nullable=True))
        op.add_column(table, sa.Column("approval_stage_label", sa.String(length=100), nullable=True))
        op.add_column(table, sa.Column("approval_step", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("approval_total_steps", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("next_approver_role", sa.String(length=100), nullable=True))

    for column_name, column_type in (
        ("payment_approval_status", sa.String(length=30)),
        ("payment_approval_stage", sa.String(length=50)),
        ("payment_approval_stage_label", sa.String(length=100)),
        ("payment_approval_step", sa.Integer()),
        ("payment_approval_total_steps", sa.Integer()),
        ("payment_next_approver_role", sa.String(length=100)),
    ):
        op.add_column("installation_requests", sa.Column(column_name, column_type, nullable=True))

    op.create_table(
        "payment_approval_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("service_payment_request_id", sa.Integer(), nullable=True),
        sa.Column("stage_key", sa.String(length=50), nullable=False),
        sa.Column("stage_label", sa.String(length=100), nullable=False),
        sa.Column("stage_level", sa.Integer(), nullable=False),
        sa.Column("total_stages", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approver_role", sa.String(length=100), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_payment_request_id"], ["service_payment_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_approval_logs_module", "payment_approval_logs", ["module"])
    op.create_index("ix_payment_approval_logs_entity_id", "payment_approval_logs", ["entity_id"])
    op.create_index(
        "ix_payment_approval_logs_service_payment_request_id",
        "payment_approval_logs",
        ["service_payment_request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_approval_logs_service_payment_request_id", table_name="payment_approval_logs")
    op.drop_index("ix_payment_approval_logs_entity_id", table_name="payment_approval_logs")
    op.drop_index("ix_payment_approval_logs_module", table_name="payment_approval_logs")
    op.drop_table("payment_approval_logs")
    for column_name in (
        "payment_next_approver_role",
        "payment_approval_total_steps",
        "payment_approval_step",
        "payment_approval_stage_label",
        "payment_approval_stage",
        "payment_approval_status",
    ):
        op.drop_column("installation_requests", column_name)
    for column_name in (
        "next_approver_role",
        "approval_total_steps",
        "approval_step",
        "approval_stage_label",
        "approval_stage",
        "approval_status",
        "payment_proof_file_path",
    ):
        op.drop_column("service_payment_requests", column_name)
