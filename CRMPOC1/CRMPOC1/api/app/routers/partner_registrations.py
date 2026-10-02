from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.partner_registration import PartnerRegistration
from app.models.role import Permission, Role
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.partner_agreement import PartnerAgreementAdminOut
from app.schemas.partner_registration import (
    BUSINESS_TYPES,
    FORM_STATUSES,
    ONBOARDING_STATUSES,
    PARTNER_TYPES,
    PartnerInviteCreate,
    PartnerInviteOut,
    PartnerRegistrationListItem,
    PartnerRegistrationListResponse,
    PartnerRegistrationOut,
    PartnerRegistrationUpdate,
)
from app.services.partner_registration import (
    build_public_registration_url,
    generate_access_token,
    generate_registration_no,
    hydrate_partner,
    refresh_form_progress,
)
from app.services.email_service import (
    send_partner_registration_invite_email,
    send_partner_agreement_invite_email,
    send_partner_approval_email,
    send_partner_rejection_email,
)
from app.services.gst_service import validate_gstin
from app.services.partner_agreement import (
    build_agreement_url,
    ensure_agreement,
    get_for_registration,
)
from app.routers.partner_agreements_public import _agreement_download_response
from app.services.vendor_accounts import ensure_partner_account
from app.services.role_access import is_system_admin, permission_role_name

router = APIRouter(prefix="/api/partner-registrations", tags=["partner-registrations"])

ADMIN_EDITABLE_REGISTRATION_FIELDS = {
    "partner_type",
    "business_type",
    "name",
    "mobile",
    "alternate_mobile",
    "email",
    "website",
    "contact_person_name",
    "contact_designation",
    "firm_address",
    "city",
    "district",
    "state",
    "pincode",
    "gst_no",
    "pan_no",
    "udyam_no",
    "cin_no",
    "aadhaar_no",
    "gem_seller_id",
    "year_of_establishment",
    "annual_turnover",
    "operating_states",
    "product_categories",
    "bank_name",
    "bank_branch",
    "account_holder_name",
    "account_number",
    "ifsc_code",
    "remarks",
    "declaration_accepted",
}

OPTIONAL_TEXT_FIELDS = ADMIN_EDITABLE_REGISTRATION_FIELDS - {
    "partner_type",
    "email",
    "year_of_establishment",
    "annual_turnover",
    "declaration_accepted",
}

UPPERCASE_TEXT_FIELDS = {"gst_no", "pan_no", "udyam_no", "cin_no", "ifsc_code"}


def _normalize_mobile(value: str) -> str:
    digits = "".join(character for character in (value or "") if character.isdigit())
    return digits[-10:]


def _normalize_admin_registration_update(data: dict) -> dict:
    normalized = dict(data)
    for field in OPTIONAL_TEXT_FIELDS:
        if field in normalized and isinstance(normalized[field], str):
            value = normalized[field].strip()
            normalized[field] = value or None
    for field in UPPERCASE_TEXT_FIELDS:
        if normalized.get(field):
            normalized[field] = str(normalized[field]).upper()
    if "email" in normalized and normalized["email"] is not None:
        normalized["email"] = str(normalized["email"]).strip().lower()
    if "mobile" in normalized and normalized["mobile"] is not None:
        normalized["mobile"] = _normalize_mobile(normalized["mobile"])
    if "alternate_mobile" in normalized and normalized["alternate_mobile"] is not None:
        normalized["alternate_mobile"] = _normalize_mobile(normalized["alternate_mobile"]) or None
    return normalized


def _mobile_exists(db: Session, mobile: str) -> bool:
    normalized = _normalize_mobile(mobile)
    if not normalized:
        return False
    existing_registrations = db.scalars(select(PartnerRegistration.mobile)).all()
    existing_users = db.scalars(select(User.phone)).all()
    existing_vendors = db.scalars(select(Vendor.contact_mobile)).all()
    return any(_normalize_mobile(value) == normalized for value in [*existing_registrations, *existing_users, *existing_vendors])


def _email_exists_for_other_record(db: Session, email: str, registration_id: int) -> bool:
    normalized = (email or "").strip().lower()
    if not normalized:
        return False
    email_in_registration = db.scalar(
        select(PartnerRegistration.id).where(
            func.lower(PartnerRegistration.email) == normalized,
            PartnerRegistration.id != registration_id,
        )
    )
    email_in_user = db.scalar(select(User.id).where(func.lower(User.email) == normalized))
    email_in_vendor = db.scalar(select(Vendor.id).where(func.lower(Vendor.email) == normalized))
    return bool(email_in_registration or email_in_user or email_in_vendor)


