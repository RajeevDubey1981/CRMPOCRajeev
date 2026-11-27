"""Web orders: orders placed on www.indcool.in, synced into the CRM.

The sync endpoint is called by a small script on the website server and is protected by a shared key; everything else
needs a login and the web_orders permission (ticked per role on the Permissions page).
"""
from __future__ import annotations

import csv
import hmac
import io
import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint
from app.models.user import User
from app.models.web_order import WebOrder, WebOrderAddress, WebOrderEvent, WebOrderItem, WebOrderPayment
from app.models.whatsapp import WaConversation, WaSetting
from app.services import web_orders as svc
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/web-orders", tags=["web-orders"])


def _need(db: Session, user: User, flag: str = "can_view") -> None:
    if not can_act_on(db, user, "web_orders", flag, None):
        raise HTTPException(403, "You do not have access to Web Orders")


# ---------------- the website calls this ----------------
@router.post("/ingest")
def ingest(payload: dict = Body(...), x_web_orders_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    secret = (settings.web_orders_ingest_key or "").strip()
    if not secret:
        raise HTTPException(503, "Web order sync is not switched on")
    if not x_web_orders_key or not hmac.compare_digest(x_web_orders_key.encode(), secret.encode()):
        raise HTTPException(401, "Invalid key")
    orders = payload.get("orders")
    if not isinstance(orders, list) or len(orders) > 200:
        raise HTTPException(422, "Send {\"orders\": [...]} with at most 200 orders")
    result = svc.ingest(db, [o for o in orders if isinstance(o, dict)])
    beat = db.get(WaSetting, "web_orders_heartbeat")  # the sync script calls every minute, even with nothing new: this tells the screen it is alive
    if beat is None:
        beat = WaSetting(key="web_orders_heartbeat")
        db.add(beat)
    beat.value = datetime.now(timezone.utc).isoformat()
    beat.updated_at = datetime.now(timezone.utc)
    db.commit()
    return result


# ---------------- screens (login needed) ----------------
def _row(o: WebOrder) -> dict:
    return {
        "id": o.id, "site_order_id": o.site_order_id, "order_number": o.order_number, "customer_name": o.customer_name,
        "mobile": o.mobile, "email": o.email, "total": float(o.total) if o.total is not None else None, "status": o.status,
        "payment_status": o.payment_status, "payment_method": o.payment_method, "placed_at": o.site_created_at,
        "updated_at": o.site_updated_at, "last_synced_at": o.last_synced_at,
    }


def _filtered(q: str, status: str, payment: str, date_from: date | None, date_to: date | None):
    stmt = select(WebOrder)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(WebOrder.order_number.ilike(like), WebOrder.customer_name.ilike(like), WebOrder.mobile.ilike(like),
                              WebOrder.email.ilike(like), WebOrder.payment_id.ilike(like), WebOrder.razorpay_order_id.ilike(like)))
    if status:
        stmt = stmt.where(func.lower(WebOrder.status) == status.lower())
    if payment:
        stmt = stmt.where(func.lower(WebOrder.payment_status) == payment.lower())
    ist = timezone(timedelta(hours=5, minutes=30))
    if date_from:
        stmt = stmt.where(WebOrder.site_created_at >= datetime.combine(date_from, datetime.min.time(), ist))
    if date_to:
        stmt = stmt.where(WebOrder.site_created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), ist))
    return stmt


