"""Taking orders from the website into the CRM (idempotent: the same order can be sent any number of times)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.web_order import WebOrder, WebOrderAddress, WebOrderEvent, WebOrderItem, WebOrderPayment

IST = timezone(timedelta(hours=5, minutes=30))  # the website stores its times in Indian time
KNOWN = {
    "id", "order_number", "user_id", "title", "full_name", "first_name", "middle_name", "last_name", "email", "mobile",
    "shipping_address", "billing_address", "gst_number", "company_name", "coupon_code", "discount_amount", "subtotal", "shipping",
    "tax", "total", "status", "payment_status", "payment_method", "razorpay_order_id", "payment_id", "stock_deducted_at",
    "created_at", "updated_at", "items", "addresses", "payments",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _s(v, n: int) -> str | None:
    if v is None:
        return None
    t = str(v).strip()
    return t[:n] if t else None


def _num(v) -> Decimal | None:
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return None


def _int(v) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _dt(v) -> datetime | None:
    if not v:
        return None
    t = str(v).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(t[:26], fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=IST)
    except ValueError:
        return None


def _json_text(v) -> str | None:
    if v is None:
        return None
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _name(o: dict) -> str | None:
    full = _s(o.get("full_name"), 255)
    if full:
        return full
    return _s(" ".join(x for x in (o.get("first_name"), o.get("middle_name"), o.get("last_name")) if x), 255)


def upsert_order(db: Session, o: dict) -> tuple[WebOrder, bool, list[str]]:
    """Create or refresh one order with its items, addresses and payment attempts. Returns (order, created, what changed)."""
    site_id = _int(o.get("id"))
    if site_id is None:
        raise ValueError("an order without an id")
    now = _now()
    order = db.scalar(select(WebOrder).where(WebOrder.site_order_id == site_id))
    created = order is None
    new_status, new_pay = _s(o.get("status"), 50), _s(o.get("payment_status"), 50)
    placed_at = _dt(o.get("created_at")) or now
    changed: list[str] = []
    if created:
        order = WebOrder(site_order_id=site_id, first_synced_at=now, last_synced_at=now)
        db.add(order)
        db.flush()
        db.add(WebOrderEvent(web_order_id=order.id, kind="placed", old_value=None, new_value=new_status, happened_at=placed_at, seen_at=now))
        if new_pay:
            db.add(WebOrderEvent(web_order_id=order.id, kind="payment_status", old_value=None, new_value=new_pay, happened_at=placed_at, seen_at=now))
    else:
        when = _dt(o.get("updated_at")) or now
        if (order.status or None) != new_status:
            db.add(WebOrderEvent(web_order_id=order.id, kind="status", old_value=order.status, new_value=new_status, happened_at=when, seen_at=now))
            changed.append("status")
        if (order.payment_status or None) != new_pay:
            db.add(WebOrderEvent(web_order_id=order.id, kind="payment_status", old_value=order.payment_status, new_value=new_pay, happened_at=when, seen_at=now))
            changed.append("payment_status")
    mobile = _s(o.get("mobile"), 30)
    order.order_number = _s(o.get("order_number"), 100)
    order.site_user_id = _int(o.get("user_id"))
    order.customer_name = _name(o)
    order.email = _s(o.get("email"), 255)
    order.mobile = mobile
    order.mobile10 = (re.sub(r"\D", "", mobile or "")[-10:] or None)
    order.company_name = _s(o.get("company_name"), 255)
    order.gst_number = _s(o.get("gst_number"), 50)
    order.shipping_address = _json_text(o.get("shipping_address"))
    order.billing_address = _json_text(o.get("billing_address"))
    order.coupon_code = _s(o.get("coupon_code"), 100)
    order.discount_amount = _num(o.get("discount_amount"))
    order.subtotal = _num(o.get("subtotal"))
    order.shipping = _num(o.get("shipping"))
    order.tax = _s(o.get("tax"), 100)
    order.total = _num(o.get("total"))
    order.status, order.payment_status = new_status, new_pay
    order.payment_method = _s(o.get("payment_method"), 50)
    order.razorpay_order_id = _s(o.get("razorpay_order_id"), 100)
    order.payment_id = _s(o.get("payment_id"), 100)
    order.stock_deducted_at = _dt(o.get("stock_deducted_at"))
    order.site_created_at = placed_at
    order.site_updated_at = _dt(o.get("updated_at"))
    extra = {k: v for k, v in o.items() if k not in KNOWN}
    order.extra_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else None
    order.last_synced_at = now
    db.flush()

    # children are replaced whole: the website is the source of truth
    for model in (WebOrderItem, WebOrderAddress, WebOrderPayment):
        db.execute(delete(model).where(model.web_order_id == order.id))
    for it in o.get("items") or []:
        db.add(WebOrderItem(
            web_order_id=order.id, site_item_id=_int(it.get("id")), product_id=_s(it.get("product_id"), 100), product_name=_s(it.get("product_name"), 255),
            product_info=_json_text(it.get("product_info")), price=_num(it.get("price")), quantity=_int(it.get("quantity")),
            delivery_date=_s(it.get("delivery_date"), 100), time_slot=_s(it.get("time_slot"), 100),
        ))
    for a in o.get("addresses") or []:
        db.add(WebOrderAddress(
            web_order_id=order.id, kind=_s(a.get("type"), 20), title=_s(a.get("title"), 100), full_name=_s(a.get("full_name"), 255),
            email=_s(a.get("email"), 255), mobile=_s(a.get("mobile"), 30), address_line1=_s(a.get("address_line1"), 255),
            address_line2=_s(a.get("address_line2"), 255), city=_s(a.get("city"), 100), state=_s(a.get("state"), 100),
            pincode=_s(a.get("pincode"), 20), country=_s(a.get("country"), 100),
        ))
    for p in o.get("payments") or []:
        db.add(WebOrderPayment(
            web_order_id=order.id, site_payment_log_id=_int(p.get("id")), razorpay_order_id=_s(p.get("razorpay_order_id"), 100),
            payment_id=_s(p.get("payment_id"), 100), status=_s(p.get("status"), 50), amount=_num(p.get("amount")),
            currency=_s(p.get("currency"), 10), attempted_at=_dt(p.get("attempted_at")), response=_s(p.get("response"), 4000),
        ))
    return order, created, changed


def ingest(db: Session, orders: list[dict]) -> dict:
    created = updated = failed = 0
    errors: list[str] = []
    for o in orders:
        try:
            _, was_new, _ = upsert_order(db, o)
            db.commit()
            created += 1 if was_new else 0
            updated += 0 if was_new else 1
        except Exception as exc:  # noqa: BLE001  one bad order must not stop the rest
            db.rollback()
            failed += 1
            errors.append(f"order {o.get('id')}: {str(exc)[:120]}")
    return {"created": created, "updated": updated, "failed": failed, "errors": errors[:10]}
