import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.services.permissions import can_act_on
from app.services.role_access import PROTECTED_USER_ROLES, is_system_admin, role_key
from app.models.user import User
from app.schemas.user import BankDetailsOut, ResetPasswordRequest, UserCreate, UserOut, UserUpdate
from app.security import hash_password
from app.services import coverage as coverage_service
from app.services.geo import canonical_state, split_pincodes
from app.services.file_service import read_upload_bytes
from app.services.vendor_accounts import (
    ensure_vendor_for_user,
    sync_vendor_for_user_email_update,
    vendor_master_for_user,
)

router = APIRouter(prefix="/api/users", tags=["users"])

ID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ID_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "application/pdf"}
PROFILE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PROFILE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def user_manager(flag: str):
    """Admin may manage every user. Any other role may too, but only once Admin > Roles has actually
    ticked users.<flag> for it -- this used to hardcode "must be Sub Admin", so a role like Accounts
    Manager could have users.can_edit ticked on its card and still get 403 every time, which failed
    closed (not a security hole) but was a real glitch (security review, 2026-10-27). Never Admin / Sub
    Admin accounts themselves (see _guard_protected)."""

    def checker(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> User:
        if is_system_admin(user):
            return user
        if can_act_on(db, user, "users", flag, None):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    return checker


def _guard_protected(actor: User, *roles: str | None) -> None:
    if actor.role == "admin":
        return
    for r in roles:
        if r is not None and role_key(r) in PROTECTED_USER_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an Admin can create or change Admin and Sub Admin accounts")


def _normalized_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalized_phone(value: str | None) -> str:
    """Digits only, keeping just the last 10 so "+91 96544 09709" and "09654409709" match "9654409709"."""
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits[-10:] if len(digits) > 10 else digits


def _phone_in_use(db: Session, normalized_phone: str, *, exclude_user_id: int | None = None) -> bool:
    """Compares digits-only so "+91 96544 09709" and "9654409709" count as the same number."""
    q = select(User.id, User.phone).where(User.phone.is_not(None), User.deleted_at.is_(None))
    if exclude_user_id is not None:
        q = q.where(User.id != exclude_user_id)
    return any(_normalized_phone(phone) == normalized_phone for _uid, phone in db.execute(q))


def _list_of(text: str | None) -> list[str]:
    try:
        return [str(s) for s in json.loads(text)] if text else []
    except ValueError:
        return []


def _skills_of(user: User) -> list[str]:
    return _list_of(user.skills)


def _user_out(db: Session, user: User) -> UserOut:
    vendor = vendor_master_for_user(db, user)
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        phone=user.phone,
        is_active=user.is_active,
        can_manage_bids=bool(user.can_manage_bids),
        can_manage_marketing=bool(user.can_manage_marketing),
        pincode=user.pincode,
        state=user.state,
        district=user.district,
        extra_pincodes=split_pincodes(user.extra_pincodes),
        coverage=coverage_service.load(user.coverage),
        skills=_skills_of(user),
        vendor_types=_list_of(user.vendor_types),
        created_at=user.created_at,
        updated_at=user.updated_at,
        vendor_id=vendor.id if vendor else None,
        vendor_code=vendor.vendor_code if vendor else None,
        has_id_proof=user.id_proof_blob is not None,
        id_proof_filename=user.id_proof_filename,
        has_profile_picture=user.profile_picture_blob is not None,
        profile_picture_filename=user.profile_picture_filename,
        has_bank_details=bool(user.bank_account_number),
    )


async def _user_payload(request: Request, schema):
    content_type = request.headers.get("content-type", "").lower()
    id_proof = profile_picture = None
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            raw = json.loads(str(form.get("payload") or "{}"))
            id_proof = form.get("id_proof")
            profile_picture = form.get("profile_picture")
        else:
            raw = await request.json()
        return schema.model_validate(raw), id_proof, profile_picture
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        detail = exc.errors() if isinstance(exc, ValidationError) else "Invalid user details"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


async def _read_user_files(id_proof, profile_picture):
    id_data = profile_data = None
    if id_proof is not None and hasattr(id_proof, "read") and getattr(id_proof, "filename", None):
        id_data = await read_upload_bytes(id_proof, allowed_ext=ID_EXTENSIONS, allowed_mime=ID_MIME_TYPES)
    if profile_picture is not None and hasattr(profile_picture, "read") and getattr(profile_picture, "filename", None):
        profile_data = await read_upload_bytes(profile_picture, allowed_ext=PROFILE_EXTENSIONS, allowed_mime=PROFILE_MIME_TYPES)
    return id_data, profile_data


