"""Persist outbound email attempts for auditing and exact send counts."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.email_send_log import EmailSendLog

logger = logging.getLogger(__name__)

EMAIL_STATUS_SENT = "sent"
EMAIL_STATUS_FAILED = "failed"
EMAIL_STATUS_SKIPPED = "skipped"

_MAX_ERROR_LEN = 4000


def record_email_send(
    *,
    to_email: str,
    subject: str,
    status: str,
    from_email: str | None = None,
    template: str | None = None,
    skip_reason: str | None = None,
    error_message: str | None = None,
) -> None:
    try:
        with SessionLocal() as db:
            db.add(
                EmailSendLog(
                    to_email=(to_email or "").strip()[:255],
                    from_email=(from_email or "").strip()[:255] or None,
                    subject=(subject or "").strip()[:500] or "(no subject)",
                    template=(template or "").strip()[:120] or None,
                    status=status,
                    skip_reason=(skip_reason or "").strip()[:80] or None,
                    error_message=(error_message or "").strip()[:_MAX_ERROR_LEN] or None,
                )
            )
            db.commit()
    except Exception:
        logger.exception("failed to persist email_send_log")


def email_send_summary(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    stmt = select(EmailSendLog.status, func.count()).select_from(EmailSendLog)
    if date_from is not None:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        stmt = stmt.where(EmailSendLog.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        stmt = stmt.where(EmailSendLog.created_at <= end)
    stmt = stmt.group_by(EmailSendLog.status)
    counts = {row[0]: row[1] for row in db.execute(stmt).all()}
    sent = counts.get(EMAIL_STATUS_SENT, 0)
    failed = counts.get(EMAIL_STATUS_FAILED, 0)
    skipped = counts.get(EMAIL_STATUS_SKIPPED, 0)
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "total_attempts": sent + failed + skipped,
    }
