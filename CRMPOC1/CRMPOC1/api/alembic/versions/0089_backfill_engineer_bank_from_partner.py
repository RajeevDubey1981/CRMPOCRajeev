"""Backfill engineer bank details from their partner onboarding registration.

Partner onboarding already collects bank details (step 6, "Bank Details"), but
ensure_partner_account() never copied them onto the User row it creates/updates,
so every engineer who came in through partner onboarding has an empty bank
section even though the data was submitted. This is a one-time catch-up for
rows created before that merge existed (see 0090's code fix for new ones).

Revision ID: 0089_backfill_engineer_bank_from_partner
Revises: 0088_ledger_audit
Create Date: 2026-10-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0089_backfill_engineer_bank_from_partner"
down_revision: Union[str, Sequence[str], None] = "0088_ledger_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users u
        JOIN (
            SELECT pr.*
            FROM partner_registrations pr
            INNER JOIN (
                SELECT LOWER(TRIM(email)) AS norm_email, MAX(id) AS max_id
                FROM partner_registrations
                WHERE account_number IS NOT NULL AND account_number != ''
                GROUP BY LOWER(TRIM(email))
            ) latest ON LOWER(TRIM(pr.email)) = latest.norm_email AND pr.id = latest.max_id
        ) pr ON LOWER(TRIM(u.email)) = LOWER(TRIM(pr.email))
        SET u.bank_account_holder_name = COALESCE(NULLIF(u.bank_account_holder_name, ''), pr.account_holder_name),
            u.bank_name = COALESCE(NULLIF(u.bank_name, ''), pr.bank_name),
            u.bank_account_number = COALESCE(NULLIF(u.bank_account_number, ''), pr.account_number),
            u.bank_ifsc = COALESCE(NULLIF(u.bank_ifsc, ''), pr.ifsc_code),
            u.bank_branch = COALESCE(NULLIF(u.bank_branch, ''), pr.bank_branch)
        WHERE LOWER(TRIM(u.role)) IN ('engineer', 'engineer non gst', 'engineer_non_gst', 'engineer non-gst', 'engineer nongst')
          AND (u.bank_account_number IS NULL OR u.bank_account_number = '')
        """
    )


def downgrade() -> None:
    pass
