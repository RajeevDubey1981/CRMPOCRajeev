"""Fetch a Sarvam voice-agent call's audio by its interaction id and keep it with the CRM call log.

Sarvam's post-call webhook carries no recording link; the audio is downloaded from its analytics API:
GET https://apps.sarvam.ai/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/recordings/{interaction_id}
with the workspace API key in X-API-Key. Needs these in the server .env (set by the owner, never in chat):
SARVAM_ORG_ID, SARVAM_WORKSPACE_ID, SARVAM_APP_ID, SARVAM_WORKSPACE_API_KEY."""
from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

from app.models.call import Call, CallRecording

logger = logging.getLogger(__name__)

BASE_URL = "https://apps.sarvam.ai/api/analytics/v1"
INTERACTION_ID_RE = re.compile(r"^\d{8}/[A-Za-z0-9_-]{6,80}$")
MAX_AUDIO_BYTES = 100 * 1024 * 1024
TIMEOUT = (10, 60)


def valid_interaction_id(value: str | None) -> bool:
    return bool(value) and INTERACTION_ID_RE.fullmatch(value) is not None


def _settings() -> dict[str, str]:
    return {
        "org": os.environ.get("SARVAM_ORG_ID", "").strip(),
        "workspace": os.environ.get("SARVAM_WORKSPACE_ID", "").strip(),
        "app": os.environ.get("SARVAM_APP_ID", "").strip(),
        "key": os.environ.get("SARVAM_WORKSPACE_API_KEY", "").strip(),
    }


def recordings_configured() -> bool:
    return all(_settings().values())


def download_recording(interaction_id: str) -> tuple[bytes, str] | None:
    """The audio bytes and content type, or None when Sarvam has no recording (404) or it can't be reached."""
    if not valid_interaction_id(interaction_id) or not recordings_configured():
        return None
    s = _settings()
    url = f"{BASE_URL}/{quote(s['org'], safe='')}/{quote(s['workspace'], safe='')}/{quote(s['app'], safe='')}/recordings/{quote(interaction_id, safe='/')}"
    try:
        with requests.get(url, headers={"X-API-Key": s["key"]}, timeout=TIMEOUT, stream=True, allow_redirects=False) as r:
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                logger.warning("Sarvam recording download answered HTTP %s for %s", r.status_code, interaction_id)
                return None
            chunks, total = [], 0
            for chunk in r.iter_content(64 * 1024):
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    logger.warning("Sarvam recording for %s is larger than the %s byte cap", interaction_id, MAX_AUDIO_BYTES)
                    return None
                chunks.append(chunk)
            content_type = (r.headers.get("Content-Type") or "audio/wav").split(";")[0].strip()
            return b"".join(chunks), content_type if content_type.startswith("audio/") else "audio/wav"
    except requests.RequestException:
        logger.exception("could not download the Sarvam recording for %s", interaction_id)
        return None


def store_recording(db: Session, call: Call) -> CallRecording | None:
    """Download and keep the audio for this call if it isn't kept yet. Commits nothing; the caller does."""
    existing = db.query(CallRecording).filter(CallRecording.call_id == call.id).first()
    if existing is not None:
        return existing
    if not call.sarvam_interaction_id:
        return None
    got = download_recording(call.sarvam_interaction_id)
    if got is None:
        return None
    audio, content_type = got
    row = CallRecording(call_id=call.id, content_type=content_type, size_bytes=len(audio), audio=audio)
    db.add(row)
    db.flush()
    return row