def _mobile_exists_for_other_record(db: Session, mobile: str, registration_id: int) -> bool:
    normalized = _normalize_mobile(mobile)
    if not normalized:
        return False
    existing_registrations = db.scalars(
        select(PartnerRegistration.mobile).where(PartnerRegistration.id != registration_id)
    ).all()
    existing_users = db.scalars(select(User.phone)).all()
    existing_vendors = db.scalars(select(Vendor.contact_mobile)).all()
    return any(_normalize_mobile(value) == normalized for value in [*existing_registrations, *existing_users, *existing_vendors])


def _has_partner_permission(db: Session, user: User, action: str) -> bool:
    if is_system_admin(user):
        return True
    role_name = permission_role_name(user.role)
    role = db.scalar(select(Role).where(func.lower(func.trim(Role.name)) == role_name))
    if role is None:
        return False
    permission = db.scalar(
        select(Permission).where(
            Permission.role_id == role.id,
            Permission.module == "partner_registrations",
            Permission.sub_module.is_(None),
        )
    )
    return bool(permission and getattr(permission, action, False))


def _require_partner_permission(db: Session, user: User, action: str, message: str) -> None:
    if not _has_partner_permission(db, user, action):
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


def _list_item(row: PartnerRegistration) -> PartnerRegistrationListItem:
    item = PartnerRegistrationListItem.model_validate(row)
    item.registration_url = build_public_registration_url(row.access_token)
    return item


def _deactivate_partner_account(db: Session, row: PartnerRegistration) -> None:
    """Soft-delete the vendor account created for this registration."""
    now = datetime.now(timezone.utc)
    email = row.email.strip().lower()
    vendor = db.scalar(
        select(Vendor).where(
            Vendor.email == email,
            Vendor.deleted_at.is_(None),
        )
    )
    if vendor is not None:
        vendor.is_active = False
        vendor.deleted_at = now

    partner_user = db.scalar(
        select(User).where(
            func.lower(User.email) == email,
            func.lower(User.role) == "vendor",
            User.deleted_at.is_(None),
        )
    )
    if partner_user is not None:
        partner_user.is_active = False
        partner_user.deleted_at = now


