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


def ad_accounts(token: str) -> list[dict]:
    out, page = [], get("me/adaccounts", token, {"fields": "account_id,name,currency,account_status,amount_spent,business{name}", "limit": 50})
    out += page.get("data", [])
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
