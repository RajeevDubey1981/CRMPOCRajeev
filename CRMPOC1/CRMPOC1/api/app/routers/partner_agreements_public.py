import logging
from html import escape
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.partner_agreement import PartnerAgreement
from app.models.partner_registration import PartnerRegistration
from app.schemas.partner_agreement import (
    AgreementContext,
    AgreementContextPublic,
    AgreementSendOtpOut,
    AgreementSendOtpPublicOut,
    AgreementSignedOut,
    AgreementVerifyOtpIn,
)
from app.services.agreement_text import agreement_for_partner_type
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
from app.services.whatsapp_service import send_partner_agreement_otp_whatsapp

router = APIRouter(prefix="/api/partner-agreements/public", tags=["partner-agreements-public"])
logger = logging.getLogger(__name__)


def _otp_channel() -> str:
    return settings.normalized_partner_agreement_otp_channel


def _mask_email(value: str | None) -> str:
    raw = (value or "").strip()
    if "@" not in raw:
        return raw
    local, domain = raw.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(1, len(local) - 2)
    return f"{masked_local}@{domain}"


def _mask_mobile(value: str | None) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) <= 4:
        return digits
    return f"{'*' * max(0, len(digits) - 4)}{digits[-4:]}"


def _otp_destination_label(registration: PartnerRegistration, agreement: PartnerAgreement) -> str:
    if _otp_channel() == "whatsapp":
        return _mask_mobile(registration.mobile)
    return _mask_email(agreement.email)


def _otp_method_label() -> str:
    return "WhatsApp OTP" if _otp_channel() == "whatsapp" else "Email OTP"


def _signed_method_label(agreement: PartnerAgreement) -> str:
    return agreement.signed_method or "Email OTP"


def _signed_destination_label(registration: PartnerRegistration, agreement: PartnerAgreement) -> str:
    if agreement.signed_destination:
        return agreement.signed_destination
    if _signed_method_label(agreement).lower().startswith("whatsapp"):
        return _mask_mobile(registration.mobile)
    return _mask_email(agreement.email)


def _format_signed_at(value: datetime | None) -> str:
    if value is None:
        return "Not signed"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%d %B %Y, %I:%M:%S %p UTC")


