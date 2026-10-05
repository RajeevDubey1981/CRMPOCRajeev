"""Run the rejected-service clean-up of 0052_clear_rejected_service_assignments once more on databases that already moved past it.

The live database was stamped at 0053_bids by a deploy made before 0052_clear_rejected_service_assignments joined this
line, so alembic counts that clean-up as done although it never ran there. The statements only touch rejected service
requests and are safe to repeat on any database.

Revision ID: 0054_clear_rejected_assignments_again
Revises: 0053_bids
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0054_clear_rejected_assignments_again"
down_revision: Union[str, Sequence[str], None] = "0053_bids"
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
