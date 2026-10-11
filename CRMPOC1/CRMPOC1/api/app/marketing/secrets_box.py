"""The tokens of connected platforms (Meta ...) are stored encrypted in the Marketing database and never sent to a browser."""

from __future__ import annotations

import base64
import hashlib
import json

from app.config import settings


def _fernet():
    from cryptography.fernet import Fernet

    seed = (settings.marketing_secret_key or settings.jwt_secret or "change-me").encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"indcool-marketing|" + seed).digest()))


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
        return {}  # the key that sealed it is not the key now in use
