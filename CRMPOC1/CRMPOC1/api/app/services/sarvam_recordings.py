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
INTERACTION_ID_RE = re.compile(r"^\d{8}/[A-Za-z0-9_:\-]{6,100}$")  # real ids look like 20261023/bf9c14fd-10:08:55-5023b492
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
    url = f"{BASE_URL}/{quote(s['org'], safe='')}/{quote(s['workspace'], safe='')}/{quote(s['app'], safe='')}/recordings/{quote(interaction_id, safe='/:')}"
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


def keep_audio_in_crm() -> bool:
    """Recordings live in Google Drive. Keeping a copy of the audio in the CRM database is off unless asked for."""
    return os.environ.get("SARVAM_KEEP_AUDIO_IN_CRM", "").strip().lower() in ("1", "true", "yes")


def drive_file_id(url: str | None) -> str | None:
    m = re.search(r"/file/d/([A-Za-z0-9_-]{10,})", url or "") or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url or "")
    return m.group(1) if m else None


def store_recording(db: Session, call: Call) -> CallRecording | None:
    """Download and keep the audio for this call if it isn't kept yet. Commits nothing; the caller does."""
    existing = db.query(CallRecording).filter(CallRecording.call_id == call.id).first()
    if existing is not None:
        return existing
    if not call.sarvam_interaction_id or not keep_audio_in_crm():
        return None
    got = download_recording(call.sarvam_interaction_id)
    if got is None:
        return None
    audio, content_type = got
    row = CallRecording(call_id=call.id, content_type=content_type, size_bytes=len(audio), audio=audio)
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------- matching a Sarvam interaction to a CRM call

def _utc(value: str | None):
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def mobile10(raw: str | None) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        return None
    m = digits[-10:]
    return m if re.fullmatch(r"[6-9]\d{9}", m) else None


def match_call(db: Session, mobile: str | None, start, end, taken: set[int] | None = None, allow_time_only: bool = True) -> Call | None:
    """The still-unlinked Sarvam call-log row for a Sarvam interaction.

    The CRM row is made while the call is on (when the agent registers the complaint), so its time falls
    between the call's start and end. Same phone number first; the caller may have given the agent a
    different number than the one they rang from, so failing that, accept a time match only when it is the
    one and only unlinked Sarvam call in that window."""
    from datetime import timedelta, timezone

    if start is None:
        return None
    end = end or start + timedelta(minutes=30)
    rows = db.query(Call).filter(
        Call.sarvam_interaction_id.is_(None),
        Call.notes.like("Sarvam voice agent call%"),
        Call.call_datetime >= start - timedelta(minutes=2),
        Call.call_datetime <= end + timedelta(minutes=10),
    ).all()
    rows = [c for c in rows if not taken or c.id not in taken]

    def gap(c: Call) -> float:
        at = c.call_datetime if c.call_datetime.tzinfo else c.call_datetime.replace(tzinfo=timezone.utc)
        return abs((at - start).total_seconds())

    same_phone = [c for c in rows if mobile and c.phone == mobile]
    if same_phone:
        return min(same_phone, key=gap)
    return rows[0] if (allow_time_only and len(rows) == 1) else None


def link_interactions(db: Session, items: list[dict], dry_run: bool = False, allow_time_only: bool = True) -> dict:
    """Tie Sarvam call-history items to CRM call-log rows. Returns counts and the matched pairs (call ref and
    interaction id only, never a phone number). Commits nothing."""
    stats = {"interactions": 0, "already_linked": 0, "matched": 0, "no_crm_call": 0, "pairs": [], "time_only": []}
    taken: set[int] = set()
    for item in sorted(items, key=lambda i: i.get("start_datetime") or ""):
        iid = item.get("interaction_id")
        if not valid_interaction_id(iid):
            continue
        stats["interactions"] += 1
        if db.query(Call.id).filter(Call.sarvam_interaction_id == iid).first() is not None:
            stats["already_linked"] += 1
            continue
        mobile = mobile10(item.get("user_contact"))
        call = match_call(db, mobile, _utc(item.get("start_datetime")), _utc(item.get("end_datetime")), taken, allow_time_only)
        if call is not None and call.phone != mobile:
            stats["time_only"].append((call.ref_no, iid))  # a different number than the caller rang from: worth a look
        if call is None:
            stats["no_crm_call"] += 1
            continue
        taken.add(call.id)
        stats["matched"] += 1
        stats["pairs"].append((call.ref_no, iid))
        if not dry_run:
            call.sarvam_interaction_id = iid
            duration = int(float(item.get("duration_in_seconds") or 0))
            if duration and not call.duration_secs:
                call.duration_secs = duration
    return stats


def list_interactions(days: int) -> list[dict]:
    """Sarvam's call history for the last N days (every page). Raises on a rejected key or ids."""
    from datetime import datetime, timedelta, timezone

    if not recordings_configured():
        raise RuntimeError("The Sarvam settings are not in this server's .env")
    s = _settings()
    url = f"{BASE_URL}/{quote(s['org'], safe='')}/{quote(s['workspace'], safe='')}/{quote(s['app'], safe='')}/interactions"
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    params = {
        "start_datetime": (now - timedelta(days=days)).isoformat(),
        "end_datetime": now.isoformat(),
        "limit": 1000,
        "offset": 0,
        "sort_by": "start_datetime",
        "sort_order": "asc",
    }
    items: list[dict] = []
    while True:
        r = requests.get(url, headers={"X-API-Key": s["key"]}, params=params, timeout=TIMEOUT, allow_redirects=False)
        if r.status_code != 200:
            raise RuntimeError(f"Sarvam answered HTTP {r.status_code} for the call history")
        body = r.json()
        page = body.get("items") or []
        items.extend(page)
        params["offset"] += len(page)
        if not page or params["offset"] >= int(body.get("total") or 0):
            return items
