"""Marketing, release 1: who may use it. Audiences, campaigns and channels come in the next releases."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
from app.marketing.models import (
    MkAudience, MkBanner, MkCampaign, MkCampaignLog, MkChannel, MkChannelAsset, MkConsent, MkContactTouch,
    MkLeadInterestToken, MkRoleTick, MkSetting, MkTickHistory, MkUserTick,
)
from app.marketing.rules import ALL_TICKS, KINDS, KINDS_ORDER, LOCKED_TICKS, OPEN_SETTINGS, SETTING_DEFAULTS, TICK_DEFAULTS, TICK_GROUPS
from app.models.order import Order
from app.models.user import User
from app.sales.db import get_sales_db, sales_enabled
from app.sales.models import SalesLead
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


class SystemTokenIn(BaseModel):
    token: str


@router.post("/meta/system-token")
def meta_system_token(body: SystemTokenIn, ctx: Ctx = Depends(require("connect")), mdb: Session = Depends(get_marketing_db)):
    """Connect with a System User token made in Business settings: it belongs to the company, not to one person's login, and does
    not run out after 60 days. The token is checked with Meta, saved encrypted and never shown again."""
    if not meta.configured():
        raise HTTPException(409, "Meta is not set up on the server yet")
    token = (body.token or "").strip()
    if len(token) < 20 or " " in token:
        raise HTTPException(422, "That does not look like a token")
    try:
        who = meta.me(token)
        accounts = meta.ad_accounts(token)
    except meta.MetaError as exc:
        raise HTTPException(400, f"Meta did not accept this token: {exc}")
    for old in mdb.scalars(select(MkChannel).where(MkChannel.platform == "meta", MkChannel.status != "removed")):
        old.status = "removed"
        old.token_enc = None
    ch = MkChannel(
        platform="meta", ext_user_id=who.get("id"), ext_name=who.get("name", "") or "System user", token_enc=secrets_box.seal({"access_token": token}),
        token_expires_at=None, scopes=",".join(meta.SCOPES_READ), status="connected", connected_by=ctx.user.id,
    )
    mdb.add(ch)
    mdb.flush()
    for a in accounts:
        mdb.add(MkChannelAsset(channel_id=ch.id, kind="ad_account", ext_id=str(a.get("account_id")), name=a.get("name", ""), currency=a.get("currency"), in_use=len(accounts) == 1))
    mdb.add(MkTickHistory(role_key=None, crm_user_id=ctx.user.id, tick_key="meta_connected", allowed=True, by_user_id=ctx.user.id, by_name=ctx.user.name))
    mdb.commit()
    return {"connected": True, "name": ch.ext_name, "ad_accounts": len(accounts)}


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


@router.get("/meta/diagnose")
def meta_diagnose(ctx: Ctx = Depends(require("connect")), mdb: Session = Depends(get_marketing_db)):
    """For Admin: what Meta gave the saved login, in words that help find why an ad account is missing."""
    ch = _meta_channel(mdb)
    if ch is None or ch.status != "connected":
        raise HTTPException(409, "Meta is not connected")
    token = _meta_token(ch)
    try:
        return meta.diagnose(token)
    except meta.MetaError as exc:
        raise HTTPException(502, str(exc))


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


# ---------------- festive banner ----------------
class BannerIn(BaseModel):
    name: str
    theme: str = "green"
    greeting: str = ""
    headline: str
    pill1: str = ""
    pill2: str = ""
    cta_text: str = "Shop Now"
    cta_link: str = ""
    image_path: Optional[str] = None
    start_date: date
    end_date: date
    target_type: str = "all"
    target_audience_id: Optional[int] = None
    is_enabled: bool = True


def _banner_out(b: MkBanner, audience_name: str | None = None) -> dict:
    today = datetime.now(timezone.utc).date()
    return {
        "id": b.id, "name": b.name, "theme": b.theme, "greeting": b.greeting, "headline": b.headline,
        "pill1": b.pill1, "pill2": b.pill2, "cta_text": b.cta_text, "cta_link": b.cta_link, "image_path": b.image_path,
        "start_date": b.start_date.isoformat(), "end_date": b.end_date.isoformat(),
        "target_type": b.target_type, "target_audience_id": b.target_audience_id, "target_audience_name": audience_name,
        "is_enabled": b.is_enabled,
        "is_active_now": b.is_enabled and b.start_date <= today <= b.end_date,
    }


# A banner image is a wide strip meant to sit above an email's own content -- not a square social post.
# 1200x300px (4:1), JPG or PNG, under 2MB. It is re-encoded on upload (EXIF stripped, capped at 1920px).
BANNER_IMAGE_GUIDE = {
    "recommended_size": "1200 x 300 px (a 4:1 wide strip, like the top of a bank's festive email)",
    "formats": ["JPG", "PNG"],
    "max_size_mb": 2,
    "note": "Keep important text inside the middle 80% of the image -- some mail apps crop the edges.",
}


@router.get("/banners/image-guide")
def banner_image_guide(_: Ctx = Depends(get_ctx)):
    return BANNER_IMAGE_GUIDE


@router.post("/banners/upload-image")
async def upload_banner_image(file: UploadFile = File(...), ctx: Ctx = Depends(require("banner_edit"))):
    from app.services.file_service import save_upload, to_public_upload_path

    path = await save_upload(file, module="marketing_banners", allowed_ext={".jpg", ".jpeg", ".png"}, allowed_mime={"image/jpeg", "image/png", "image/jpg"})
    return {"image_path": to_public_upload_path(path)}


@router.get("/banners")
def list_banners(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db)):
    if not (ctx.has("banner_edit") or ctx.has("view")):
        raise HTTPException(403, "You do not have this tick in Marketing")
    rows = mdb.scalars(select(MkBanner).order_by(MkBanner.start_date.desc())).all()
    names = _audience_names(mdb, {r.target_audience_id for r in rows if r.target_audience_id})
    return [_banner_out(b, names.get(b.target_audience_id)) for b in rows]


@router.post("/banners")
def create_banner(body: BannerIn, ctx: Ctx = Depends(require("banner_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date cannot be before the start date")
    if body.target_type == "audience" and not body.target_audience_id:
        raise HTTPException(400, "Pick an audience to target, or switch target back to Everyone")
    b = MkBanner(**body.model_dump(), created_by=ctx.user.id)
    mdb.add(b)
    commit(main_db, mdb)
    audience = mdb.get(MkAudience, b.target_audience_id) if b.target_audience_id else None
    return _banner_out(b, audience.name if audience else None)


@router.put("/banners/{banner_id}")
def update_banner(banner_id: int, body: BannerIn, ctx: Ctx = Depends(require("banner_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    b = mdb.get(MkBanner, banner_id)
    if b is None:
        raise HTTPException(404, "Banner not found")
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date cannot be before the start date")
    if body.target_type == "audience" and not body.target_audience_id:
        raise HTTPException(400, "Pick an audience to target, or switch target back to Everyone")
    for key, value in body.model_dump().items():
        setattr(b, key, value)
    commit(main_db, mdb)
    audience = mdb.get(MkAudience, b.target_audience_id) if b.target_audience_id else None
    return _banner_out(b, audience.name if audience else None)


@router.delete("/banners/{banner_id}")
def delete_banner(banner_id: int, ctx: Ctx = Depends(require("banner_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    b = mdb.get(MkBanner, banner_id)
    if b is None:
        raise HTTPException(404, "Banner not found")
    mdb.delete(b)
    commit(main_db, mdb)
    return {"deleted": True}


# ---------------- consent / STOP list ----------------
def normalize_contact(value: str | None) -> str | None:
    """A phone's digits, or a lowercased/trimmed email -- so the same person matches however it was typed."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if "@" in v:
        return v.lower()
    digits = "".join(ch for ch in v if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else (digits or None)


def _stopped_keys(mdb: Session, channel: str = "email") -> set[str]:
    rows = mdb.scalars(select(MkConsent.contact_key).where(MkConsent.channel.in_(["all", channel])))
    return set(rows)


class ConsentIn(BaseModel):
    contact: str
    channel: str = "all"
    reason: str = ""


def _consent_out(c: MkConsent) -> dict:
    return {
        "id": c.id, "contact": c.contact_display, "channel": c.channel, "reason": c.reason,
        "source": c.source, "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/consent")
def list_consent(ctx: Ctx = Depends(require("consent_edit")), mdb: Session = Depends(get_marketing_db)):
    rows = mdb.scalars(select(MkConsent).order_by(MkConsent.id.desc())).all()
    return [_consent_out(c) for c in rows]


@router.post("/consent")
def add_consent(body: ConsentIn, ctx: Ctx = Depends(require("consent_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    key = normalize_contact(body.contact)
    if not key:
        raise HTTPException(400, "Enter a phone number or an email")
    channel = body.channel if body.channel in ("all", "email", "whatsapp", "sms") else "all"
    existing = mdb.scalar(select(MkConsent).where(MkConsent.contact_key == key, MkConsent.channel == channel))
    if existing:
        return _consent_out(existing)
    c = MkConsent(contact_key=key, contact_display=body.contact.strip(), channel=channel, reason=body.reason.strip(), source="manual", created_by=ctx.user.id)
    mdb.add(c)
    commit(main_db, mdb)
    return _consent_out(c)


@router.delete("/consent/{consent_id}")
def remove_consent(consent_id: int, ctx: Ctx = Depends(require("consent_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    c = mdb.get(MkConsent, consent_id)
    if c is None:
        raise HTTPException(404, "Not on the STOP list")
    mdb.delete(c)
    commit(main_db, mdb)
    return {"deleted": True}


# ---------------- audiences ----------------
class AudienceIn(BaseModel):
    name: str
    source: str = "prospects"  # prospects | customers
    market: Optional[str] = None
    stage: Optional[str] = None
    state: Optional[str] = None
    stale_days: Optional[int] = None
    heat: Optional[str] = None
    priority: Optional[str] = None
    csd_tier: Optional[str] = None  # only meaningful when market is "csd" or "gem"


def _apply_csd_tier(q, column, a: dict):
    tier = a.get("csd_tier")
    if not tier or a.get("market") not in ("csd", "gem"):
        return q
    if tier == "unset":
        return q.filter(column.is_(None))
    return q.filter(column == tier)


def _count_prospects(sales_db: Session | None, mdb: Session, ctx: Ctx, a: dict) -> int:
    if sales_db is None or not sales_enabled():
        return 0
    q = sales_db.query(SalesLead.phone, SalesLead.email)
    if a.get("market"):
        q = q.filter(SalesLead.lead_type == a["market"])
    q = _apply_csd_tier(q, SalesLead.csd_tier, a)
    if a.get("stage"):
        q = q.filter(SalesLead.status == a["stage"])
    if a.get("state"):
        q = q.filter(SalesLead.state == a["state"])
    if a.get("heat"):
        q = q.filter(SalesLead.heat == a["heat"])
    if a.get("priority"):
        q = q.filter(SalesLead.priority == a["priority"])
    if a.get("stale_days"):
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(a["stale_days"]))
        q = q.filter((SalesLead.last_action_at.is_(None)) | (SalesLead.last_action_at <= cutoff))
    if not ctx.has("aud_all"):
        q = q.filter(SalesLead.owner_user_id == ctx.user.id)
    stopped = _stopped_keys(mdb)
    return sum(1 for phone, email in q.all() if normalize_contact(phone) not in stopped and normalize_contact(email) not in stopped)


def _count_customers(main_db: Session, mdb: Session, a: dict) -> int:
    q = main_db.query(Order.customer_contact, Order.customer_email).filter(Order.customer_contact.isnot(None), Order.deleted_at.is_(None))
    if a.get("market"):
        q = q.filter(Order.market == a["market"])
    q = _apply_csd_tier(q, Order.csd_tier, a)
    if a.get("state"):
        q = q.filter(Order.customer_state == a["state"])
    if a.get("stale_days"):
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=int(a["stale_days"]))
        q = q.filter(Order.order_date <= cutoff)
    stopped = _stopped_keys(mdb)
    seen: set[str] = set()
    count = 0
    for contact, email in q.distinct().all():
        key = normalize_contact(contact) or normalize_contact(email)
        if not key or key in seen:
            continue
        if normalize_contact(contact) in stopped or normalize_contact(email) in stopped:
            continue
        seen.add(key)
        count += 1
    return count


def _prospect_rows(sales_db: Session | None, ctx: Ctx, a: dict) -> list[tuple[int | None, str, str, str | None]]:
    """[(lead_id, name, phone, email), ...] for an audience of source=prospects, before consent/cooldown filtering."""
    if sales_db is None or not sales_enabled():
        return []
    q = sales_db.query(SalesLead.id, SalesLead.name, SalesLead.phone, SalesLead.email)
    if a.get("market"):
        q = q.filter(SalesLead.lead_type == a["market"])
    q = _apply_csd_tier(q, SalesLead.csd_tier, a)
    if a.get("stage"):
        q = q.filter(SalesLead.status == a["stage"])
    if a.get("state"):
        q = q.filter(SalesLead.state == a["state"])
    if a.get("heat"):
        q = q.filter(SalesLead.heat == a["heat"])
    if a.get("priority"):
        q = q.filter(SalesLead.priority == a["priority"])
    if a.get("stale_days"):
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(a["stale_days"]))
        q = q.filter((SalesLead.last_action_at.is_(None)) | (SalesLead.last_action_at <= cutoff))
    if not ctx.has("aud_all"):
        q = q.filter(SalesLead.owner_user_id == ctx.user.id)
    return list(q.all())


def _customer_rows(main_db: Session, a: dict) -> list[tuple[int | None, str, str, str | None]]:
    """[(None, name, phone, email), ...] for an audience of source=customers, deduped by contact, before consent/cooldown filtering.
    The id slot is always None -- a customer row has no Sales lead to link an interest-form submission back to."""
    q = main_db.query(Order.customer_name, Order.customer_contact, Order.customer_email).filter(
        Order.customer_contact.isnot(None), Order.deleted_at.is_(None)
    )
    if a.get("market"):
        q = q.filter(Order.market == a["market"])
    q = _apply_csd_tier(q, Order.csd_tier, a)
    if a.get("state"):
        q = q.filter(Order.customer_state == a["state"])
    if a.get("stale_days"):
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=int(a["stale_days"]))
        q = q.filter(Order.order_date <= cutoff)
    seen: set[str] = set()
    out: list[tuple[int | None, str, str, str | None]] = []
    for name, contact, email in q.distinct().all():
        key = normalize_contact(contact) or normalize_contact(email)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((None, name, contact, email))
    return out


def _audience_rows(main_db: Session, sales_db: Session | None, ctx: Ctx, a: dict) -> list[tuple[int | None, str, str, str | None]]:
    if a.get("source") == "customers":
        return _customer_rows(main_db, a) if ctx.has("aud_all") else []
    return _prospect_rows(sales_db, ctx, a)


def _audience_count(main_db: Session, sales_db: Session | None, mdb: Session, ctx: Ctx, a: dict) -> int:
    if a.get("source") == "customers":
        if not ctx.has("aud_all"):
            return 0  # only an "all CRM data" tick may build audiences from existing customers
        return _count_customers(main_db, mdb, a)
    return _count_prospects(sales_db, mdb, ctx, a)


def _audience_out(a: MkAudience, count: int) -> dict:
    return {
        "id": a.id, "name": a.name, "source": a.source, "market": a.market, "stage": a.stage, "state": a.state,
        "stale_days": a.stale_days, "heat": a.heat, "priority": a.priority, "csd_tier": a.csd_tier, "count": count,
    }


@router.get("/audiences")
def list_audiences(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    rows = mdb.scalars(select(MkAudience).order_by(MkAudience.id.desc())).all()
    out = []
    for r in rows:
        a = {"source": r.source, "market": r.market, "stage": r.stage, "state": r.state, "stale_days": r.stale_days, "heat": r.heat, "priority": r.priority, "csd_tier": r.csd_tier}
        out.append(_audience_out(r, _audience_count(main_db, sales_db, mdb, ctx, a)))
    return out


@router.get("/audiences/count")
def count_audience(
    source: str = Query("prospects"), market: Optional[str] = None, stage: Optional[str] = None, state: Optional[str] = None,
    stale_days: Optional[int] = None, heat: Optional[str] = None, priority: Optional[str] = None, csd_tier: Optional[str] = None,
    ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db),
):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    a = {"source": source, "market": market, "stage": stage, "state": state, "stale_days": stale_days, "heat": heat, "priority": priority, "csd_tier": csd_tier}
    return {"count": _audience_count(main_db, sales_db, mdb, ctx, a)}


@router.get("/audiences/members")
def audience_members(
    source: str = Query("prospects"), market: Optional[str] = None, stage: Optional[str] = None, state: Optional[str] = None,
    stale_days: Optional[int] = None, heat: Optional[str] = None, priority: Optional[str] = None, csd_tier: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db),
):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    if source == "customers" and not ctx.has("aud_all"):
        raise HTTPException(403, "Building audiences from existing customers needs the 'all CRM data' tick")
    a = {"source": source, "market": market, "stage": stage, "state": state, "stale_days": stale_days, "heat": heat, "priority": priority, "csd_tier": csd_tier}
    rows = _audience_rows(main_db, sales_db, ctx, a)
    stopped = _stopped_keys(mdb, "email")
    seen: set[str] = set()
    out = []
    for _id, name, phone, email in rows:
        key = normalize_contact(email) or normalize_contact(phone)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({
            "name": name, "phone": phone, "email": email,
            "stopped": normalize_contact(email) in stopped or normalize_contact(phone) in stopped,
        })
    return {"total": len(out), "truncated": len(out) > limit, "members": out[:limit]}


@router.post("/audiences")
def create_audience(body: AudienceIn, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    if body.source == "customers" and not ctx.has("aud_all"):
        raise HTTPException(403, "Building audiences from existing customers needs the 'all CRM data' tick")
    a = MkAudience(**body.model_dump(), created_by=ctx.user.id)
    mdb.add(a)
    commit(main_db, mdb)
    return _audience_out(a, _audience_count(main_db, sales_db, mdb, ctx, body.model_dump()))


@router.put("/audiences/{audience_id}")
def update_audience(audience_id: int, body: AudienceIn, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    a = mdb.get(MkAudience, audience_id)
    if a is None:
        raise HTTPException(404, "Audience not found")
    if body.source == "customers" and not ctx.has("aud_all"):
        raise HTTPException(403, "Building audiences from existing customers needs the 'all CRM data' tick")
    for key, value in body.model_dump().items():
        setattr(a, key, value)
    commit(main_db, mdb)
    return _audience_out(a, _audience_count(main_db, sales_db, mdb, ctx, body.model_dump()))


@router.delete("/audiences/{audience_id}")
def delete_audience(audience_id: int, ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    a = mdb.get(MkAudience, audience_id)
    if a is None:
        raise HTTPException(404, "Audience not found")
    mdb.delete(a)
    commit(main_db, mdb)
    return {"deleted": True}


# ---------------- campaigns ----------------
class CampaignIn(BaseModel):
    name: str
    audience_id: Optional[int] = None
    send_to_all: bool = False
    image_path: Optional[str] = None
    offer_name: str = ""
    offer_price: str = ""
    offer_mrp: str = ""
    offer_image_path: Optional[str] = None
    offer_link: str = ""
    collect_interest: bool = False
    interest_fields: list[dict] = []
    subject: str
    body: str


def _campaign_out(c: MkCampaign, audience_name: str | None) -> dict:
    return {
        "id": c.id, "name": c.name, "audience_id": c.audience_id, "audience_name": "Everyone" if c.send_to_all else audience_name,
        "send_to_all": c.send_to_all, "image_path": c.image_path,
        "offer_name": c.offer_name, "offer_price": c.offer_price, "offer_mrp": c.offer_mrp,
        "offer_image_path": c.offer_image_path, "offer_link": c.offer_link, "collect_interest": c.collect_interest,
        "interest_fields": json.loads(c.interest_fields or "[]"),
        "channel": c.channel, "subject": c.subject, "body": c.body, "status": c.status, "reject_reason": c.reject_reason,
        "total_count": c.total_count, "sent_count": c.sent_count, "skipped_count": c.skipped_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
        "next_batch_at": c.next_batch_at.isoformat() if c.next_batch_at else None,
    }


CAMPAIGN_IMAGE_GUIDE = {
    "recommended_size": "1200 x 600 px (roughly 2:1, a big hero banner for the top of the email)",
    "formats": ["JPG", "PNG"],
    "max_size_mb": 3,
    "note": "Keep important text inside the middle 80% -- some mail apps crop the edges.",
}


@router.get("/campaigns/image-guide")
def campaign_image_guide(_: Ctx = Depends(get_ctx)):
    return CAMPAIGN_IMAGE_GUIDE


@router.post("/campaigns/upload-image")
async def upload_campaign_image(file: UploadFile = File(...), ctx: Ctx = Depends(require("draft"))):
    from app.services.file_service import save_upload, to_public_upload_path

    path = await save_upload(file, module="marketing_campaigns", allowed_ext={".jpg", ".jpeg", ".png"}, allowed_mime={"image/jpeg", "image/png", "image/jpg"}, max_bytes=3 * 1024 * 1024)
    return {"image_path": to_public_upload_path(path)}


def _rows_for_campaign(main_db: Session, sales_db: Session | None, ctx: Ctx, c: MkCampaign, audience: MkAudience | None) -> list[tuple[int | None, str, str, str | None]]:
    if c.send_to_all:
        rows = _prospect_rows(sales_db, ctx, {})
        if ctx.has("aud_all"):
            rows = rows + _customer_rows(main_db, {})
        return rows
    a = {"source": audience.source, "market": audience.market, "stage": audience.stage, "state": audience.state, "stale_days": audience.stale_days, "heat": audience.heat, "priority": audience.priority}
    return _audience_rows(main_db, sales_db, ctx, a)


def _count_for_campaign(main_db: Session, sales_db: Session | None, mdb: Session, ctx: Ctx, c: MkCampaign, audience: MkAudience | None) -> int:
    if c.send_to_all:
        rows = _prospect_rows(sales_db, ctx, {})
        if ctx.has("aud_all"):
            rows = rows + _customer_rows(main_db, {})
        stopped = _stopped_keys(mdb, "email")
        seen: set[str] = set()
        for _id, _name, phone, email in rows:
            key = normalize_contact(email) or normalize_contact(phone)
            if not key or key in seen:
                continue
            if normalize_contact(email) in stopped or normalize_contact(phone) in stopped:
                continue
            seen.add(key)
        return len(seen)
    a = {"source": audience.source, "market": audience.market, "stage": audience.stage, "state": audience.state, "stale_days": audience.stale_days, "heat": audience.heat, "priority": audience.priority}
    return _audience_count(main_db, sales_db, mdb, ctx, a)


def _audience_names(mdb: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {a.id: a.name for a in mdb.scalars(select(MkAudience).where(MkAudience.id.in_(ids)))}


@router.get("/campaigns")
def list_campaigns(ctx: Ctx = Depends(require("draft", "submit", "approve")), mdb: Session = Depends(get_marketing_db)):
    rows = mdb.scalars(select(MkCampaign).order_by(MkCampaign.id.desc())).all()
    names = _audience_names(mdb, {r.audience_id for r in rows if r.audience_id})
    return [_campaign_out(r, names.get(r.audience_id)) for r in rows]


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, ctx: Ctx = Depends(require("draft", "submit", "approve")), mdb: Session = Depends(get_marketing_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    names = _audience_names(mdb, {c.audience_id} if c.audience_id else set())
    out = _campaign_out(c, names.get(c.audience_id))
    logs = mdb.scalars(select(MkCampaignLog).where(MkCampaignLog.campaign_id == c.id).order_by(MkCampaignLog.id.desc()).limit(500)).all()
    out["logs"] = [
        {"contact": l.contact_name, "address": l.contact_address, "result": l.result, "at": l.at.isoformat() if l.at else None}
        for l in logs
    ]
    return out


def _validate_campaign_target(body: CampaignIn, ctx: Ctx, mdb: Session) -> MkAudience | None:
    if body.send_to_all:
        if not ctx.has("aud_all"):
            raise HTTPException(403, "Sending to everyone needs the 'all CRM data' tick")
        return None
    if not body.audience_id:
        raise HTTPException(400, "Pick an audience, or switch to Everyone")
    audience = mdb.get(MkAudience, body.audience_id)
    if audience is None:
        raise HTTPException(404, "Audience not found")
    return audience


def _check_collect_interest(body: CampaignIn, audience: MkAudience | None) -> None:
    if body.collect_interest and (body.send_to_all or audience is None or audience.source != "prospects"):
        raise HTTPException(400, "Collecting interest needs a Prospects (Sales leads) audience -- there's no existing lead to write onto otherwise")


FIELD_TYPES = {"text", "select", "yesno"}


def _clean_interest_fields(raw: list[dict]) -> str:
    cleaned = []
    for i, f in enumerate(raw or []):
        label = str(f.get("label") or "").strip()
        if not label:
            continue
        ftype = f.get("type") if f.get("type") in FIELD_TYPES else "text"
        field = {"key": str(f.get("key") or f"field_{i}"), "label": label[:120], "type": ftype}
        if ftype == "select":
            options = [str(o).strip()[:80] for o in (f.get("options") or []) if str(o).strip()]
            field["options"] = options[:20]
        cleaned.append(field)
    return json.dumps(cleaned[:10])


@router.post("/campaigns")
def create_campaign(body: CampaignIn, ctx: Ctx = Depends(require("draft")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    audience = _validate_campaign_target(body, ctx, mdb)
    _check_collect_interest(body, audience)
    c = MkCampaign(
        name=body.name, audience_id=audience.id if audience else None, send_to_all=body.send_to_all, image_path=body.image_path,
        offer_name=body.offer_name, offer_price=body.offer_price, offer_mrp=body.offer_mrp,
        offer_image_path=body.offer_image_path, offer_link=body.offer_link, collect_interest=body.collect_interest,
        interest_fields=_clean_interest_fields(body.interest_fields),
        subject=body.subject, body=body.body, status="draft", created_by=ctx.user.id,
    )
    mdb.add(c)
    commit(main_db, mdb)
    return _campaign_out(c, audience.name if audience else None)


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, body: CampaignIn, ctx: Ctx = Depends(require("draft")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status != "draft":
        raise HTTPException(409, "Only a draft campaign can be edited")
    audience = _validate_campaign_target(body, ctx, mdb)
    _check_collect_interest(body, audience)
    c.name, c.audience_id, c.send_to_all, c.image_path, c.subject, c.body = (
        body.name, audience.id if audience else None, body.send_to_all, body.image_path, body.subject, body.body,
    )
    c.offer_name, c.offer_price, c.offer_mrp, c.offer_image_path, c.offer_link, c.collect_interest = (
        body.offer_name, body.offer_price, body.offer_mrp, body.offer_image_path, body.offer_link, body.collect_interest,
    )
    c.interest_fields = _clean_interest_fields(body.interest_fields)
    commit(main_db, mdb)
    return _campaign_out(c, audience.name if audience else None)


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int, ctx: Ctx = Depends(require("draft")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status not in ("draft", "rejected"):
        raise HTTPException(409, "A campaign that is waiting, approved or already sent cannot be deleted")
    mdb.delete(c)
    commit(main_db, mdb)
    return {"deleted": True}


def _campaign_asset_url(path: str) -> str:
    from app.config import settings

    base = (settings.app_public_url or "").rstrip("/")
    return f"{base}{path}" if base else path


def _build_interest_link(mdb: Session, c: MkCampaign, lead_id: int) -> str:
    import secrets

    token = secrets.token_urlsafe(24)
    mdb.add(MkLeadInterestToken(token=token, campaign_id=c.id, lead_id=lead_id))
    from app.config import settings

    return f"{(settings.app_public_url or '').rstrip('/')}/interest/{token}"


def _campaign_offer_html(c: MkCampaign, cta_link: str = "", cta_text: str = "Shop Now") -> str:
    if not (c.offer_name or "").strip():
        return ""
    img = (
        f"<img src='{_campaign_asset_url(c.offer_image_path)}' width='110' "
        f"style='display:block; width:110px; height:110px; object-fit:cover; border-radius:8px; border:1px solid #e8e2f4;' />"
        if c.offer_image_path else ""
    )
    price_html = f"<span style='font-size:17px; font-weight:800; color:#1c2230;'>{c.offer_price}</span>" if c.offer_price else ""
    mrp_html = f"<span style='font-size:13px; color:#9aa; text-decoration:line-through; margin-left:8px;'>{c.offer_mrp}</span>" if c.offer_mrp else ""
    link = cta_link or c.offer_link
    btn_html = (
        f"<a href='{link}' style='display:inline-block; margin-top:10px; background:#1e3a78; color:#fff; "
        f"font-size:13px; font-weight:700; padding:7px 16px; border-radius:7px; text-decoration:none;'>{cta_text} &rarr;</a>"
        if link else ""
    )
    img_cell = f"<td style='width:110px; padding-right:14px; vertical-align:top;'>{img}</td>" if img else ""
    return (
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
        "style='margin:16px 0; border:1px solid #e8e2f4; border-radius:10px; background:#fafafe;'>"
        f"<tr><td style='padding:14px;'><table role='presentation' cellpadding='0' cellspacing='0'><tr>{img_cell}"
        f"<td style='vertical-align:top;'>"
        "<span style='font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:.04em; color:#b8860b; "
        "background:#faf1dc; border-radius:999px; padding:2px 8px;'>Today's offer</span>"
        f"<div style='font-size:14.5px; font-weight:700; color:#1c2230; margin-top:6px; line-height:1.3;'>{c.offer_name}</div>"
        f"<div style='margin-top:6px;'>{price_html}{mrp_html}</div>{btn_html}"
        "</td></tr></table></td></tr></table>"
    )


def _campaign_email_html(c: MkCampaign, name: str, lead_id: int | None, mdb: Session) -> str:
    body_html = (c.body or "").replace("{{name}}", name or "there").replace("\n", "<br/>")
    interest_link = _build_interest_link(mdb, c, lead_id) if (c.collect_interest and lead_id) else ""
    offer_html = _campaign_offer_html(c, cta_link=interest_link, cta_text="Yes, I'm interested" if interest_link else "Shop Now")
    banner_html = ""
    if c.image_path:
        src = _campaign_asset_url(c.image_path)
        banner_html = f"<img src='{src}' alt='{c.subject}' width='600' style='display:block; width:100%; max-width:600px; height:auto; border:0;' />"
    return (
        "<div style='font-family:Arial,sans-serif;'>"
        f"{banner_html}{offer_html}"
        f"<div style='padding:16px 4px; font-size:14px; color:#1c2230;'>{body_html}</div>"
        "</div>"
    )


CAMPAIGN_BATCH_SIZE = 25
CAMPAIGN_BATCH_GAP_MINUTES = 20


def _send_campaign_batch(mdb: Session, main_db: Session, sales_db: Session, ctx: Ctx, c: MkCampaign) -> None:
    """Send up to CAMPAIGN_BATCH_SIZE not-yet-logged contacts, then either finish or schedule the next batch.
    Safe to call repeatedly for the same campaign (by the cron runner) -- already-logged contacts are skipped."""
    from app.services.email_service import send_email

    audience = mdb.get(MkAudience, c.audience_id) if c.audience_id else None
    rows = _rows_for_campaign(main_db, sales_db, ctx, c, audience)
    stopped = _stopped_keys(mdb, "email")
    pause_days = int(get_setting(mdb, "pause_days") or 4)
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(days=pause_days)
    already_logged = set(
        mdb.scalars(select(MkCampaignLog.contact_key).where(MkCampaignLog.campaign_id == c.id))
    )

    seen: set[str] = set()
    unique_rows: list[tuple[str, int | None, str, str, str | None]] = []
    for lead_id, name, phone, email in rows:
        key = normalize_contact(email) or normalize_contact(phone)
        if not key or key in seen:
            continue
        seen.add(key)
        unique_rows.append((key, lead_id, name, phone, email))
    unique_rows.sort(key=lambda r: r[0])
    pending = [row for row in unique_rows if row[0] not in already_logged]
    batch = pending[:CAMPAIGN_BATCH_SIZE]

    sent = skipped = 0
    for key, lead_id, name, phone, email in batch:
        if not email:
            mdb.add(MkCampaignLog(campaign_id=c.id, contact_key=key, contact_name=name or "", contact_address="", result="no_email"))
            skipped += 1
            continue
        if normalize_contact(email) in stopped or normalize_contact(phone) in stopped:
            mdb.add(MkCampaignLog(campaign_id=c.id, contact_key=key, contact_name=name or "", contact_address=email, result="stopped"))
            skipped += 1
            continue
        touch = mdb.get(MkContactTouch, key)
        if touch is not None and touch.last_sent_at and touch.last_sent_at.replace(tzinfo=timezone.utc) > cooldown_cutoff:
            mdb.add(MkCampaignLog(campaign_id=c.id, contact_key=key, contact_name=name or "", contact_address=email, result="cooldown"))
            skipped += 1
            continue
        ok = send_email(email, c.subject, _campaign_email_html(c, name, lead_id, mdb), template="marketing_campaign")
        mdb.add(MkCampaignLog(campaign_id=c.id, contact_key=key, contact_name=name or "", contact_address=email, result="sent" if ok else "failed"))
        if ok:
            sent += 1
            if touch is None:
                mdb.add(MkContactTouch(contact_key=key, last_campaign_id=c.id, last_sent_at=datetime.now(timezone.utc)))
            else:
                touch.last_campaign_id = c.id
                touch.last_sent_at = datetime.now(timezone.utc)
        else:
            skipped += 1

    c.total_count = len(unique_rows)
    c.sent_count = (c.sent_count or 0) + sent
    c.skipped_count = (c.skipped_count or 0) + skipped
    remaining = len(pending) - len(batch)
    if remaining > 0:
        c.status = "sending"
        c.next_batch_at = datetime.now(timezone.utc) + timedelta(minutes=CAMPAIGN_BATCH_GAP_MINUTES)
    else:
        c.status = "sent"
        c.sent_at = datetime.now(timezone.utc)
        c.next_batch_at = None


@router.post("/campaigns/{campaign_id}/submit")
def submit_campaign(campaign_id: int, ctx: Ctx = Depends(require("submit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status not in ("draft", "rejected"):
        raise HTTPException(409, "Only a draft or rejected campaign can be submitted")
    if not (c.subject or "").strip() or not (c.body or "").strip():
        raise HTTPException(400, "Write a subject and a message before sending")
    audience = mdb.get(MkAudience, c.audience_id) if c.audience_id else None
    count = _count_for_campaign(main_db, sales_db, mdb, ctx, c, audience)
    limit = int(get_setting(mdb, "approval_min_audience") or 1000)
    if count <= limit and ctx.has("release_small"):
        c.approved_by = ctx.user.id
        c.approved_at = datetime.now(timezone.utc)
        _send_campaign_batch(mdb, main_db, sales_db, ctx, c)
        commit(main_db, mdb)
        return _campaign_out(c, audience.name if audience else None)
    c.status = "wait"
    commit(main_db, mdb)
    return _campaign_out(c, audience.name if audience else None)


@router.post("/campaigns/{campaign_id}/approve")
def approve_campaign(campaign_id: int, ctx: Ctx = Depends(require("approve")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status != "wait":
        raise HTTPException(409, "Only a campaign waiting for approval can be approved")
    c.approved_by = ctx.user.id
    c.approved_at = datetime.now(timezone.utc)
    _send_campaign_batch(mdb, main_db, sales_db, ctx, c)
    commit(main_db, mdb)
    audience = mdb.get(MkAudience, c.audience_id) if c.audience_id else None
    return _campaign_out(c, audience.name if audience else None)


class RejectIn(BaseModel):
    reason: str = ""


@router.post("/campaigns/{campaign_id}/reject")
def reject_campaign(campaign_id: int, body: RejectIn, ctx: Ctx = Depends(require("approve")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    c = mdb.get(MkCampaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status != "wait":
        raise HTTPException(409, "Only a campaign waiting for approval can be rejected")
    c.status = "rejected"
    c.reject_reason = body.reason.strip()
    commit(main_db, mdb)
    audience = mdb.get(MkAudience, c.audience_id)
    return _campaign_out(c, audience.name if audience else None)
