from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserPermissionOut,
    UserOut,
)
from app.schemas.role import MODULES, SUB_MODULES
from app.security import create_access_token, hash_password, verify_password
from app.services.bid_access import synthetic_bid_permission
from app.services.role_access import permission_role_name

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _all_permission_keys() -> list[tuple[str, str | None]]:
    keys: list[tuple[str, str | None]] = []
    for module in MODULES:
        keys.append((module, None))
        for sub_module in SUB_MODULES.get(module, ()):
            keys.append((module, sub_module))
    return keys


def _user_out(db: Session, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    role_name = permission_role_name(user.role)
    role = db.scalar(select(Role).where(func.lower(func.trim(Role.name)) == role_name))
    rows = []
    if role is not None:
        rows = db.scalars(select(Permission).where(Permission.role_id == role.id)).all()
    by_key = {(row.module, row.sub_module): row for row in rows}
    out.permissions = [
        UserPermissionOut(
            module=module,
            sub_module=sub_module,
            can_view=permission.can_view if permission else False,
            can_create=permission.can_create if permission else False,
            can_edit=permission.can_edit if permission else False,
            can_delete=permission.can_delete if permission else False,
            can_export=permission.can_export if permission else False,
        )
        for module, sub_module in _all_permission_keys()
        for permission in [by_key.get((module, sub_module))]
    ]
    # Bids: managers come from the user's tick, vendors from the role card; nobody else gets the module.
    bids_perm = synthetic_bid_permission(db, user)
    for item in out.permissions:
        if item.module == "bids" and item.sub_module is None:
            flags = bids_perm or {}
            item.can_view = flags.get("can_view", False)
            item.can_create = flags.get("can_create", False)
            item.can_edit = flags.get("can_edit", False)
            item.can_delete = flags.get("can_delete", False)
            item.can_export = flags.get("can_export", False)
    # Sales: admins always, other roles through their role card; nobody sees it while the Sales database is not set up.
    from app.sales.access import has_sales_menu

    sales_on = has_sales_menu(db, user)
    for item in out.permissions:
        if item.module == "sales" and item.sub_module is None:
            item.can_view = sales_on
            item.can_create = item.can_edit = item.can_delete = item.can_export = False
    return out


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email, User.deleted_at.is_(None)))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(access_token=token, user=_user_out(db, user))


@router.post("/logout")
def logout(_: User = Depends(get_current_user)):
    # Stateless JWT: client drops the token. Returned for API completeness.
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(db, user)


@router.put("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