@router.get("")
def list_orders(
    q: str = "", status: str = "", payment_status: str = "", date_from: date | None = None, date_to: date | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _need(db, user)
    base = _filtered(q, status, payment_status, date_from, date_to)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(desc(WebOrder.site_created_at), desc(WebOrder.id)).limit(limit).offset(offset)).all()
    return {"total": total, "items": [_row(o) for o in rows]}


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Counts for the chips, and how fresh the sync is (the screen shows 'live' while it is recent)."""
    _need(db, user)
    by_status = {(s or "unknown"): n for s, n in db.execute(select(WebOrder.status, func.count()).group_by(WebOrder.status)).all()}
    by_payment = {(s or "unknown"): n for s, n in db.execute(select(WebOrder.payment_status, func.count()).group_by(WebOrder.payment_status)).all()}
    last = db.scalar(select(func.max(WebOrder.last_synced_at)))
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.combine(datetime.now(ist).date(), datetime.min.time(), ist)
    return {
        "total": sum(by_status.values()), "by_status": by_status, "by_payment_status": by_payment,
        "today": db.scalar(select(func.count()).select_from(WebOrder).where(WebOrder.site_created_at >= today)) or 0,
        "last_synced_at": last, "heartbeat_at": (db.get(WaSetting, "web_orders_heartbeat").value if db.get(WaSetting, "web_orders_heartbeat") else None), "sync_enabled": bool((settings.web_orders_ingest_key or "").strip()),
    }


def _dump(m, skip=("web_order_id",)) -> dict:
    out = {}
    for c in m.__table__.columns:
        if c.name in skip:
            continue
        v = getattr(m, c.name)
        out[c.name] = float(v) if hasattr(v, "as_tuple") else v
    return out


@router.get("/export")
def export_csv(
    q: str = "", status: str = "", payment_status: str = "", date_from: date | None = None, date_to: date | None = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _need(db, user, "can_export")
    rows = db.scalars(_filtered(q, status, payment_status, date_from, date_to).order_by(desc(WebOrder.site_created_at)).limit(5000)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Order", "Placed", "Customer", "Mobile", "Email", "Total", "Status", "Payment status", "Payment method", "Payment id", "Shipping address"])
    for o in rows:
        w.writerow([o.order_number, o.site_created_at, o.customer_name, o.mobile, o.email, o.total, o.status, o.payment_status, o.payment_method, o.payment_id, (o.shipping_address or "").replace("\n", " ")])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=web-orders.csv"})


@router.get("/{order_id}")
def detail(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user)
    o = db.get(WebOrder, order_id)
    if o is None:
        raise HTTPException(404, "Order not found")
    items = db.scalars(select(WebOrderItem).where(WebOrderItem.web_order_id == o.id).order_by(WebOrderItem.id)).all()
    addresses = db.scalars(select(WebOrderAddress).where(WebOrderAddress.web_order_id == o.id).order_by(WebOrderAddress.id)).all()
    payments = db.scalars(select(WebOrderPayment).where(WebOrderPayment.web_order_id == o.id).order_by(WebOrderPayment.attempted_at, WebOrderPayment.id)).all()
    events = db.scalars(select(WebOrderEvent).where(WebOrderEvent.web_order_id == o.id).order_by(WebOrderEvent.happened_at, WebOrderEvent.id)).all()
    data = _dump(o)
    data["extra"] = json.loads(o.extra_json) if o.extra_json else None
    data.pop("extra_json", None)
    out_items = []
    for it in items:
        d = _dump(it)
        try:
            d["product_info"] = json.loads(it.product_info) if it.product_info else None
        except ValueError:
            pass
        out_items.append(d)
    complaints, chat = [], None
    if o.mobile10:
        complaints = [
            {"id": c.id, "comp_no": c.comp_no, "status": c.status, "query_type": c.query_type, "comp_date": c.comp_date}
            for c in db.scalars(select(Complaint).where(Complaint.customer_mobile == o.mobile10, Complaint.deleted_at.is_(None)).order_by(desc(Complaint.id)).limit(10))
        ]
        if can_act_on(db, user, "whatsapp", "can_view", None):
            conv = db.scalar(select(WaConversation).where(WaConversation.wa_phone.like("%" + o.mobile10)))
            chat = conv.id if conv else None
    return {
        "order": data, "items": out_items, "addresses": [_dump(a) for a in addresses], "payments": [_dump(p) for p in payments],
        "events": [_dump(e) for e in events], "complaints": complaints, "whatsapp_conversation_id": chat,
    }
