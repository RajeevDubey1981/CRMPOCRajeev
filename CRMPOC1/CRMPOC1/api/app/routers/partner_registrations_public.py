from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.partner_registration import (
    BUSINESS_TYPES,
    FORM_STEPS,
    PARTNER_TYPES,
    PartnerPublicContext,
    PartnerPublicStepSave,
    PartnerPublicSubmit,
)
from app.services.file_service import save_upload
from app.services.partner_registration import (
    DOCUMENT_KEYS,
    apply_step_fields,
    get_by_token,
    hydrate_partner,
    refresh_form_progress,
    validate_submission,
)

router = APIRouter(prefix="/api/partner-registrations/public", tags=["partner-registrations-public"])


def _get_row(db: Session, token: str):
    row = get_by_token(db, token)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registration link is invalid or expired")
    if row.onboarding_status == "Cancelled":
        raise HTTPException(status.HTTP_410_GONE, "This registration has been cancelled")
    return row


@router.get("/{token}", response_model=PartnerPublicContext)
def public_registration_context(token: str, db: Session = Depends(get_db)):
    row = _get_row(db, token)
    if row.form_status == "Invite Sent" and row.form_started_at is None:
        row.form_started_at = datetime.now(timezone.utc)
        row.form_status = "In Progress"
        db.commit()
        db.refresh(row)

    hydrated = hydrate_partner(row)
    return PartnerPublicContext(
        registration_no=row.registration_no,
        partner_type=row.partner_type,
        email=row.email,
        form_status=row.form_status,
        current_form_step=row.current_form_step,
        completion_percent=row.completion_percent,
        is_submitted=row.form_status == "Submitted",
        form_steps=[{"step": step["step"], "title": step["title"]} for step in FORM_STEPS],
        partner_types=list(PARTNER_TYPES),
        business_types=list(BUSINESS_TYPES),
        data=hydrated,
    )


@router.put("/{token}/step", response_model=PartnerPublicContext)
def public_save_step(token: str, body: PartnerPublicStepSave, db: Session = Depends(get_db)):
    row = _get_row(db, token)
    if row.form_status == "Submitted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration has already been submitted")

    try:
        apply_step_fields(row, body.step, body.data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    row.current_form_step = max(row.current_form_step, body.step)
    refresh_form_progress(row)
    db.commit()
    db.refresh(row)
    return public_registration_context(token, db)


@router.post("/{token}/documents/{document_key}", response_model=PartnerPublicContext)
async def public_upload_document(
    token: str,
    document_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if document_key not in DOCUMENT_KEYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid document type")

    row = _get_row(db, token)
    if row.form_status == "Submitted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration has already been submitted")
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is required")

    path = await save_upload(file, module="partners")
    setattr(row, f"{document_key}_path", path)
    if row.form_started_at is None:
        row.form_started_at = datetime.now(timezone.utc)
    row.current_form_step = max(row.current_form_step, 8)
    refresh_form_progress(row)
    db.commit()
    db.refresh(row)
    return public_registration_context(token, db)


@router.post("/{token}/submit", response_model=PartnerPublicContext)
def public_submit_registration(token: str, body: PartnerPublicSubmit, db: Session = Depends(get_db)):
    row = _get_row(db, token)
    if row.form_status == "Submitted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration has already been submitted")
    if not body.declaration_accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Declaration must be accepted")

    row.declaration_accepted = True
    refresh_form_progress(row)
    errors = validate_submission(row)
    if errors:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "; ".join(errors))

    now = datetime.now(timezone.utc)
    row.form_status = "Submitted"
    row.form_submitted_at = now
    row.submitted_at = now
    row.status_updated_at = now
    row.onboarding_status = "Registration Submitted"
    row.completion_percent = 100
    row.current_form_step = 9
    db.commit()
    db.refresh(row)
    return public_registration_context(token, db)
