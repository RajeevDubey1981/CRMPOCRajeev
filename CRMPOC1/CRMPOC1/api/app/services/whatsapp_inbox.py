"""WhatsApp inbox: check and store what Meta sends, and send staff replies.

Phase 1: receive, log, and let staff reply by hand. No automatic replies happen here.
Rules kept here: signatures are checked on the raw body, every webhook call is saved before it is processed,
a message id is stored once (Meta retries), and free text is only sent inside the 24-hour window.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.whatsapp import WaConversation, WaMessage, WaWebhookEvent
from app.services.whatsapp_service import _normalize_indian_mobile

logger = logging.getLogger(__name__)

WINDOW = timedelta(hours=24)
STOP_WORDS = {"stop", "unsubscribe", "opt out", "optout"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def signature_ok(raw: bytes, header: str | None) -> bool:
    """Meta signs the exact request body with the app secret: X-Hub-Signature-256: sha256=<hex>."""
    # The WhatsApp number may belong to a different Meta app than the marketing one, so accept either secret.
    secrets = [x.strip() for x in (settings.wa_app_secret, settings.meta_app_secret) if (x or "").strip()]
    if not secrets or not header or not header.startswith("sha256="):
        return False
    given = header[7:].strip()
    return any(hmac.compare_digest(hmac.new(sec.encode("utf-8"), raw, hashlib.sha256).hexdigest(), given) for sec in secrets)


def verify_token_ok(token: str | None) -> bool:
    expected = (settings.wa_verify_token or "").strip()
    return bool(expected and token and hmac.compare_digest(expected.encode(), token.encode()))


def _preview(msg_type: str, body: str | None) -> str:
    if msg_type == "text":
        return (body or "")[:200]
    label = {"image": "Photo", "document": "Document", "audio": "Voice note", "video": "Video", "sticker": "Sticker", "location": "Location"}.get(msg_type, msg_type.title())
    return f"[{label}]" + (f" {body}" if body else "")[:190]


def get_or_create_conversation(db: Session, wa_phone: str, name: str | None = None) -> WaConversation:
    conv = db.scalar(select(WaConversation).where(WaConversation.wa_phone == wa_phone))
    if conv is None:
        conv = WaConversation(wa_phone=wa_phone, contact_name=(name or None), status="open", unread_count=0)
        db.add(conv)
        db.flush()
    elif name and not conv.contact_name:
        conv.contact_name = name[:255]
    return conv


def _store_inbound(db: Session, message: dict, contact_names: dict[str, str]) -> None:
    wa_id = message.get("id")
    if wa_id and db.scalar(select(WaMessage.id).where(WaMessage.wa_message_id == wa_id)):
        return  # a retry of something already stored
    phone = _normalize_indian_mobile(message.get("from")) or str(message.get("from") or "")
    if not phone:
        return
    msg_type = message.get("type") or "text"
    body, media = None, {}
    if msg_type == "text":
        body = (message.get("text") or {}).get("body")
    elif msg_type in {"image", "document", "audio", "video", "sticker"}:
        media = message.get(msg_type) or {}
        body = media.get("caption")
    elif msg_type == "location":
        loc = message.get("location") or {}
        body = f"{loc.get('latitude')},{loc.get('longitude')} {loc.get('name') or ''}".strip()
    elif msg_type == "button":
        body = (message.get("button") or {}).get("text")
    elif msg_type == "interactive":
        inter = message.get("interactive") or {}
        body = ((inter.get("button_reply") or inter.get("list_reply")) or {}).get("title")
    try:
        sent_at = datetime.fromtimestamp(int(message.get("timestamp")), tz=timezone.utc)
    except (TypeError, ValueError):
        sent_at = _now()

    conv = get_or_create_conversation(db, phone, contact_names.get(message.get("from") or ""))
    db.add(WaMessage(
        conversation_id=conv.id, direction="in", wa_message_id=wa_id, msg_type=msg_type, body=body,
        media_id=media.get("id"), media_mime=media.get("mime_type"), media_name=media.get("filename"),
        status="received", created_at=sent_at,
    ))
    conv.unread_count = (conv.unread_count or 0) + 1
    last_in = _aware(conv.last_inbound_at)
    if last_in is None or sent_at > last_in:
        conv.last_inbound_at = sent_at
    last_msg = _aware(conv.last_message_at)
    if last_msg is None or sent_at >= last_msg:
        conv.last_message_at = sent_at
        conv.last_message_preview = _preview(msg_type, body)
    if conv.status == "closed":
        conv.status = "open"
    if msg_type == "text" and (body or "").strip().lower() in STOP_WORDS:
        conv.opted_out = True  # consent: never send proactive messages to this number again


# A status can only move forward: a late "sent" must not undo "delivered".
_RANK = {"sending": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 9}


def _apply_status(db: Session, status: dict) -> None:
    msg = db.scalar(select(WaMessage).where(WaMessage.wa_message_id == status.get("id")))
    if msg is None or msg.direction != "out":
        return
    new = status.get("status")
    if new not in _RANK:
        return
    if new == "failed":
        errors = status.get("errors") or [{}]
        msg.status = "failed"
        msg.error = ((errors[0].get("title") or "") + " " + (errors[0].get("message") or "")).strip()[:500] or "Failed"
    elif _RANK.get(msg.status, 0) < _RANK[new] and msg.status != "failed":
        msg.status = new


def process_payload(db: Session, payload: dict) -> int:
    """Store the messages and statuses in a Meta webhook body. Returns how many messages were new."""
    configured = (settings.wa_phone_number_id or "").strip()
    stored = 0
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if (change.get("field") or "messages") != "messages":
                continue
            number_id = str((value.get("metadata") or {}).get("phone_number_id") or "")
            if configured and number_id and number_id != configured:
                continue  # meant for another number
            names = {c.get("wa_id"): ((c.get("profile") or {}).get("name") or "") for c in value.get("contacts") or []}
            for message in value.get("messages") or []:
                before = db.scalar(select(WaMessage.id).where(WaMessage.wa_message_id == message.get("id")))
                _store_inbound(db, message, names)
                stored += 0 if before else 1
            for status in value.get("statuses") or []:
                _apply_status(db, status)
    return stored


def handle_webhook(db: Session, raw: bytes) -> None:
    """Save the verified call first, then process it. A failure is recorded on the event; Meta still gets a 200."""
    event = WaWebhookEvent(payload=raw.decode("utf-8", "replace"), received_at=_now())
    db.add(event)
    db.commit()
    try:
        process_payload(db, json.loads(event.payload))
        event.processed = True
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        event = db.get(WaWebhookEvent, event.id)
        event.error = str(exc)[:500]
        db.commit()
        logger.exception("whatsapp webhook processing failed")


def window_open(conv: WaConversation) -> bool:
    last = _aware(conv.last_inbound_at)
    return last is not None and _now() - last < WINDOW


class SendError(Exception):
    pass


def send_text(db: Session, conv: WaConversation, text: str, user_id: int | None) -> WaMessage:
    """Send a free-text reply. Only inside the 24-hour window, never to an opted-out number."""
    text = (text or "").strip()
    if not text:
        raise SendError("Write a message first.")
    if conv.opted_out:
        raise SendError("This customer asked us to stop messaging them.")
    if not window_open(conv):
        raise SendError("It has been more than 24 hours since the customer's last message, so WhatsApp only allows an approved template now.")
    if not settings.whatsapp_enabled:
        raise SendError("WhatsApp sending is switched off (WHATSAPP_ENABLED).")
    number_id = (settings.wa_phone_number_id or "").strip()
    token = (settings.wa_access_token or "").strip()
    if not number_id or not token:
        raise SendError("WhatsApp is not configured on the server.")

    now = _now()
    msg = WaMessage(conversation_id=conv.id, direction="out", msg_type="text", body=text[:4000], status="sending", sent_by=user_id, created_at=now)
    db.add(msg)
    db.flush()  # the row exists before the call, so an ambiguous failure is visible and is not retried blindly
    try:
        r = requests.post(
            f"https://graph.facebook.com/{settings.whatsapp_api_version}/{number_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"messaging_product": "whatsapp", "to": conv.wa_phone, "type": "text", "text": {"body": msg.body, "preview_url": False}},
            timeout=20,
        )
        data = r.json() if r.content else {}
        if r.ok and (data.get("messages") or [{}])[0].get("id"):
            msg.wa_message_id = data["messages"][0]["id"]
            msg.status = "sent"
        else:
            msg.status = "failed"
            msg.error = str((data.get("error") or {}).get("message") or r.text)[:500]
    except requests.RequestException as exc:
        msg.status = "failed"
        msg.error = f"Could not reach WhatsApp: {type(exc).__name__}"
    conv.last_message_at = now
    conv.last_message_preview = msg.body[:200]
    db.commit()
    if msg.status == "failed":
        raise SendError(msg.error or "WhatsApp did not accept the message.")
    return msg
