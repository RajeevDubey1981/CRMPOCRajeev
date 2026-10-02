"""Detect emails that bounced (bad or missing recipient address) and flag them in the CRM.

Two ways a bounce is learnt:
  * the mail server refuses the recipient while we are sending (SMTPRecipientsRefused), or
  * the mail server accepts the message and later sends a "Delivery Status Notification (Failure)"
    report back to the sending mailbox. A background thread reads those reports over IMAP (read only:
    nothing is deleted, moved or marked as read) and stores one row per failed address.

An address counts as "bounced" until we successfully send to it again after the bounce.
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.email_bounce import EmailBounce
from app.models.email_send_log import EmailSendLog

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-']+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SENDERS = ("mailer-daemon", "postmaster")


def _norm(addr: str | None) -> str:
    return (addr or "").strip().lower()


def plain_reason(status: str | None, diagnostic: str | None) -> str:
    status = (status or "").strip()
    diag = " ".join((diagnostic or "").split())
    low = diag.lower()
    if status.startswith(("5.1.1", "5.1.0", "5.1.10")) or any(
        t in low for t in ("does not exist", "not found", "unknown user", "no such user", "user unknown")
    ):
        label = "Email address not found"
    elif status.startswith("5.1.2") or "domain" in low and ("not found" in low or "not exist" in low):
        label = "Email domain does not exist"
    elif status.startswith("5.2.2") or "mailbox full" in low or "over quota" in low:
        label = "Recipient mailbox is full"
    elif status.startswith("5.2.1") or "disabled" in low:
        label = "Recipient mailbox is disabled"
    elif status.startswith("5.7") or "blocked" in low or "rejected" in low:
        label = "Blocked by the recipient's mail server"
    else:
        label = "Email could not be delivered"
    return f"{label}. Server said: {diag[:240]}" if diag else label


# --------------------------------------------------------------------------- recording

def record_bounce(
    to_email: str,
    *,
    status_code: str | None,
    diagnostic: str | None,
    source: str,
    message_key: str | None = None,
    occurred_at: datetime | None = None,
) -> bool:
    """Store a bounce. Returns False if it was already known."""
    addr = _norm(to_email)
    if not addr:
        return False
    try:
        with SessionLocal() as db:
            row = EmailBounce(
                to_email=addr[:255],
                reason=plain_reason(status_code, diagnostic),
                status_code=(status_code or "")[:20] or None,
                source=source,
                message_key=(message_key or "")[:300] or None,
            )
            if occurred_at is not None:
                row.created_at = occurred_at
            db.add(row)
            db.commit()
        logger.warning("email bounced: to=%s source=%s status=%s", addr, source, status_code)
        return True
    except IntegrityError:
        return False  # same bounce report already stored
    except Exception:
        logger.exception("failed to store email bounce")
        return False


def bounced_map(db: Session, emails) -> dict[str, str]:
    """{lowercase address: reason} for the addresses whose latest send ended in a bounce."""
    addrs = {_norm(e) for e in emails if _norm(e)}
    if not addrs:
        return {}
    last: dict[str, tuple[datetime, str]] = {}
    for to, reason, at in db.execute(
        select(EmailBounce.to_email, EmailBounce.reason, EmailBounce.created_at)
        .where(EmailBounce.to_email.in_(addrs))
        .order_by(EmailBounce.created_at)
    ).all():
        last[to] = (at, reason)
    if not last:
        return {}
    sent = dict(
        db.execute(
            select(func.lower(EmailSendLog.to_email), func.max(EmailSendLog.created_at))
            .where(func.lower(EmailSendLog.to_email).in_(list(last)), EmailSendLog.status == "sent")
            .group_by(func.lower(EmailSendLog.to_email))
        ).all()
    )
    out: dict[str, str] = {}
    for addr, (at, reason) in last.items():
        last_sent = sent.get(addr)
        # A bounce report is dated after the send it belongs to; a newer successful send clears it.
        if last_sent is None or at + timedelta(seconds=8) >= last_sent:
            out[addr] = reason
    return out


def bounce_info(db: Session, email_address: str | None) -> tuple[bool, str | None]:
    reason = bounced_map(db, [email_address]).get(_norm(email_address))
    return (reason is not None, reason)


# --------------------------------------------------------------------------- reading reports

def parse_bounce_report(msg: Message) -> list[dict]:
    """Failed recipients found in a delivery-status report: [{email, status, diagnostic}]."""
    found: list[dict] = []
    for part in msg.walk():
        if part.get_content_type() != "message/delivery-status":
            continue
        blocks = part.get_payload()
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            final = str(block.get("Final-Recipient") or block.get("Original-Recipient") or "")
            action = str(block.get("Action") or "").strip().lower()
            if not final or action not in ("failed", ""):
                continue
            m = _EMAIL_RE.search(final)
            if not m:
                continue
            found.append(
                {
                    "email": _norm(m.group(0)),
                    "status": str(block.get("Status") or "").strip(),
                    "diagnostic": str(block.get("Diagnostic-Code") or "").strip(),
                }
            )
    if found:
        return found

    # Fallback for plain-text reports without a machine-readable part.
    subject = str(msg.get("Subject") or "").lower()
    if not any(w in subject for w in ("undeliver", "delivery status", "failure", "returned mail", "failed")):
        return []
    body = ""
    try:
        text_part = msg.get_body(preferencelist=("plain", "html"))
        body = text_part.get_content() if text_part else ""
    except Exception:
        body = ""
    own = {_norm(settings.smtp_user), _norm(settings.smtp_from)}
    for m in _EMAIL_RE.finditer(body):
        addr = _norm(m.group(0))
        if addr and addr not in own and not addr.startswith(("mailer-daemon", "postmaster")):
            return [{"email": addr, "status": "", "diagnostic": " ".join(body.split())[:240]}]
    return []


def _message_date(msg: Message) -> datetime | None:
    try:
        dt = parsedate_to_datetime(str(msg.get("Date")))
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def poll_bounces_once(lookback_days: int | None = None) -> int:
    """Read recent delivery-failure reports from the sending mailbox. Returns how many new bounces were stored."""
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_password or "").strip()
    if not (settings.email_enabled and user and password):
        return 0
    days = lookback_days or settings.bounce_lookback_days
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    new = 0
    imap = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port, timeout=30)
    try:
        imap.login(user, password)
        imap.select("INBOX", readonly=True)  # read only: never changes the mailbox
        uids: set[bytes] = set()
        for sender in _SENDERS:
            typ, data = imap.search(None, "SINCE", since, "FROM", sender)
            if typ == "OK" and data and data[0]:
                uids.update(data[0].split())
        for uid in sorted(uids, key=int):
            typ, parts = imap.fetch(uid, "(BODY.PEEK[])")
            if typ != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            msg = email.message_from_bytes(parts[0][1], policy=policy.default)
            base_key = str(msg.get("Message-ID") or f"uid-{uid.decode()}").strip()
            occurred = _message_date(msg)
            for item in parse_bounce_report(msg):
                key = f"{base_key}|{item['email']}"
                if record_bounce(
                    item["email"],
                    status_code=item["status"],
                    diagnostic=item["diagnostic"],
                    source="imap",
                    message_key=key,
                    occurred_at=occurred,
                ):
                    new += 1
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return new


# --------------------------------------------------------------------------- background thread

_started = False


def _loop() -> None:
    time.sleep(30)
    while True:
        try:
            n = poll_bounces_once()
            if n:
                logger.warning("bounce watcher stored %s new bounce(s)", n)
        except Exception:
            logger.exception("bounce watcher failed (will retry)")
        time.sleep(max(60, settings.bounce_poll_seconds))


def start_bounce_watcher() -> None:
    global _started
    if _started or not settings.bounce_check_enabled:
        return
    _started = True
    threading.Thread(target=_loop, name="bounce-watcher", daemon=True).start()
