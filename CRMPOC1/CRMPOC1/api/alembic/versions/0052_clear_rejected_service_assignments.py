"""Clear stale engineer/vendor assignments on rejected service requests.

Revision ID: 0052_clear_rejected_service_assignments
Revises: 0051_merge_installation_service_user_and_accounts
Create Date: 2026-10-04
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0052_clear_rejected_service_assignments"
down_revision: Union[str, Sequence[str], None] = "0051_merge_installation_service_user_and_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE service_assignments sa
        JOIN service_requests sr ON sr.id = sa.service_request_id
        SET sa.is_active = 0
        WHERE sr.status = 'Rejected'
        """
    )
    op.execute(
        """
        UPDATE complaints c
        JOIN service_requests sr ON sr.complaint_id = c.id
        SET c.assigned_engineer = NULL
        WHERE sr.status = 'Rejected'
        """
    )
    op.execute(
        """
        UPDATE service_requests
        SET assigned_engineer_id = NULL,
            assigned_vendor_id = NULL,
            completion_code = NULL
        WHERE status = 'Rejected'
        """
    )


def downgrade() -> None:
    pass
