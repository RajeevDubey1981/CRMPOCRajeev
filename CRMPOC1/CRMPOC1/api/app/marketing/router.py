"""Marketing, release 1: who may use it. Audiences, campaigns and channels come in the next releases."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.marketing.access import (
    Ctx, NEVER_ROLES, get_ctx, has_marketing_menu, kind_of, kind_ticks, menu_flags, user_ticks,
)
from app.marketing.db import get_marketing_db, marketing_enabled
from app.marketing.models import MkRoleTick, MkSetting, MkTickHistory, MkUserTick
from app.marketing.rules import ALL_TICKS, KINDS, KINDS_ORDER, LOCKED_TICKS, SETTING_DEFAULTS, TICK_DEFAULTS, TICK_GROUPS
from app.models.user import User
from app.services.role_access import role_key

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


class TicksIn(BaseModel):
    ticks: dict[str, Optional[bool]]


class SettingsIn(BaseModel):
    rate_whatsapp: Optional[float] = None
    rate_sms: Optional[float] = None
    monthly_cap: Optional[int] = None
    daily_limit: Optional[int] = None


def commit(main_db: Session, mdb: Session) -> None:
    mdb.commit()
    main_db.commit()


def get_setting(mdb: Session, key: str) -> str:
    row = mdb.get(MkSetting, key)
    return row.value if row is not None else SETTING_DEFAULTS.get(key, "")


def settings_out(mdb: Session) -> dict:
    return {k: get_setting(mdb, k) for k in SETTING_DEFAULTS}


def _candidates(main_db: Session) -> list[User]:
    """Everyone who has or could have the Marketing menu: the Marketing role, the Sales roles, and anyone with the tick."""
    users = main_db.scalars(select(User).where(User.is_active.is_(True), User.deleted_at.is_(None)).order_by(User.name)).all()
    return [
        u for u in users
        if role_key(u.role) not in NEVER_ROLES and (role_key(u.role) in ("marketing", "sales", "sales_manager") or u.can_manage_marketing)
    ]


@router.get("/enabled")
def enabled(_: User = Depends(get_current_user)):
    return {"enabled": marketing_enabled()}


@router.get("/status")
def marketing_status(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db)):
    return {
        "enabled": True,
        "is_admin": ctx.is_admin,
        "kind": "admin" if ctx.is_admin else kind_of(ctx.user),
        "ticks": sorted(ctx.ticks),
        "menu": menu_flags(ctx),
        "settings": settings_out(mdb) if ctx.has("cost") or ctx.has("settings") else {},
    }


# ---------------- ticks ----------------
@router.get("/ticks")
def ticks_catalog(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    return {
        "groups": [{"group": g, "ticks": [{"key": k, "label": lb, "locked": lk} for k, lb, lk in items]} for g, items in TICK_GROUPS],
        "kinds": [{"key": k, "label": KINDS[k]} for k in KINDS_ORDER],
        "defaults": {k: sorted(v) for k, v in TICK_DEFAULTS.items()},
        "roles": {k: sorted(kind_ticks(mdb, k)) for k in KINDS_ORDER},
        "people": [
            {
                "user_id": u.id, "name": u.name, "role": u.role, "kind": kind_of(u), "has_menu": has_marketing_menu(u),
                "can_manage_marketing": bool(u.can_manage_marketing),
                "ticks": sorted(user_ticks(mdb, u)),
                "overrides": {r.tick_key: r.allowed for r in mdb.scalars(select(MkUserTick).where(MkUserTick.crm_user_id == u.id))},
            }
            for u in _candidates(main_db)
        ],
    }


def _history(mdb: Session, ctx: Ctx, *, role_key_=None, user_id=None, tick_key: str, allowed):
    mdb.add(MkTickHistory(role_key=role_key_, crm_user_id=user_id, tick_key=tick_key, allowed=allowed, by_user_id=ctx.user.id, by_name=ctx.user.name))


@router.put("/ticks/role/{kind}")
def set_role_ticks(kind: str, body: TicksIn, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    if kind not in KINDS:
        raise HTTPException(404, "Unknown kind of person")
    for key, allowed in body.ticks.items():
        if key not in ALL_TICKS or key in LOCKED_TICKS:
            raise HTTPException(400, f"{key} cannot be ticked for a kind of person")
        row = mdb.scalar(select(MkRoleTick).where(MkRoleTick.role_key == kind, MkRoleTick.tick_key == key))
        default = key in TICK_DEFAULTS[kind]
        if allowed is None or allowed == default:
            if row is not None:
                mdb.delete(row)
        elif row is None:
            mdb.add(MkRoleTick(role_key=kind, tick_key=key, allowed=bool(allowed)))
        else:
            row.allowed = bool(allowed)
        _history(mdb, ctx, role_key_=kind, tick_key=key, allowed=allowed)
    commit(main_db, mdb)
    return {"kind": kind, "ticks": sorted(kind_ticks(mdb, kind))}


@router.put("/ticks/user/{user_id}")
def set_user_ticks(user_id: int, body: TicksIn, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    if user_id == ctx.user.id:
        raise HTTPException(400, "Nobody can tick for themselves")
    u = main_db.get(User, user_id)
    if u is None or u.deleted_at is not None or role_key(u.role) in NEVER_ROLES:
        raise HTTPException(404, "This person cannot use Marketing")
    for key, allowed in body.ticks.items():
        if key not in ALL_TICKS or key in LOCKED_TICKS:
            raise HTTPException(400, f"{key} cannot be ticked for a person")
        row = mdb.scalar(select(MkUserTick).where(MkUserTick.crm_user_id == user_id, MkUserTick.tick_key == key))
        if allowed is None:
            if row is not None:
                mdb.delete(row)
        elif row is None:
            mdb.add(MkUserTick(crm_user_id=user_id, tick_key=key, allowed=bool(allowed)))
        else:
            row.allowed = bool(allowed)
        _history(mdb, ctx, user_id=user_id, tick_key=key, allowed=allowed)
    commit(main_db, mdb)
    return {"user_id": user_id, "ticks": sorted(user_ticks(mdb, u))}


@router.get("/ticks/history")
def ticks_history(limit: int = Query(100, ge=1, le=500), ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin see this")
    rows = list(mdb.scalars(select(MkTickHistory).order_by(MkTickHistory.id.desc()).limit(limit)))
    names = {u.id: u.name for u in main_db.scalars(select(User).where(User.id.in_({r.crm_user_id for r in rows if r.crm_user_id} or {0})))}
    return [
        {"at": r.at.isoformat() if r.at else None, "kind": r.role_key, "person": names.get(r.crm_user_id), "tick": r.tick_key, "allowed": r.allowed, "by": r.by_name}
        for r in rows
    ]


# ---------------- people ----------------
@router.get("/people")
def people(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    """Who has the Marketing menu now (for the Marketing home)."""
    if not ctx.has("view"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    users = main_db.scalars(select(User).where(User.is_active.is_(True), User.deleted_at.is_(None)).order_by(User.name)).all()
    return [{"user_id": u.id, "name": u.name, "role": u.role} for u in users if has_marketing_menu(u)]


# ---------------- settings ----------------
@router.put("/settings")
def update_settings(body: SettingsIn, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.has("settings"):
        raise HTTPException(403, "Only Admin and Sub Admin change these settings")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, (int, float)) and v < 0:
            raise HTTPException(400, f"{k} cannot be negative")
        row = mdb.get(MkSetting, k)
        if row is None:
            mdb.add(MkSetting(key=k, value=str(v)))
        else:
            row.value = str(v)
    commit(main_db, mdb)
    return settings_out(mdb)
