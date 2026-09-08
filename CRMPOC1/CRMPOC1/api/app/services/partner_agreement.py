from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.partner_agreement import PartnerAgreement
from app.models.partner_registration import PartnerRegistration
from app.services.agreement_text import AGREEMENT_VERSION

OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 30
OTP_MAX_SENDS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    """MySQL returns naive datetimes; treat stored values as UTC for comparison."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def generate_agreement_no(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(PartnerAgreement)) or 0
    return f"AGR-{_now().year}-{count + 1:05d}"


def build_agreement_url(token: str) -> str:
    base = (settings.app_public_url or "").strip()
    if not base:
        base = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:5173"
    return urljoin(base.rstrip("/") + "/", f"partner-agreement/{token}")


def get_by_token(db: Session, token: str) -> PartnerAgreement | None:
    return db.scalar(select(PartnerAgreement).where(PartnerAgreement.access_token == token))


def get_for_registration(db: Session, registration_id: int) -> PartnerAgreement | None:
    return db.scalar(
        select(PartnerAgreement)
        .where(PartnerAgreement.registration_id == registration_id)
        .order_by(PartnerAgreement.id.desc())
    )


def ensure_agreement(db: Session, registration: PartnerRegistration) -> PartnerAgreement:
    """Return this registration's agreement, creating an unsigned one if needed.

    An already-signed agreement is returned as-is so re-approving can never
    silently void a signature the partner has already given.
    """
    existing = get_for_registration(db, registration.id)
    if existing is not None:
        return existing

    row = PartnerAgreement(
        registration_id=registration.id,
        agreement_no=generate_agreement_no(db),
        agreement_version=AGREEMENT_VERSION,
        access_token=secrets.token_urlsafe(32),
        email=registration.email.strip().lower(),
    )
    db.add(row)
    db.flush()
    return row


def issue_otp(agreement: PartnerAgreement) -> tuple[str, int]:
    """Generate and attach a fresh OTP. Returns (otp, expiry_minutes)."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    agreement.otp_code = otp
    agreement.otp_expires_at = _now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    agreement.otp_attempts = 0
    agreement.otp_sent_at = _now()
    agreement.otp_send_count = (agreement.otp_send_count or 0) + 1
    return otp, OTP_EXPIRY_MINUTES


def resend_wait_seconds(agreement: PartnerAgreement) -> int:
    """Seconds the partner must still wait before another OTP may be sent."""
    sent_at = _as_aware(agreement.otp_sent_at)
    if sent_at is None:
        return 0
    elapsed = (_now() - sent_at).total_seconds()
    remaining = OTP_RESEND_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining + 0.999))


class OtpError(Exception):
    """Raised when an OTP cannot be verified; message is safe to show the partner."""


def verify_otp(agreement: PartnerAgreement, submitted: str) -> None:
    """Validate the submitted OTP, consuming it on success.

    Raises OtpError with a partner-facing message on any failure.
    """
    if not agreement.otp_code:
        raise OtpError("OTP expired or not requested. Please request a new one.")

    expires_at = _as_aware(agreement.otp_expires_at)
    if expires_at is None or _now() > expires_at:
        agreement.otp_code = None
        agreement.otp_expires_at = None
        raise OtpError("OTP has expired. Please request a new one.")

    if (agreement.otp_attempts or 0) >= OTP_MAX_ATTEMPTS:
        agreement.otp_code = None
        agreement.otp_expires_at = None
        raise OtpError("Too many incorrect attempts. Please request a new OTP.")

    if agreement.otp_code != (submitted or "").strip():
        agreement.otp_attempts = (agreement.otp_attempts or 0) + 1
        remaining = OTP_MAX_ATTEMPTS - agreement.otp_attempts
        if remaining <= 0:
            agreement.otp_code = None
            agreement.otp_expires_at = None
            raise OtpError("Too many incorrect attempts. Please request a new OTP.")
        plural = "s" if remaining != 1 else ""
        raise OtpError(f"Invalid OTP. {remaining} attempt{plural} remaining.")

    # Correct: consume the code so it can't be replayed.
    agreement.otp_code = None
    agreement.otp_expires_at = None
    agreement.otp_attempts = 0
