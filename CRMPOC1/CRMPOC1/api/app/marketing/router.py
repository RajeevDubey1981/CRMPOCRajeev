"""Marketing, release 1: who may use it. Audiences, campaigns and channels come in the next releases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.marketing.access import (
    Ctx, NEVER_ROLES, get_ctx, has_marketing_menu, kind_of, kind_ticks, menu_flags, require, user_ticks,
)
from app.marketing import meta, secrets_box
from app.marketing.db import get_marketing_db, marketing_enabled, new_marketing_session
from app.marketing.models import MkChannel, MkChannelAsset, MkRoleTick, MkSetting, MkTickHistory, MkUserTick
from app.marketing.rules import ALL_TICKS, KINDS, KINDS_ORDER, LOCKED_TICKS, OPEN_SETTINGS, SETTING_DEFAULTS, TICK_DEFAULTS, TICK_GROUPS
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
    approval_min_audience: Optional[int] = None
    pause_days: Optional[int] = None


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
        if role_key(u.role) not in NEVER_ROLES and (role_key(u.role) in ("marketing", "marketing_manager", "sales", "sales_manager") or u.can_manage_marketing)
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
        "rules": {k: get_setting(mdb, k) for k in OPEN_SETTINGS},
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
    if not (ctx.has("settings") or ctx.has("cost")):
        raise HTTPException(403, "Only a Marketing manager, Admin or Sub Admin change these settings")
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


# ---------------- Meta: log in, ad accounts, campaigns (read only in this release) ----------------
def _meta_channel(mdb: Session) -> MkChannel | None:
    return mdb.scalar(select(MkChannel).where(MkChannel.platform == "meta", MkChannel.status != "removed").order_by(MkChannel.id.desc()))


def _meta_token(ch: MkChannel) -> str:
    token = secrets_box.unseal(ch.token_enc).get("access_token")
    if not token:
        raise HTTPException(409, "The Meta login cannot be read: connect Meta again")
    if ch.token_expires_at and ch.token_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        ch.status = "expired"
        raise HTTPException(409, "The Meta login has expired: connect Meta again")
    return token


@router.get("/meta/status")
def meta_status(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db)):
    if not (ctx.has("cost") or ctx.has("connect")):
        raise HTTPException(403, "You do not have this tick in Marketing")
    ch = _meta_channel(mdb)
    days = None
    if ch and ch.token_expires_at:
        days = (ch.token_expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
    return {
        "configured": meta.configured(),
        "connected": bool(ch and ch.status == "connected"),
        "status": ch.status if ch else "not connected",
        "name": ch.ext_name if ch else None,
        "scopes": ch.scopes.split(",") if ch and ch.scopes else [],
        "days_left": days,
        "can_connect": ctx.has("connect"),
        "redirect_uri": meta.settings.meta_redirect_uri if ctx.has("connect") else None,
    }


@router.get("/meta/connect")
def meta_connect(ctx: Ctx = Depends(require("connect"))):
    """The address of Meta's own login page. Nothing is typed into the CRM."""
    from app.security import create_access_token

    state = create_access_token(subject=str(ctx.user.id), extra_claims={"purpose": "meta_connect"})
    try:
        return {"url": meta.login_url(state)}
    except meta.MetaError as exc:
        raise HTTPException(409, str(exc))


@router.get("/meta/callback", include_in_schema=False)
def meta_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    """Meta sends the browser back here after the login. The state says who started it; no password or token is shown."""
    from app.security import decode_token

    base = "/marketing/channels"
    if error or not code:
        return RedirectResponse(f"{base}?meta=cancelled")
    try:
        claims = decode_token(state)
        if claims.get("purpose") != "meta_connect":
            raise ValueError("wrong purpose")
        user_id = int(claims["sub"])
    except Exception:
        return RedirectResponse(f"{base}?meta=failed")
    mdb = new_marketing_session()
    try:
        try:
            got = meta.exchange_code(code)
            who = meta.me(got["access_token"])
            accounts = meta.ad_accounts(got["access_token"])
        except meta.MetaError:
            return RedirectResponse(f"{base}?meta=failed")
        for old in mdb.scalars(select(MkChannel).where(MkChannel.platform == "meta", MkChannel.status != "removed")):
            old.status = "removed"
            old.token_enc = None
        ch = MkChannel(
            platform="meta", ext_user_id=who.get("id"), ext_name=who.get("name", ""), token_enc=secrets_box.seal({"access_token": got["access_token"]}),
            token_expires_at=(datetime.now(timezone.utc) + timedelta(seconds=got["expires_in"])) if got["expires_in"] else None,
            scopes=",".join(meta.SCOPES_READ), status="connected", connected_by=user_id,
        )
        mdb.add(ch)
        mdb.flush()
        for a in accounts:
            mdb.add(MkChannelAsset(channel_id=ch.id, kind="ad_account", ext_id=str(a.get("account_id")), name=a.get("name", ""), currency=a.get("currency"), in_use=len(accounts) == 1))
        mdb.add(MkTickHistory(role_key=None, crm_user_id=user_id, tick_key="meta_connected", allowed=True, by_user_id=user_id, by_name="Meta login"))
        mdb.commit()
    finally:
        mdb.close()
    return RedirectResponse(f"{base}?meta=connected")