def _assign_user_files(user: User, id_data, profile_data) -> None:
    if id_data:
        user.id_proof_blob, user.id_proof_filename, user.id_proof_content_type, user.id_proof_size_bytes = id_data
    if profile_data:
        user.profile_picture_blob, user.profile_picture_filename, user.profile_picture_content_type, user.profile_picture_size_bytes = profile_data


def _fits_filters(u: User, state: str | None, digits: str, part: str, vtype: str, cat: str) -> bool:
    cov = coverage_service.load(u.coverage)
    rows = (cov or {}).get("states") or {}
    everywhere = bool(cov) and cov.get("mode") == "all"
    if vtype and vtype not in {t.lower() for t in _list_of(u.vendor_types)}:
        return False
    if cat and cat not in {c.lower() for c in _list_of(u.skills)}:
        return False
    if digits:
        pins = [p for p in [u.pincode, *split_pincodes(u.extra_pincodes)] if p] + [p for r in rows.values() for p in r.get("pins") or []]
        if not any(p.startswith(digits) for p in pins):
            return False
    if state and not (u.state == state or everywhere or any(coverage_service.plain(n) == coverage_service.plain(state) for n in rows)):
        return False
    if part:
        home = part in (u.district or "").lower()
        covered = everywhere or any(
            (not state or coverage_service.plain(n) == coverage_service.plain(state)) and (r.get("all") or any(part in d.lower() for d in r.get("districts") or []))
            for n, r in rows.items()
        )
        if not (home or covered):
            return False
    return True


