"""Keys and passwords of the Sales connections (IndiaMART key, Meta token, a mailbox password ...) are stored
encrypted in the Sales database and never sent back to a browser."""

from __future__ import annotations

import base64
import hashlib
import json

from app.config import settings


def _fernet():
    from cryptography.fernet import Fernet

    seed = (settings.sales_secret_key or settings.jwt_secret or "change-me").encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"indcool-sales|" + seed).digest()))


def seal(values: dict | None) -> str | None:
    if not values:
        return None
    return _fernet().encrypt(json.dumps(values, ensure_ascii=False).encode("utf-8")).decode("ascii")


def unseal(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(_fernet().decrypt(text.encode("ascii")).decode("utf-8"))
    except Exception:
        # the key that sealed it is not the key now in use
        return {}
