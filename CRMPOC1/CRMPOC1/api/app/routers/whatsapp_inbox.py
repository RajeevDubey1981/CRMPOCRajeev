"""WhatsApp inbox. The webhook is public (Meta calls it) and protected by the signature; everything else needs a login
and the whatsapp permission."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint
from app.models.service import ServiceRequest
from app.models.user import User
from app.models.whatsapp import WaAiRun, WaConversation, WaKnowledge, WaMessage, WaNote, WaWebhookEvent
from app.services import wa_ai, wa_knowledge, whatsapp_inbox as wa
from app.services.pending_action_service import resolve_all_for_entity
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


@router.get("/for-complaint/{complaint_id}")
def chat_for_complaint(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Is there a WhatsApp chat with this complaint's customer? Used by the complaint page."""
    if not can_act_on(db, user, "whatsapp", "can_view", None):
        return {"conversation_id": None}
    c = db.get(Complaint, complaint_id)
    if c is None or not (c.customer_mobile or "").strip():
        return {"conversation_id": None}
    conv = db.scalar(select(WaConversation).where(WaConversation.wa_phone.like("%" + c.customer_mobile.strip()[-10:])))
    if conv is None:
        return {"conversation_id": None}
    count = db.scalar(select(func.count()).select_from(WaMessage).where(WaMessage.conversation_id == conv.id)) or 0
    return {"conversation_id": conv.id, "messages": count, "status": conv.status, "last_message_at": conv.last_message_at}


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
    resolve_all_for_entity(db, module="whatsapp", entity_id=conv.id)  # someone answered: the bell alert is done
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
    if body.get("to_me"):
        resolve_all_for_entity(db, module="whatsapp", entity_id=conv.id)
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
    if value != "needs_staff":
        resolve_all_for_entity(db, module="whatsapp", entity_id=conv.id)
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
    resolve_all_for_entity(db, module="whatsapp", entity_id=conv.id)
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


# ---------------- what the assistant knows (administrators only) ----------------
def _admin(user: User) -> None:
    if not is_system_admin(user):
        raise HTTPException(403, "Only an administrator can change what the assistant knows")


def _k_out(k: WaKnowledge, full: bool = True) -> dict:
    d = {"id": k.id, "title": k.title, "category": k.category, "always_send": k.always_send, "active": k.active, "source": k.source,
         "chars": len(k.body or ""), "updated_at": k.updated_at}
    if full:
        d["body"] = k.body
    return d


@router.get("/knowledge")
def list_knowledge(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    rows = db.scalars(select(WaKnowledge).order_by(WaKnowledge.always_send.desc(), WaKnowledge.category, WaKnowledge.title)).all()
    return {"using": "database" if rows else "builtin files", "items": [_k_out(r, full=False) for r in rows]}


@router.get("/knowledge/{kid}")
def get_knowledge(kid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    k = db.get(WaKnowledge, kid)
    if k is None:
        raise HTTPException(404, "Entry not found")
    return _k_out(k)


def _clean_entry(body: dict) -> dict:
    title = str(body.get("title") or "").strip()[:200]
    text = str(body.get("body") or "").strip()
    if not title or not text:
        raise HTTPException(422, "An entry needs a title and some text")
    if len(text) > 60000:
        raise HTTPException(422, "That entry is too long (60,000 characters at most). Split it into several entries.")
    return {"title": title, "body": text, "category": str(body.get("category") or "").strip()[:100],
            "always_send": bool(body.get("always_send")), "active": body.get("active", True) is not False}


@router.post("/knowledge")
def create_knowledge(body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    data = _clean_entry(body)
    wa_knowledge.ensure_seeded(db, user.id)  # the first change keeps everything from the built-in files
    k = WaKnowledge(**data, source="typed", updated_by=user.id)
    db.add(k)
    db.commit()
    return _k_out(k)


@router.put("/knowledge/{kid}")
def update_knowledge(kid: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    k = db.get(WaKnowledge, kid)
    if k is None:
        raise HTTPException(404, "Entry not found")
    for key, value in _clean_entry({**_k_out(k), **body}).items():
        setattr(k, key, value)
    k.updated_by = user.id
    db.commit()
    return _k_out(k)


@router.delete("/knowledge/{kid}")
def delete_knowledge(kid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _admin(user)
    k = db.get(WaKnowledge, kid)
    if k is None:
        raise HTTPException(404, "Entry not found")
    db.delete(k)
    db.commit()
    return {"ok": True}


@router.post("/knowledge-import")
def import_builtin_knowledge(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Copy the built-in knowledge files into the editor (only while it is empty)."""
    _admin(user)
    return {"created": wa_knowledge.import_builtin(db, user.id)}


@router.post("/knowledge-upload")
async def upload_knowledge(
    file: UploadFile = File(...), category: str = Form(""), always_send: bool = Form(False),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """A Word, Markdown or text file becomes one or more entries."""
    _admin(user)
    data = await file.read()
    if len(data) > 3 * 1024 * 1024:
        raise HTTPException(413, "That file is too big (3 MB at most)")
    try:
        text = wa_knowledge.read_upload(file.filename or "", data)
        stem = (file.filename or "upload").rsplit(".", 1)[0][:150]
        entries = wa_knowledge.split_into_entries(stem, text, (category or stem).strip()[:100])
    except wa_knowledge.UploadError as exc:
        raise HTTPException(422, str(exc))
    if len(entries) > 300:
        raise HTTPException(422, "That file would make more than 300 entries. Split it first.")
    wa_knowledge.ensure_seeded(db, user.id)
    for title, cat, text_body in entries:
        db.add(WaKnowledge(title=title, category=cat, body=text_body, always_send=bool(always_send), active=True, source="upload", updated_by=user.id))
    db.commit()
    return {"created": len(entries)}


@router.post("/knowledge-preview")
def preview_knowledge(body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """What the assistant would be given for a customer question: the general rules plus the entries that match it."""
    _admin(user)
    head, chosen = wa_knowledge.select_blocks(str(body.get("question") or ""), db)
    titles = [c.split("###", 1)[1].strip().splitlines()[0] if "###" in c else c[:80] for c in chosen]
    return {"general_chars": len(head), "matched": titles, "total_chars": len(head) + sum(len(c) for c in chosen)}