@router.get("", response_model=list[UserOut])
def list_users(
    role: str | None = Query(None),
    active: bool | None = Query(None, description="If true, only active. If false, only inactive. Omit for both."),
    search: str | None = Query(None),
    pincode: str | None = Query(None, description="Pin code, or its first digits"),
    state: str | None = Query(None),
    district: str | None = Query(None, description="Part of the district name"),
    vendor_type: str | None = Query(None, description="A vendor type, for example GeM"),
    category: str | None = Query(None, description="An item category the person works on or supplies"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Every internal staff role needs this for the engineer/person pickers scattered across the app
    # (assigning a complaint, an installation, a service...), so it stays open to them without a
    # dedicated "users" permission. A vendor or engineer portal account has no such need and could
    # otherwise enumerate every other engineer's and every staff member's name/email/phone/home address --
    # that's real PII with no legitimate use from an external party's own login (security review, 2026-10-27).
    if role_key(user.role) in ("vendor", "engineer"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    stmt = select(User).where(User.deleted_at.is_(None))
    if role:
        stmt = stmt.where(User.role == role)
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            User.name.ilike(like), User.email.ilike(like),
            User.pincode.ilike(like), User.extra_pincodes.ilike(like), User.district.ilike(like), User.state.ilike(like),
            User.coverage.ilike(like), User.vendor_types.ilike(like), User.skills.ilike(like),
        ))
    users = db.scalars(stmt.order_by(User.id)).all()
    # the place filters also take in where a person is covered (All India, a state, a district or a pin code), not only the home place
    want_state = None
    if state and state.strip():
        try:
            want_state = canonical_state(state) or state.strip()
        except ValueError:
            want_state = state.strip()
    digits = (pincode or "").strip()
    part = (district or "").strip().lower()
    wanted_type = (vendor_type or "").strip().lower()
    wanted_cat = (category or "").strip().lower()
    if want_state or digits or part or wanted_type or wanted_cat:
        users = [u for u in users if _fits_filters(u, want_state, digits, part, wanted_type, wanted_cat)]
    return [_user_out(db, user) for user in users]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    caller: User = Depends(get_current_user),
):
    if role_key(caller.role) in ("vendor", "engineer"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _user_out(db, user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_create")),
):
    body, id_proof, profile_picture = await _user_payload(request, UserCreate)
    _guard_protected(actor, body.role)
    if db.scalar(
        select(User).where(
            func.lower(func.trim(User.email)) == _normalized_email(body.email),
            User.deleted_at.is_(None),
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    new_phone = _normalized_phone(body.phone)
    if new_phone and _phone_in_use(db, new_phone):
        raise HTTPException(status.HTTP_409_CONFLICT, "Phone number already exists")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        phone=body.phone,
        is_active=body.is_active,
        can_manage_bids=bool(body.can_manage_bids) and role_key(body.role) != "vendor",
        can_manage_marketing=bool(body.can_manage_marketing) and role_key(body.role) not in ("vendor", "engineer"),
        pincode=body.pincode,
        state=body.state,
        district=body.district,
        extra_pincodes=",".join(body.extra_pincodes or []) or None,
        coverage=json.dumps(body.coverage) if body.coverage else None,
        skills=json.dumps(body.skills) if body.skills else None,
        vendor_types=json.dumps(body.vendor_types) if body.vendor_types else None,
        bank_account_holder_name=body.bank_account_holder_name,
        bank_name=body.bank_name,
        bank_account_number=body.bank_account_number,
        bank_ifsc=body.bank_ifsc,
        bank_branch=body.bank_branch,
    )
    id_data, profile_data = await _read_user_files(id_proof, profile_picture)
    _assign_user_files(user, id_data, profile_data)
    db.add(user)
    db.flush()
    ensure_vendor_for_user(db, user)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_edit")),
):
    body, id_proof, profile_picture = await _user_payload(request, UserUpdate)
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    data = body.model_dump(exclude_unset=True)
    _guard_protected(actor, user.role, data.get("role"))
    previous_email = user.email
    if "email" in data:
        new_email = (data["email"] or "").strip()
        if _normalized_email(new_email) != _normalized_email(previous_email):
            existing = db.scalar(
                select(User).where(
                    func.lower(func.trim(User.email)) == _normalized_email(new_email),
                    User.id != user.id,
                    User.deleted_at.is_(None),
                )
            )
            if existing:
                raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    if "phone" in data:
        new_phone = _normalized_phone(data["phone"])
        if new_phone and new_phone != _normalized_phone(user.phone) and _phone_in_use(db, new_phone, exclude_user_id=user.id):
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone number already in use")

    if data.get("can_manage_bids") is None:
        data.pop("can_manage_bids", None)
    if data.get("can_manage_marketing") is None:
        data.pop("can_manage_marketing", None)
    if "extra_pincodes" in data:
        data["extra_pincodes"] = ",".join(data["extra_pincodes"] or []) or None
    if "coverage" in data:
        data["coverage"] = json.dumps(data["coverage"]) if data["coverage"] else None
    if "skills" in data:
        data["skills"] = json.dumps(data["skills"]) if data["skills"] else None
    if "vendor_types" in data:
        data["vendor_types"] = json.dumps(data["vendor_types"]) if data["vendor_types"] else None
    for field, value in data.items():
        setattr(user, field, value)
    id_data, profile_data = await _read_user_files(id_proof, profile_picture)
    _assign_user_files(user, id_data, profile_data)
    if role_key(user.role) == "vendor":
        user.can_manage_bids = False  # vendors use the vendor side of Bids, never the bid team side
    if role_key(user.role) in ("vendor", "engineer"):
        user.can_manage_marketing = False  # these two never get Marketing
    sync_vendor_for_user_email_update(db, user, previous_email)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


def _file_response(contents: bytes | None, content_type: str | None, filename: str | None) -> Response:
    if contents is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    safe_name = filename or "document"
    return Response(
        content=contents,
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(safe_name)}", "Cache-Control": "private, no-store"},
    )


@router.get("/{user_id}/id-proof")
def get_id_proof(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_view")),
):
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    _guard_protected(actor, user.role)
    return _file_response(user.id_proof_blob, user.id_proof_content_type, user.id_proof_filename)


@router.get("/{user_id}/profile-picture")
def get_profile_picture(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_view")),
):
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    _guard_protected(actor, user.role)
    return _file_response(user.profile_picture_blob, user.profile_picture_content_type, user.profile_picture_filename)


@router.get("/{user_id}/bank-details", response_model=BankDetailsOut)
def get_bank_details(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_view")),
):
    """The actual account number/IFSC, for prefilling the Edit User form -- never part of UserOut, which
    any logged-in user can read (GET /api/users has no permission gate beyond being signed in)."""
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    _guard_protected(actor, user.role)
    return BankDetailsOut(
        bank_account_holder_name=user.bank_account_holder_name,
        bank_name=user.bank_name,
        bank_account_number=user.bank_account_number,
        bank_ifsc=user.bank_ifsc,
        bank_branch=user.bank_branch,
    )


@router.put("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_edit")),
):
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    _guard_protected(actor, user.role)
    user.password_hash = hash_password(body.new_password)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(user_manager("can_edit")),
):
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    _guard_protected(admin, user.role)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    user.is_active = False
    db.commit()