def _agreement_download_html(registration: PartnerRegistration, agreement: PartnerAgreement) -> str:
    agreement_document = agreement_for_partner_type(registration.partner_type)
    partner_name = registration.name or registration.contact_person_name or "Partner"
    signed_method = _signed_method_label(agreement)
    signed_destination = _signed_destination_label(registration, agreement)
    signed_status = "Digitally Signed" if agreement.signed_at else "Unsigned"
    paragraphs = "".join(
        f"<p>{escape(block).replace(chr(10), '<br>')}</p>"
        for block in agreement_document.text.split("\n\n")
        if block.strip()
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(agreement.agreement_no)} - {escape(agreement_document.title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #0f172a; margin: 40px; line-height: 1.45; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    h2 {{ font-size: 16px; margin-top: 28px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }}
    .meta, .signature {{ border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin: 18px 0; }}
    .row {{ display: flex; gap: 16px; padding: 5px 0; border-bottom: 1px solid #e2e8f0; }}
    .row:last-child {{ border-bottom: 0; }}
    .label {{ width: 190px; color: #475569; font-weight: 700; }}
    .value {{ flex: 1; }}
    .status {{ color: #047857; font-weight: 800; }}
    p {{ white-space: normal; margin: 0 0 10px; }}
    @media print {{ body {{ margin: 24px; }} }}
  </style>
</head>
<body>
  <h1>{escape(agreement_document.title)}</h1>
  <div>{escape(agreement_document.effective)} | Version {escape(agreement.agreement_version)}</div>
  <div class="meta">
    <div class="row"><div class="label">Agreement No</div><div class="value">{escape(agreement.agreement_no)}</div></div>
    <div class="row"><div class="label">Registration No</div><div class="value">{escape(registration.registration_no)}</div></div>
    <div class="row"><div class="label">Partner</div><div class="value">{escape(partner_name)}</div></div>
    <div class="row"><div class="label">Registered Email</div><div class="value">{escape(agreement.email)}</div></div>
    <div class="row"><div class="label">Status</div><div class="value status">{escape(signed_status)}</div></div>
  </div>
  <h2>Agreement Terms</h2>
  {paragraphs}
  <h2>Digital Signature Audit</h2>
  <div class="signature">
    <div class="row"><div class="label">Signed Method</div><div class="value">{escape(signed_method)}</div></div>
    <div class="row"><div class="label">Verified Destination</div><div class="value">{escape(signed_destination or '-')}</div></div>
    <div class="row"><div class="label">Signed At</div><div class="value">{escape(_format_signed_at(agreement.signed_at))}</div></div>
    <div class="row"><div class="label">IP Address</div><div class="value">{escape(agreement.ip_address or '-')}</div></div>
    <div class="row"><div class="label">User Agent</div><div class="value">{escape(agreement.user_agent or '-')}</div></div>
    <div class="row"><div class="label">Legal Validity</div><div class="value">Electronic signature recorded under the Information Technology Act, 2000 (India).</div></div>
  </div>
</body>
</html>"""


def _agreement_download_response(registration: PartnerRegistration, agreement: PartnerAgreement) -> Response:
    filename = f"{agreement.agreement_no}_signed_agreement.html"
    return Response(
        content=_agreement_download_html(registration, agreement),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _deliver_otp(registration: PartnerRegistration, agreement: PartnerAgreement, otp: str, expiry_minutes: int) -> None:
    if _otp_channel() == "whatsapp":
        delivered = send_partner_agreement_otp_whatsapp(to_mobile=registration.mobile or "", otp=otp)
        if delivered:
            return
        logger.error("WhatsApp OTP delivery failed; falling back to email for agreement %s", agreement.agreement_no)

    send_partner_agreement_otp_email(
        to=agreement.email,
        otp=otp,
        agreement_no=agreement.agreement_no,
        expiry_minutes=expiry_minutes,
    )


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


@router.get("/{token}", response_model=AgreementContextPublic)
def agreement_context(token: str, db: Session = Depends(get_db)):
    agreement = _get_agreement(db, token)
    registration = _registration(db, agreement)
    agreement_document = agreement_for_partner_type(registration.partner_type)
    return AgreementContextPublic(
        agreement_no=agreement.agreement_no,
        agreement_version=agreement.agreement_version,
        agreement_title=agreement_document.title,
        agreement_effective=agreement_document.effective,
        agreement_text=agreement_document.text,
        registration_no=registration.registration_no,
        partner_name=registration.name or registration.contact_person_name,
        email=_mask_email(agreement.email),
        otp_channel=_otp_channel(),
        otp_destination=_otp_destination_label(registration, agreement),
        is_signed=agreement.signed_at is not None,
        signed_at=agreement.signed_at,
        signed_method=agreement.signed_method,
        signed_destination=agreement.signed_destination,
        resend_wait_seconds=resend_wait_seconds(agreement),
    )


@router.get("/{token}/download")
def download_agreement(token: str, db: Session = Depends(get_db)):
    agreement = _get_agreement(db, token)
    registration = _registration(db, agreement)
    return _agreement_download_response(registration, agreement)


@router.post("/{token}/send-otp", response_model=AgreementSendOtpPublicOut)
def send_agreement_otp(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    agreement = _get_agreement(db, token)
    registration = _registration(db, agreement)
    if agreement.signed_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This agreement has already been signed")

    if _otp_channel() == "whatsapp" and not (registration.mobile or "").strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "WhatsApp OTP is enabled but no mobile number is available for this partner registration",
        )

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

    if _otp_channel() == "whatsapp":
        background_tasks.add_task(
            _deliver_otp,
            registration=registration,
            agreement=agreement,
            otp=otp,
            expiry_minutes=expiry_minutes,
        )
    else:
        background_tasks.add_task(
            send_partner_agreement_otp_email,
            to=agreement.email,
            otp=otp,
            agreement_no=agreement.agreement_no,
            expiry_minutes=expiry_minutes,
        )
    return AgreementSendOtpPublicOut(
        message=f"OTP sent via {_otp_method_label()} to {_otp_destination_label(registration, agreement)}",
        resend_wait_seconds=resend_wait_seconds(agreement),
        otp_channel=_otp_channel(),
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
    agreement.signed_method = _otp_method_label()
    agreement.signed_destination = _otp_destination_label(registration, agreement)

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
        method=_otp_method_label(),
        signed_destination=agreement.signed_destination,
    )
