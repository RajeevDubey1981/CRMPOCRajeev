from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner_agreement import PartnerAgreement
from app.models.partner_registration import PartnerRegistration
from app.schemas.partner_agreement import (
    AgreementContext,
    AgreementSendOtpOut,
    AgreementSignedOut,
    AgreementVerifyOtpIn,
)
from app.services.agreement_text import (
    AGREEMENT_EFFECTIVE,
    AGREEMENT_TEXT,
    AGREEMENT_TITLE,
)
from app.services.email_service import (
    send_partner_agreement_otp_email,
    send_partner_agreement_signed_email,
    send_partner_approval_email,
)
from app.services.partner_agreement import (
    OTP_MAX_SENDS,
    OtpError,
    get_by_token,
    issue_otp,
    resend_wait_seconds,
    verify_otp,
)
from app.services.vendor_accounts import ensure_partner_account

router = APIRouter(prefix="/api/partner-agreements/public", tags=["partner-agreements-public"])


def _client_ip(request: Request) -> str | None:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:45]
    return request.client.host[:45] if request.client else None


def _get_agreement(db: Session, token: str) -> PartnerAgreement:
    row = get_by_token(db, token)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement link is invalid or expired")
    return row


def _registration(db: Session, agreement: PartnerAgreement) -> PartnerRegistration:
    row = db.get(PartnerRegistration, agreement.registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement link is invalid or expired")
    return row


@router.get("/{token}", response_model=AgreementContext)
def agreement_context(token: str, db: Session = Depends(get_db)):
    agreement = _get_agreement(db, token)
    registration = _registration(db, agreement)
    return AgreementContext(
        agreement_no=agreement.agreement_no,
        agreement_version=agreement.agreement_version,
        agreement_title=AGREEMENT_TITLE,
        agreement_effective=AGREEMENT_EFFECTIVE,
        agreement_text=AGREEMENT_TEXT,
        registration_no=registration.registration_no,
        partner_name=registration.name or registration.contact_person_name,
        email=agreement.email,
        is_signed=agreement.signed_at is not None,
        signed_at=agreement.signed_at,
        resend_wait_seconds=resend_wait_seconds(agreement),
    )


@router.post("/{token}/send-otp", response_model=AgreementSendOtpOut)
def send_agreement_otp(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    agreement = _get_agreement(db, token)
    if agreement.signed_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This agreement has already been signed")

    wait = resend_wait_seconds(agreement)
    if wait > 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Please wait {wait} more second{'s' if wait != 1 else ''} before requesting another OTP",
        )
    if (agreement.otp_send_count or 0) >= OTP_MAX_SENDS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many OTP requests for this agreement. Please contact INDcool support.",
        )

    otp, expiry_minutes = issue_otp(agreement)
    db.commit()
    db.refresh(agreement)

    background_tasks.add_task(
        send_partner_agreement_otp_email,
        to=agreement.email,
        otp=otp,
        agreement_no=agreement.agreement_no,
        expiry_minutes=expiry_minutes,
    )
    return AgreementSendOtpOut(
        message=f"OTP sent to {agreement.email}",
        resend_wait_seconds=resend_wait_seconds(agreement),
    )


@router.post("/{token}/verify-otp", response_model=AgreementSignedOut)
def verify_agreement_otp(
    token: str,
    body: AgreementVerifyOtpIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    agreement = _get_agreement(db, token)
    if agreement.signed_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This agreement has already been signed")

    registration = _registration(db, agreement)

    try:
        verify_otp(agreement, body.otp)
    except OtpError as exc:
        # Persist the attempt counter / cleared code before returning.
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    now = datetime.now(timezone.utc)
    agreement.signed_at = now
    agreement.ip_address = _client_ip(request)
    agreement.user_agent = request.headers.get("user-agent")

    # Signing the agreement is what activates the partner: create the vendor
    # account and move the registration to active.
    vendor = ensure_partner_account(db, registration)
    registration.onboarding_status = "Partner Active"
    registration.status_updated_at = now
    db.commit()
    db.refresh(agreement)

    partner_name = registration.name or registration.contact_person_name or "Partner"
    signed_at_display = now.strftime("%d %B %Y, %I:%M:%S %p UTC")

    background_tasks.add_task(
        send_partner_agreement_signed_email,
        to=agreement.email,
        partner_name=partner_name,
        agreement_no=agreement.agreement_no,
        agreement_version=agreement.agreement_version,
        signed_at=signed_at_display,
        ip_address=agreement.ip_address,
    )
    background_tasks.add_task(
        send_partner_approval_email,
        to=agreement.email,
        partner_name=partner_name,
        vendor_code=vendor.vendor_code,
    )

    return AgreementSignedOut(
        agreement_no=agreement.agreement_no,
        agreement_version=agreement.agreement_version,
        email=agreement.email,
        signed_at=agreement.signed_at,
        ip_address=agreement.ip_address,
    )
