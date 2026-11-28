"""Sarvam chat completions, used by the WhatsApp automatic replies.

Endpoint, headers, model names and JSON mode are from docs.sarvam.ai (POST /v1/chat/completions).
The key lives only in the server settings and is never logged.
"""
from __future__ import annotations

import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class SarvamChatError(Exception):
    pass


def chat_configured() -> bool:
    return bool((settings.sarvam_chat_api_key or "").strip() and (settings.sarvam_chat_model or "").strip())


def chat_json(messages: list[dict], *, max_tokens: int = 500, timeout: int = 25) -> tuple[dict, int]:
    """Ask the model for one JSON object. Returns (parsed object, tokens used). Raises SarvamChatError on any problem."""
    if not chat_configured():
        raise SarvamChatError("Sarvam chat is not configured")
    key = settings.sarvam_chat_api_key.strip()
    try:
        r = requests.post(
            settings.sarvam_chat_url,
            headers={"Authorization": f"Bearer {key}", "api-subscription-key": key, "Content-Type": "application/json"},
            json={
                "model": settings.sarvam_chat_model.strip(),
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SarvamChatError(f"Could not reach Sarvam: {type(exc).__name__}") from exc
    if not r.ok:
        try:
            msg = (r.json().get("error") or {}).get("message") or ""
        except ValueError:
            msg = ""
        raise SarvamChatError(f"Sarvam returned {r.status_code}: {msg[:200]}")
    try:
        data = r.json()
        content = data["choices"][0]["message"]["content"] or ""
        tokens = int((data.get("usage") or {}).get("total_tokens") or 0)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise SarvamChatError("Sarvam sent an unexpected reply") from exc
    text = content.strip()
    if text.startswith("```"):  # some models wrap JSON in a code fence
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise SarvamChatError("The model did not return valid JSON") from exc
    if not isinstance(obj, dict):
        raise SarvamChatError("The model did not return a JSON object")
    return obj, tokens
