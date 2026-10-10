import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.services.permissions import can_act_on
from app.services.role_access import PROTECTED_USER_ROLES, is_sub_admin, role_key
from app.models.user import User
from app.schemas.user import ResetPasswordRequest, UserCreate, UserOut, UserUpdate
from app.security import hash_password
from app.services import coverage as coverage_service
from app.services.geo import canonical_state, split_pincodes
from app.services.vendor_accounts import (
    ensure_vendor_for_user,
    sync_vendor_for_user_email_update,
    vendor_master_for_user,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def user_manager(flag: str):
    """Admin may manage every user. A Sub Admin may manage users only when the role table gives it
    users.<flag>, and never Admin / Sub Admin accounts (see _guard_protected)."""

    def checker(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> User:
        if user.role == "admin":
            return user
        if is_sub_admin(user) and can_act_on(db, user, "users", flag, None):
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
    )


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
    _: User = Depends(get_current_user),
):
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
    _: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _user_out(db, user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_create")),
):
    _guard_protected(actor, body.role)
    if db.scalar(
        select(User).where(
            func.lower(func.trim(User.email)) == _normalized_email(body.email),
            User.deleted_at.is_(None),
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        phone=body.phone,
        is_active=body.is_active,
        can_manage_bids=bool(body.can_manage_bids) and role_key(body.role) != "vendor",
        pincode=body.pincode,
        state=body.state,
        district=body.district,
        extra_pincodes=",".join(body.extra_pincodes or []) or None,
        coverage=json.dumps(body.coverage) if body.coverage else None,
        skills=json.dumps(body.skills) if body.skills else None,
        vendor_types=json.dumps(body.vendor_types) if body.vendor_types else None,
    )
    db.add(user)
    db.flush()
    ensure_vendor_for_user(db, user)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager("can_edit")),
):
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

    if data.get("can_manage_bids") is None:
        data.pop("can_manage_bids", None)
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
    if role_key(user.role) == "vendor":
        user.can_manage_bids = False  # vendors use the vendor side of Bids, never the bid team side
    sync_vendor_for_user_email_update(db, user, previous_email)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


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
