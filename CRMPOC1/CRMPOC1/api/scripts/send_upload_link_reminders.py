#!/usr/bin/env python3
"""Run periodically (via cron) to chase customers who haven't uploaded their installation
documents yet. For every InstallationRequest with an active (not yet expired, not yet uploaded)
document upload link:

  - sends Reminder 1 once the link is within 24h of expiring (i.e. ~24h after it was sent)
  - sends Reminder 2 once the link is within 6h of expiring
  - sends a one-time "link expired" notice once the 48h window has actually passed

A request is treated as "not yet uploaded" if it has no InstallationDocument rows -- once the
customer uploads anything, reminders stop automatically.

Usage (from the api/ directory, same venv the app runs in):
  venv/bin/python scripts/send_upload_link_reminders.py

Suggested cron (runs hourly -- the 24h/6h windows don't need finer granularity):
  0 * * * * cd /var/www/indcool/api && venv/bin/python scripts/send_upload_link_reminders.py >> /var/log/indcool-upload-reminders.log 2>&1
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.installation import InstallationDocument, InstallationRequest  # noqa: E402
from app.services.email_service import (  # noqa: E402
    send_document_upload_expired_email,
    send_document_upload_reminder_email,
)
from app.services.installation_workflow import document_upload_url  # noqa: E402

REMINDER_1_WINDOW = timedelta(hours=24)  # send once within 24h of expiry
REMINDER_2_WINDOW = timedelta(hours=6)   # send once within 6h of expiry


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> int:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    sent_r1 = sent_r2 = sent_expired = 0
    try:
        candidates = db.scalars(
            select(InstallationRequest).where(
                InstallationRequest.document_access_token.is_not(None),
                InstallationRequest.document_access_token_expires_at.is_not(None),
                InstallationRequest.customer_email.is_not(None),
            )
        ).all()

        for inst in candidates:
            expires_at = _aware(inst.document_access_token_expires_at)
            if expires_at is None or not inst.customer_email:
                continue

            has_upload = db.scalar(
                select(InstallationDocument.id).where(InstallationDocument.installation_request_id == inst.id).limit(1)
            )
            if has_upload:
                continue  # customer already responded -- no more chasing

            if now > expires_at:
                if inst.document_expired_notified_at is None:
                    send_document_upload_expired_email(inst.customer_email, inst.customer_name, f"INST-{inst.id}")
                    inst.document_expired_notified_at = now
                    sent_expired += 1
                continue

            remaining = expires_at - now
            upload_url = document_upload_url(inst) or ""

            if remaining <= REMINDER_2_WINDOW and inst.document_reminder_2_sent_at is None:
                send_document_upload_reminder_email(
                    inst.customer_email, inst.customer_name, f"INST-{inst.id}", upload_url,
                    hours_remaining=max(1, int(remaining.total_seconds() // 3600)),
                )
                inst.document_reminder_2_sent_at = now
                sent_r2 += 1
            elif remaining <= REMINDER_1_WINDOW and inst.document_reminder_1_sent_at is None:
                send_document_upload_reminder_email(
                    inst.customer_email, inst.customer_name, f"INST-{inst.id}", upload_url,
                    hours_remaining=max(1, int(remaining.total_seconds() // 3600)),
                )
                inst.document_reminder_1_sent_at = now
                sent_r1 += 1

        db.commit()
    finally:
        db.close()

    print(f"Reminder 1 sent: {sent_r1}, Reminder 2 sent: {sent_r2}, Expired notices sent: {sent_expired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
