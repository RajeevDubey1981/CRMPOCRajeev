"""Data fix: clear stale serial_verified_at on installation requests sitting in "Serial Pending
Verification" -- that status means the engineer just (re-)entered serials and nothing's been
approved yet, but any row assigned before the serial-entry redesign (0092) carries a
serial_verified_at the old auto-verify logic set at assignment time, which the save endpoint
didn't clear until this fix landed. Left in place, it skips Jayveer's review screen entirely and
shows the old "already verified" admin panel instead.

Revision ID: 0093_clear_stale_serial_verification
Revises: 0092_installation_serial_review_note
Create Date: 2026-10-29
"""

from alembic import op


revision = "0093_clear_stale_serial_verification"
down_revision = "0092_installation_serial_review_note"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE installation_requests
        SET serial_verified_at = NULL, serial_verified_by = NULL
        WHERE status = 'Serial Pending Verification' AND serial_verified_at IS NOT NULL
        """
    )


def downgrade() -> None:
    pass
