"""WhatsApp inbox. The webhook is public (Meta calls it) and protected by the signature; everything else needs a login
and the whatsapp permission."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint
from app.models.service import ServiceRequest
from app.models.user import User
from app.models.whatsapp import WaAiRun, WaConversation, WaMessage, WaNote, WaWebhookEvent
from app.services import wa_ai, whatsapp_inbox as wa
from app.services.permissions import can_act_on
from app.services.role_access import is_system_admin
from app.services.sarvam_chat import chat_configured

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


def _need(db: Session, user: User, flag: str) -> None:
    if not can_act_on(db, user, "whatsapp", flag, None):
        raise HTTPException(403, "You do not have access to WhatsApp")


# ---------------- Meta calls these ----------------
@router.get("/webhook")
def verify_webhook(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and wa.verify_token_ok(q.get("hub.verify_token")):
        return PlainTextResponse(q.get("hub.challenge") or "")
    raise HTTPException(403, "Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    if not ((settings.wa_app_secret or "").strip() or (settings.meta_app_secret or "").strip()):
        raise HTTPException(503, "WhatsApp webhook is not configured")
    raw = await request.body()
    if not wa.signature_ok(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "Invalid signature")
    wa.handle_webhook(db, raw)
    return Response(status_code=200)


# ---------------- inbox (login needed) ----------------
def _conv_out(c: WaConversation, db: Session) -> dict:
    return {
        "id": c.id, "wa_phone": c.wa_phone, "contact_name": c.contact_name, "status": c.status,
        "assigned_to": c.assigned_to, "assigned_name": (db.get(User, c.assigned_to).name if c.assigned_to else None),
        "ai_paused": c.ai_paused, "unread_count": c.unread_count, "opted_out": c.opted_out,
        "last_message_at": c.last_message_at, "last_message_preview": c.last_message_preview,
        "window_open": wa.window_open(c),
    }


@router.get("/status")
def integration_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_view")
    configured = bool((settings.wa_phone_number_id or "").strip() and (settings.wa_access_token or "").strip())
    return {
        "sending_enabled": bool(settings.whatsapp_enabled),
        "configured": configured,
        "app_secret_set": bool((settings.wa_app_secret or "").strip() or (settings.meta_app_secret or "").strip()),
        "verify_token_set": bool((settings.wa_verify_token or "").strip()),
        "phone_number_id": (settings.wa_phone_number_id[:3] + "***" + settings.wa_phone_number_id[-3:]) if settings.wa_phone_number_id else None,
        "api_version": settings.whatsapp_api_version,
        "ai_enabled": bool(settings.whatsapp_ai_enabled),
        "ai_key_set": chat_configured(),
        "ai_switch": wa_ai.switch_on(db),
        "ai_active": wa_ai.server_allows() and wa_ai.switch_on(db),
        "ai_runs_24h": {o: n for o, n in db.execute(select(WaAiRun.outcome, func.count()).where(WaAiRun.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)).group_by(WaAiRun.outcome)).all()},
        "webhook_url": f"{(settings.app_public_url or '').rstrip('/')}/api/whatsapp/webhook" if settings.app_public_url else "/api/whatsapp/webhook",
        "conversations": db.scalar(select(func.count()).select_from(WaConversation)) or 0,
        "unread": db.scalar(select(func.coalesce(func.sum(WaConversation.unread_count), 0))) or 0,
        "messages": db.scalar(select(func.count()).select_from(WaMessage)) or 0,
        "events_failed": db.scalar(select(func.count()).select_from(WaWebhookEvent).where(WaWebhookEvent.error.is_not(None))) or 0,
    }


@router.get("/conversations")
def list_conversations(
    search: Optional[str] = None,
    status: Optional[str] = None,
    unread: bool = False,
    mine: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "can_view")
    stmt = select(WaConversation)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(WaConversation.wa_phone.ilike(like), WaConversation.contact_name.ilike(like), WaConversation.last_message_preview.ilike(like)))
    if status:
        stmt = stmt.where(WaConversation.status == status)
    if unread:
        stmt = stmt.where(WaConversation.unread_count > 0)
    if mine:
        stmt = stmt.where(WaConversation.assigned_to == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(desc(WaConversation.last_message_at), desc(WaConversation.id)).offset((page - 1) * per_page).limit(per_page)).all()
    return {"items": [_conv_out(c, db) for c in rows], "total": total, "page": page, "per_page": per_page}


def _load(db: Session, conv_id: int) -> WaConversation:
    conv = db.get(WaConversation, conv_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_view")
    conv = _load(db, conv_id)
    msgs = db.scalars(select(WaMessage).where(WaMessage.conversation_id == conv.id).order_by(WaMessage.created_at, WaMessage.id).limit(500)).all()
    notes = db.scalars(select(WaNote).where(WaNote.conversation_id == conv.id).order_by(WaNote.created_at)).all()
    last10 = conv.wa_phone[-10:]
    complaints = db.scalars(select(Complaint).where(Complaint.customer_mobile == last10, Complaint.deleted_at.is_(None)).order_by(desc(Complaint.id)).limit(8)).all()
    services = db.scalars(select(ServiceRequest).where(ServiceRequest.customer_mobile == last10, ServiceRequest.deleted_at.is_(None)).order_by(desc(ServiceRequest.id)).limit(8)).all()
    return {
        "conversation": _conv_out(conv, db),
        "messages": [
            {"id": m.id, "direction": m.direction, "type": m.msg_type, "body": m.body, "media_name": m.media_name, "status": m.status,
             "error": m.error, "sent_by": (db.get(User, m.sent_by).name if m.sent_by else None), "created_at": m.created_at}
            for m in msgs
        ],
        "notes": [{"id": n.id, "body": n.body, "by": (db.get(User, n.created_by).name if n.created_by else None), "created_at": n.created_at} for n in notes],
        "complaints": [{"id": c.id, "comp_no": c.comp_no, "status": c.status, "query_type": c.query_type} for c in complaints],
        "services": [{"id": s.id, "request_no": s.request_no, "status": s.status} for s in services],
    }


@router.post("/conversations/{conv_id}/read")
def mark_read(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_view")
    conv = _load(db, conv_id)
    conv.unread_count = 0
    db.commit()
    return {"ok": True}


@router.post("/conversations/{conv_id}/reply")
def reply(conv_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    try:
        msg = wa.send_text(db, conv, str(body.get("text") or ""), user.id)
    except wa.SendError as exc:
        raise HTTPException(409, str(exc))
    if conv.assigned_to is None:
        conv.assigned_to = user.id  # whoever answers first owns the thread
    conv.unread_count = 0
    db.commit()
    return {"ok": True, "message_id": msg.id, "status": msg.status}


@router.post("/conversations/{conv_id}/assign")
def assign(conv_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    conv.assigned_to = user.id if body.get("to_me") else None
    db.commit()
    return _conv_out(conv, db)


@router.post("/conversations/{conv_id}/status")
def set_status(conv_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    value = str(body.get("status") or "")
    if value not in {"open", "needs_staff", "closed"}:
        raise HTTPException(422, "Status must be open, needs_staff or closed")
    conv.status = value
    db.commit()
    return _conv_out(conv, db)


@router.post("/conversations/{conv_id}/ai-pause")
def ai_pause(conv_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    conv.ai_paused = bool(body.get("paused"))
    db.commit()
    return _conv_out(conv, db)


@router.post("/ai-switch")
def ai_switch(body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The master switch for automatic replies. Administrators only."""
    if not is_system_admin(user):
        raise HTTPException(403, "Only an administrator can switch automatic replies on or off")
    on = bool(body.get("on"))
    if on and not wa_ai.server_allows():
        raise HTTPException(409, "Automatic replies are not allowed on this server yet (the Sarvam key or WHATSAPP_AI_ENABLED is missing)")
    wa_ai.set_switch(db, on, user.id)
    return {"ai_switch": wa_ai.switch_on(db)}


@router.post("/conversations/{conv_id}/resume")
def resume_auto(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Give the chat back to the automatic replies after staff have dealt with it."""
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    conv.assigned_to = None
    conv.ai_paused = False
    conv.pending_action = None
    if conv.status == "needs_staff":
        conv.status = "open"
    db.commit()
    return _conv_out(conv, db)


@router.post("/conversations/{conv_id}/notes")
def add_note(conv_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "can_edit")
    conv = _load(db, conv_id)
    text = str(body.get("body") or "").strip()
    if not text:
        raise HTTPException(422, "Write the note first")
    db.add(WaNote(conversation_id=conv.id, body=text[:4000], created_by=user.id, created_at=datetime.now(timezone.utc)))
    db.commit()
    return {"ok": True}
