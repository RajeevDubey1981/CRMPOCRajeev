"""Marketing, release 1: who may use it. Audiences, campaigns and channels come in the next releases."""

from __future__ import annotations

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
from app.marketing.models import MkAudience, MkBanner, MkChannel, MkChannelAsset, MkConsent, MkRoleTick, MkSetting, MkTickHistory, MkUserTick
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
    is_enabled: bool = True


def _banner_out(b: MkBanner) -> dict:
    today = datetime.now(timezone.utc).date()
    return {
        "id": b.id, "name": b.name, "theme": b.theme, "greeting": b.greeting, "headline": b.headline,
        "pill1": b.pill1, "pill2": b.pill2, "cta_text": b.cta_text, "cta_link": b.cta_link, "image_path": b.image_path,
        "start_date": b.start_date.isoformat(), "end_date": b.end_date.isoformat(),
        "target_type": b.target_type, "is_enabled": b.is_enabled,
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
    return [_banner_out(b) for b in rows]


@router.post("/banners")
def create_banner(body: BannerIn, ctx: Ctx = Depends(require("banner_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date cannot be before the start date")
    b = MkBanner(**body.model_dump(), created_by=ctx.user.id)
    mdb.add(b)
    commit(main_db, mdb)
    return _banner_out(b)


@router.put("/banners/{banner_id}")
def update_banner(banner_id: int, body: BannerIn, ctx: Ctx = Depends(require("banner_edit")), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db)):
    b = mdb.get(MkBanner, banner_id)
    if b is None:
        raise HTTPException(404, "Banner not found")
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date cannot be before the start date")
    for key, value in body.model_dump().items():
        setattr(b, key, value)
    commit(main_db, mdb)
    return _banner_out(b)


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


def _count_prospects(sales_db: Session | None, mdb: Session, ctx: Ctx, a: dict) -> int:
    if sales_db is None or not sales_enabled():
        return 0
    q = sales_db.query(SalesLead.phone, SalesLead.email)
    if a.get("market"):
        q = q.filter(SalesLead.lead_type == a["market"])
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


def _audience_count(main_db: Session, sales_db: Session | None, mdb: Session, ctx: Ctx, a: dict) -> int:
    if a.get("source") == "customers":
        if not ctx.has("aud_all"):
            return 0  # only an "all CRM data" tick may build audiences from existing customers
        return _count_customers(main_db, mdb, a)
    return _count_prospects(sales_db, mdb, ctx, a)


def _audience_out(a: MkAudience, count: int) -> dict:
    return {
        "id": a.id, "name": a.name, "source": a.source, "market": a.market, "stage": a.stage, "state": a.state,
        "stale_days": a.stale_days, "heat": a.heat, "priority": a.priority, "count": count,
    }


@router.get("/audiences")
def list_audiences(ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db)):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    rows = mdb.scalars(select(MkAudience).order_by(MkAudience.id.desc())).all()
    out = []
    for r in rows:
        a = {"source": r.source, "market": r.market, "stage": r.stage, "state": r.state, "stale_days": r.stale_days, "heat": r.heat, "priority": r.priority}
        out.append(_audience_out(r, _audience_count(main_db, sales_db, mdb, ctx, a)))
    return out


@router.get("/audiences/count")
def count_audience(
    source: str = Query("prospects"), market: Optional[str] = None, stage: Optional[str] = None, state: Optional[str] = None,
    stale_days: Optional[int] = None, heat: Optional[str] = None, priority: Optional[str] = None,
    ctx: Ctx = Depends(get_ctx), mdb: Session = Depends(get_marketing_db), main_db: Session = Depends(get_db), sales_db: Session = Depends(get_sales_db),
):
    if not ctx.any("aud_own", "aud_all"):
        raise HTTPException(403, "You do not have this tick in Marketing")
    a = {"source": source, "market": market, "stage": stage, "state": state, "stale_days": stale_days, "heat": heat, "priority": priority}
    return {"count": _audience_count(main_db, sales_db, mdb, ctx, a)}


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