@router.get("", response_model=PartnerRegistrationListResponse)
def list_partner_registrations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    partner_type: str | None = Query(None),
    form_status: str | None = Query(None),
    onboarding_status: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_view", "You do not have permission to view partner registrations")
    stmt = select(PartnerRegistration)
    if partner_type:
        stmt = stmt.where(PartnerRegistration.partner_type == partner_type)
    if form_status:
        stmt = stmt.where(PartnerRegistration.form_status == form_status)
    if onboarding_status:
        stmt = stmt.where(PartnerRegistration.onboarding_status == onboarding_status)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                PartnerRegistration.name.ilike(term),
                PartnerRegistration.email.ilike(term),
                PartnerRegistration.mobile.ilike(term),
                PartnerRegistration.contact_person_name.ilike(term),
                PartnerRegistration.registration_no.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(PartnerRegistration.invited_at.desc(), PartnerRegistration.submitted_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return PartnerRegistrationListResponse(
        items=[_list_item(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/meta")
def partner_registration_meta(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_partner_permission(db, user, "can_view", "You do not have permission to view partner registrations")
    return {
        "partner_types": list(PARTNER_TYPES),
        "business_types": list(BUSINESS_TYPES),
        "form_statuses": list(FORM_STATUSES),
        "onboarding_statuses": list(ONBOARDING_STATUSES),
    }


@router.post("/invite", response_model=PartnerInviteOut, status_code=status.HTTP_201_CREATED)
def invite_partner_registration(
    body: PartnerInviteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_create", "You do not have permission to create partner registrations")
    now = datetime.now(timezone.utc)
    email = str(body.email).strip().lower()
    mobile = _normalize_mobile(body.mobile)

    # Check historical rows too: soft-deleted users/vendors still occupy the
    # database's unique email and vendor-code constraints.
    email_in_registration = db.scalar(
        select(PartnerRegistration.id).where(func.lower(PartnerRegistration.email) == email)
    )
    email_in_user = db.scalar(
        select(User.id).where(func.lower(User.email) == email)
    )
    email_in_vendor = db.scalar(
        select(Vendor.id).where(func.lower(Vendor.email) == email)
    )
    if email_in_registration or email_in_user or email_in_vendor:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This email is already registered or has an existing user/vendor account.",
        )

    if _mobile_exists(db, mobile):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This mobile number is already registered or linked to an existing user/vendor account.",
        )

    token = generate_access_token()
    row = PartnerRegistration(
        registration_no=generate_registration_no(db),
        access_token=token,
        partner_type=body.partner_type,
        email=email,
        contact_person_name=body.contact_person_name.strip() if body.contact_person_name else None,
        mobile=mobile,
        name=body.name.strip() if body.name else None,
        form_status="Invite Sent",
        current_form_step=1,
        completion_percent=0,
        onboarding_status="Invite Sent",
        invited_at=now,
        submitted_at=now,
        status_updated_at=now,
        created_by=user.id,
    )
    refresh_form_progress(row)
    db.add(row)
    db.commit()
    db.refresh(row)
    background_tasks.add_task(
        send_partner_registration_invite_email,
        to=row.email,
        contact_person_name=row.contact_person_name,
        firm_name=row.name,
        registration_no=row.registration_no,
        registration_url=build_public_registration_url(row.access_token),
    )
    return PartnerInviteOut(
        id=row.id,
        registration_no=row.registration_no,
        access_token=row.access_token,
        registration_url=build_public_registration_url(row.access_token),
        partner_type=row.partner_type,
        email=row.email,
        form_status=row.form_status,
        completion_percent=row.completion_percent,
    )


@router.get("/{registration_id}", response_model=PartnerRegistrationOut)
def get_partner_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_view", "You do not have permission to view partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    return hydrate_partner(row)


@router.get("/{registration_id}/agreement", response_model=PartnerAgreementAdminOut | None)
def get_partner_agreement(
    registration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agreement signing status for the admin review page (null before approval)."""
    _require_partner_permission(db, user, "can_view", "You do not have permission to view partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")

    agreement = get_for_registration(db, registration_id)
    if agreement is None:
        return None
    return PartnerAgreementAdminOut(
        id=agreement.id,
        agreement_no=agreement.agreement_no,
        agreement_version=agreement.agreement_version,
        email=agreement.email,
        agreement_url=build_agreement_url(agreement.access_token),
        is_signed=agreement.signed_at is not None,
        signed_at=agreement.signed_at,
        ip_address=agreement.ip_address,
        signed_method=agreement.signed_method,
        signed_destination=agreement.signed_destination,
        created_at=agreement.created_at,
    )


@router.get("/{registration_id}/agreement/download")
def download_partner_agreement(
    registration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_view", "You do not have permission to view partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    agreement = get_for_registration(db, registration_id)
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement not found")
    return _agreement_download_response(row, agreement)


@router.get("/{registration_id}/gst/validate")
def validate_partner_gstin(
    registration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Look up the vendor-submitted GSTIN so admin can compare it against submitted data before approving."""
    _require_partner_permission(db, user, "can_edit", "You do not have permission to edit partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    gstin = (row.gst_no or "").strip().upper()
    if not gstin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration has no GSTIN submitted")
    return validate_gstin(gstin)


@router.post("/{registration_id}/reject", response_model=PartnerRegistrationOut)
def reject_partner_registration(
    registration_id: int,
    body: PartnerRegistrationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject a submitted registration: reopen the form for the vendor to redo, and email them to restart."""
    _require_partner_permission(db, user, "can_edit", "You do not have permission to edit partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    if row.form_status != "Submitted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a submitted registration can be rejected")

    now = datetime.now(timezone.utc)
    row.admin_remark = body.admin_remark or row.admin_remark
    row.onboarding_status = "Rejected"
    row.form_status = "In Progress"
    row.current_form_step = 1
    row.declaration_accepted = False
    row.form_submitted_at = None
    row.status_updated_at = now
    db.commit()
    db.refresh(row)

    background_tasks.add_task(
        send_partner_rejection_email,
        to=row.email,
        contact_person_name=row.contact_person_name,
        firm_name=row.name,
        registration_no=row.registration_no,
        registration_url=build_public_registration_url(row.access_token),
        reason=row.admin_remark,
    )
    return hydrate_partner(row)


@router.post("/{registration_id}/resend-email")
def resend_partner_email(
    registration_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_edit", "You do not have permission to edit partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    if row.onboarding_status == "Cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cancelled registrations cannot receive email")

    if row.onboarding_status in {"Onboarding Approved", "Partner Active"}:
        agreement = ensure_agreement(db, row)
        db.commit()
        db.refresh(agreement)

        # Until the agreement is signed there is no account to welcome them to,
        # so resend the signing link instead of the vendor-code email.
        if agreement.signed_at is None:
            background_tasks.add_task(
                send_partner_agreement_invite_email,
                to=agreement.email,
                contact_person_name=row.contact_person_name,
                firm_name=row.name,
                registration_no=row.registration_no,
                agreement_no=agreement.agreement_no,
                agreement_url=build_agreement_url(agreement.access_token),
            )
            return {
                "message": f"Agreement signing link queued for {row.email}",
                "email_type": "agreement",
            }

        vendor = ensure_partner_account(db, row)
        db.commit()
        background_tasks.add_task(
            send_partner_approval_email,
            to=row.email,
            partner_name=row.name or row.contact_person_name or "Partner",
            vendor_code=vendor.vendor_code,
        )
        return {"message": f"Welcome email queued for {row.email}", "email_type": "welcome"}

    background_tasks.add_task(
        send_partner_registration_invite_email,
        to=row.email,
        contact_person_name=row.contact_person_name,
        firm_name=row.name,
        registration_no=row.registration_no,
        registration_url=build_public_registration_url(row.access_token),
    )
    return {"message": f"Onboarding invite queued for {row.email}", "email_type": "invite"}


@router.put("/{registration_id}", response_model=PartnerRegistrationOut)
def update_partner_registration(
    registration_id: int,
    body: PartnerRegistrationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_edit", "You do not have permission to edit partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")

    data = _normalize_admin_registration_update(body.model_dump(exclude_unset=True))
    status_change_requested = "onboarding_status" in data
    if row.form_status != "Submitted" and status_change_requested and data.get("onboarding_status") != "Cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Partner must submit the form before onboarding status can be updated")

    if "email" in data and data["email"] and data["email"] != row.email.strip().lower():
        if _email_exists_for_other_record(db, data["email"], row.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This email is already registered or has an existing user/vendor account.",
            )
    if "mobile" in data and data["mobile"] and data["mobile"] != _normalize_mobile(row.mobile):
        if _mobile_exists_for_other_record(db, data["mobile"], row.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This mobile number is already registered or linked to an existing user/vendor account.",
            )

    registration_fields_changed = any(field in ADMIN_EDITABLE_REGISTRATION_FIELDS for field in data)
    # Approval no longer creates the partner account. It issues the service
    # agreement and emails a signing link; the vendor account and welcome email
    # are created only once the partner signs (see partner_agreements_public).
    approval_transition = (
        data.get("onboarding_status") == "Onboarding Approved"
        and row.onboarding_status != "Onboarding Approved"
    )
    if "onboarding_status" in data:
        row.status_updated_at = datetime.now(timezone.utc)
    for field, value in data.items():
        setattr(row, field, value)
    if registration_fields_changed:
        refresh_form_progress(row)
    if row.onboarding_status == "Cancelled":
        row.form_status = "Cancelled"
        _deactivate_partner_account(db, row)

    agreement = ensure_agreement(db, row) if approval_transition else None
    if "email" in data and not approval_transition:
        pending_agreement = get_for_registration(db, row.id)
        if pending_agreement is not None and pending_agreement.signed_at is None:
            pending_agreement.email = row.email
    db.commit()
    db.refresh(row)
    if agreement is not None and agreement.signed_at is None:
        background_tasks.add_task(
            send_partner_agreement_invite_email,
            to=agreement.email,
            contact_person_name=row.contact_person_name,
            firm_name=row.name,
            registration_no=row.registration_no,
            agreement_no=agreement.agreement_no,
            agreement_url=build_agreement_url(agreement.access_token),
        )
    return hydrate_partner(row)


@router.delete("/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_partner_permission(db, user, "can_delete", "You do not have permission to delete partner registrations")
    row = db.get(PartnerRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner registration not found")
    db.delete(row)
    db.commit()