@router.post("/meta/disconnect")
def meta_disconnect(ctx: Ctx = Depends(require("connect")), mdb: Session = Depends(get_marketing_db)):
    ch = _meta_channel(mdb)
    if ch:
        ch.status = "removed"
        ch.token_enc = None
        mdb.add(MkTickHistory(role_key=None, crm_user_id=ctx.user.id, tick_key="meta_disconnected", allowed=False, by_user_id=ctx.user.id, by_name=ctx.user.name))
        mdb.commit()
    return {"connected": False}


@router.get("/meta/ad-accounts")
def meta_ad_accounts(ctx: Ctx = Depends(require("cost")), mdb: Session = Depends(get_marketing_db)):
    ch = _meta_channel(mdb)
    if ch is None or ch.status != "connected":
        raise HTTPException(409, "Meta is not connected")
    token = _meta_token(ch)
    try:
        live = {str(a.get("account_id")): a for a in meta.ad_accounts(token)}
    except meta.MetaError as exc:
        raise HTTPException(502, str(exc))
    mine = {a.ext_id: a for a in mdb.scalars(select(MkChannelAsset).where(MkChannelAsset.channel_id == ch.id, MkChannelAsset.kind == "ad_account"))}
    out = []
    for ext_id, a in live.items():
        row = mine.get(ext_id)
        if row is None:
            row = MkChannelAsset(channel_id=ch.id, kind="ad_account", ext_id=ext_id, name=a.get("name", ""), currency=a.get("currency"), in_use=False)
            mdb.add(row)
        out.append({"id": ext_id, "name": a.get("name", ""), "currency": a.get("currency"), "status": a.get("account_status"), "amount_spent": a.get("amount_spent"), "business": (a.get("business") or {}).get("name"), "in_use": row.in_use})
    mdb.commit()
    return out


@router.put("/meta/ad-accounts/{ext_id}")
def meta_use_ad_account(ext_id: str, in_use: bool = Query(...), ctx: Ctx = Depends(require("connect")), mdb: Session = Depends(get_marketing_db)):
    ch = _meta_channel(mdb)
    row = mdb.scalar(select(MkChannelAsset).where(MkChannelAsset.channel_id == (ch.id if ch else 0), MkChannelAsset.kind == "ad_account", MkChannelAsset.ext_id == ext_id))
    if row is None:
        raise HTTPException(404, "Ad account not found")
    row.in_use = in_use
    mdb.commit()
    return {"id": ext_id, "in_use": in_use}


@router.get("/meta/campaigns")
def meta_campaigns(account: str = Query(..., min_length=3, max_length=40), ctx: Ctx = Depends(require("cost")), mdb: Session = Depends(get_marketing_db)):
    ch = _meta_channel(mdb)
    if ch is None or ch.status != "connected":
        raise HTTPException(409, "Meta is not connected")
    allowed = {a.ext_id for a in mdb.scalars(select(MkChannelAsset).where(MkChannelAsset.channel_id == ch.id, MkChannelAsset.kind == "ad_account", MkChannelAsset.in_use.is_(True)))}
    if account.removeprefix("act_") not in allowed:
        raise HTTPException(403, "This ad account is not switched on for the CRM")
    token = _meta_token(ch)
    try:
        return meta.campaigns(token, account)
    except meta.MetaError as exc:
        raise HTTPException(502, str(exc))
