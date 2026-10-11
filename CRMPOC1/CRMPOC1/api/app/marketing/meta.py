"""Meta (Facebook and Instagram) through the Graph API. Read-only for ads in this release: log in with Facebook, list the
ad accounts, list campaigns and read their results. Nothing here creates, changes or spends anything.

The token is sent in the Authorization header (never in a URL), and every call carries appsecret_proof, which Meta
recommends so a stolen token alone is not enough."""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlencode

import requests

from app.config import settings

SCOPES_READ = ("ads_read", "business_management")
TIMEOUT = 25


class MetaError(Exception):
    """A problem with Meta, in words that are safe to show (never a token)."""


def configured() -> bool:
    return bool((settings.meta_app_id or "").strip() and (settings.meta_app_secret or "").strip())


def _base() -> str:
    return f"https://graph.facebook.com/{settings.meta_graph_version}"


def _proof(token: str) -> str:
    return hmac.new(settings.meta_app_secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def login_url(state: str, scopes=SCOPES_READ) -> str:
    if not configured():
        raise MetaError("Meta is not set up yet: the App ID and App Secret are missing on the server")
    query = urlencode({"client_id": settings.meta_app_id, "redirect_uri": settings.meta_redirect_uri, "state": state, "scope": ",".join(scopes), "response_type": "code"})
    return f"https://www.facebook.com/{settings.meta_graph_version}/dialog/oauth?{query}"


def _check(resp: requests.Response):
    try:
        data = resp.json()
    except ValueError:
        raise MetaError(f"Meta answered with something unreadable (status {resp.status_code})")
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        msg = str(err.get("message") or f"status {resp.status_code}")
        raise MetaError(f"Meta said: {msg[:200]}")
    return data


def exchange_code(code: str) -> dict:
    """The code Meta gave after login becomes a short token, then a long one (about 60 days)."""
    short = _check(requests.get(f"{_base()}/oauth/access_token", params={"client_id": settings.meta_app_id, "client_secret": settings.meta_app_secret, "redirect_uri": settings.meta_redirect_uri, "code": code}, timeout=TIMEOUT))
    long_ = _check(requests.get(f"{_base()}/oauth/access_token", params={"grant_type": "fb_exchange_token", "client_id": settings.meta_app_id, "client_secret": settings.meta_app_secret, "fb_exchange_token": short["access_token"]}, timeout=TIMEOUT))
    return {"access_token": long_["access_token"], "expires_in": int(long_.get("expires_in") or 0)}


def get(path: str, token: str, params: dict | None = None):
    q = dict(params or {})
    q["appsecret_proof"] = _proof(token)
    return _check(requests.get(f"{_base()}/{path.lstrip('/')}", params=q, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT))


def me(token: str) -> dict:
    return get("me", token, {"fields": "id,name"})


ACCOUNT_FIELDS = "account_id,name,currency,account_status,amount_spent,business{name}"


def businesses(token: str) -> list[dict]:
    return get("me/businesses", token, {"fields": "id,name", "limit": 50}).get("data", [])


def ad_accounts(token: str) -> list[dict]:
    """Every ad account this login can see: the ones given to the person directly, and the ones of the businesses the
    person belongs to (owned by the business, or shared with it by another business)."""
    found: dict[str, dict] = {}
    for a in get("me/adaccounts", token, {"fields": ACCOUNT_FIELDS, "limit": 50}).get("data", []):
        found[str(a.get("account_id"))] = a
    try:  # a System User sees its ad accounts here, not in me/adaccounts
        for a in get("me/assigned_ad_accounts", token, {"fields": ACCOUNT_FIELDS, "limit": 50}).get("data", []):
            found.setdefault(str(a.get("account_id")), a)
    except MetaError:
        pass
    try:
        for biz in businesses(token):
            for edge in ("owned_ad_accounts", "client_ad_accounts"):
                try:
                    for a in get(f"{biz['id']}/{edge}", token, {"fields": ACCOUNT_FIELDS, "limit": 50}).get("data", []):
                        found.setdefault(str(a.get("account_id")), a)
                except MetaError:
                    continue
    except MetaError:
        pass  # the business view needs business_management; the personal list above still works
    return list(found.values())


def diagnose(token: str) -> dict:
    """What Meta actually gave this login: permissions, the ad accounts chosen in Facebook's window, the businesses, and
    how many ad accounts each way of asking returns. No token is returned."""
    out: dict = {"permissions": [], "granular": [], "businesses": [], "direct_accounts": None}
    try:
        out["permissions"] = [{"name": p.get("permission"), "status": p.get("status")} for p in get("me/permissions", token).get("data", [])]
    except MetaError as exc:
        out["permissions_error"] = str(exc)
    try:
        info = _check(requests.get(f"{_base()}/debug_token", params={"input_token": token}, headers={"Authorization": f"Bearer {settings.meta_app_id}|{settings.meta_app_secret}"}, timeout=TIMEOUT)).get("data", {})
        out["granular"] = [{"scope": g.get("scope"), "target_ids": g.get("target_ids", [])} for g in info.get("granular_scopes", [])]
        out["app_id"] = info.get("app_id")
        out["is_valid"] = info.get("is_valid")
    except MetaError as exc:
        out["granular_error"] = str(exc)
    try:
        out["direct_accounts"] = len(get("me/adaccounts", token, {"fields": "account_id", "limit": 50}).get("data", []))
    except MetaError as exc:
        out["direct_error"] = str(exc)
    try:
        out["assigned_accounts"] = len(get("me/assigned_ad_accounts", token, {"fields": "account_id", "limit": 50}).get("data", []))
    except MetaError as exc:
        out["assigned_accounts"] = f"not allowed ({str(exc)[:80]})"
    try:
        for biz in businesses(token):
            row = {"id": biz.get("id"), "name": biz.get("name")}
            for edge in ("owned_ad_accounts", "client_ad_accounts"):
                try:
                    row[edge] = len(get(f"{biz['id']}/{edge}", token, {"fields": "account_id", "limit": 50}).get("data", []))
                except MetaError as exc:
                    row[edge] = f"not allowed ({str(exc)[:80]})"
            out["businesses"].append(row)
    except MetaError as exc:
        out["businesses_error"] = str(exc)
    return out


def campaigns(token: str, account_id: str) -> list[dict]:
    acc = account_id if account_id.startswith("act_") else f"act_{account_id}"
    rows = get(f"{acc}/campaigns", token, {"fields": "id,name,status,effective_status,objective,daily_budget,lifetime_budget", "limit": 100}).get("data", [])
    stats = {r.get("campaign_id"): r for r in get(f"{acc}/insights", token, {"level": "campaign", "fields": "campaign_id,spend,impressions,reach,clicks,actions", "date_preset": "last_30d", "limit": 200}).get("data", [])}
    for c in rows:
        s = stats.get(c["id"], {})
        results = sum(float(a.get("value", 0)) for a in s.get("actions", []) if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead", "onsite_conversion.messaging_conversation_started_7d"))
        c["last_30_days"] = {"spend": s.get("spend", "0"), "impressions": s.get("impressions", "0"), "reach": s.get("reach", "0"), "clicks": s.get("clicks", "0"), "leads": int(results)}
    return rows
