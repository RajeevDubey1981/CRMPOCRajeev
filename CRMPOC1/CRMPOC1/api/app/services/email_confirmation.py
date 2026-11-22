"""Emails typed by the caller. The voice agent mishears spoken emails, so it sends the caller an SMS with a short code;
the caller opens the link, types the email and the code, and the email is stored as confirmed."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.email_confirmation import EmailConfirmation

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+([.][A-Za-z0-9-]+)*[.][A-Za-z]{2,}")
VALID_MINUTES = 60
MAX_ATTEMPTS = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def create_request(db: Session, mobile: str, comp_no: str | None) -> EmailConfirmation:
    """A new pending request with a 6-digit code that no other live request is using."""
    live = set(db.execute(select(EmailConfirmation.code).where(EmailConfirmation.expires_at > _now(), EmailConfirmation.confirmed_at.is_(None))).scalars())
    code = ""
    for _ in range(50):
        code = f"{secrets.randbelow(900000) + 100000}"
        if code not in live:
            break
    row = EmailConfirmation(code=code, mobile=mobile, comp_no=(comp_no or None), expires_at=_now() + timedelta(minutes=VALID_MINUTES))
    db.add(row)
    db.flush()
    return row


def confirm(db: Session, code: str, email: str) -> tuple[bool, str]:
    """Check the code and store the email. Returns (ok, message for the caller)."""
    code = (code or "").strip()
    email = (email or "").strip().lower()
    if not EMAIL_RE.fullmatch(email):
        return False, "That does not look like an email address. Please check it."
    if not re.fullmatch(r"[0-9]{6}", code):
        return False, "The code is 6 digits, as in the SMS."
    row = db.execute(
        select(EmailConfirmation).where(EmailConfirmation.code == code, EmailConfirmation.confirmed_at.is_(None)).order_by(EmailConfirmation.id.desc())
    ).scalars().first()
    if row is None or _aware(row.expires_at) < _now():
        return False, "This code is not valid or has expired. Please ask the INDcool team to send it again."
    if row.attempts >= MAX_ATTEMPTS:
        return False, "Too many tries. Please ask the INDcool team to send a new code."
    row.attempts += 1
    row.email = email
    row.confirmed_at = _now()
    if row.comp_no:
        complaint = db.execute(select(Complaint).where(Complaint.comp_no == row.comp_no)).scalars().first()
        if complaint is not None:
            complaint.customer_email = email
    db.commit()
    return True, "Thank you. Your email is confirmed."


def latest_for_mobile(db: Session, mobile: str) -> EmailConfirmation | None:
    return db.execute(
        select(EmailConfirmation).where(EmailConfirmation.mobile == mobile).order_by(EmailConfirmation.id.desc())
    ).scalars().first()


def confirmed_recently(db: Session, mobile: str, email: str | None, hours: int = 3) -> bool:
    """True when this caller typed this same email in the last few hours."""
    if not email:
        return False
    since = _now() - timedelta(hours=hours)
    row = db.execute(
        select(EmailConfirmation).where(
            EmailConfirmation.mobile == mobile,
            EmailConfirmation.confirmed_at.is_not(None),
            EmailConfirmation.confirmed_at >= since,
            EmailConfirmation.email == email.strip().lower(),
        )
    ).scalars().first()
    return row is not None
