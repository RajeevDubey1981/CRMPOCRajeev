"""INDcool Assistant: a free, in-app help bot. Pure keyword matching over a small guide-content
list (app/assistant_intents.py) plus a few real lookups against the CRM's own data (order search,
ledger balance) -- no external AI API, no per-request cost. Every lookup is scoped through the same
permission/visibility rules every other page already uses (e.g. a vendor only ever sees their own
orders, via the same _vendor_ids_for_user/_apply_order_visibility helpers orders.py uses)."""

import re
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant_intents import GUIDE_INTENTS, LOOKUP_INTENTS
from app.database import get_db
from app.deps import get_current_user
from app.models.account_ledger import AccountLedgerEntry
from app.models.complaint import Complaint
from app.models.courier import Courier
from app.models.installation import InstallationRequest
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.vendor import Vendor
from app.services.role_access import is_operations_admin, role_key

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AskIn(BaseModel):
    message: str


class AskOut(BaseModel):
    text: str
    steps: list[str] | None = None
    link: str | None = None
    link_label: str | None = None
    card_title: str | None = None
    card_body: str | None = None


def _stem(word: str) -> str:
    # Minimal plural-folding so "lead"/"leads", "quote"/"quotes" etc. match without
    # enumerating every form in assistant_intents.py.
    if len(word) > 3 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _score(message_words: set[str], keywords: list[str]) -> int:
    score = 0
    for kw in keywords:
        kw_words = kw.lower().split()
        if all(w in message_words for w in kw_words):
            score += len(kw_words)
    return score


def _best_match(message: str, intents: list[dict]) -> dict | None:
    raw_words = set(re.findall(r"[a-z0-9]+", message.lower()))
    words = raw_words | {_stem(w) for w in raw_words}
    best, best_score = None, 0
    for intent in intents:
        s = _score(words, intent["keywords"])
        if s > best_score:
            best, best_score = intent, s
    return best


def _extract_order_token(message: str) -> str | None:
    # An order number/serial usually has a digit in it -- pull the longest such token.
    tokens = re.findall(r"[A-Za-z0-9\-/]+", message)
    candidates = [t for t in tokens if any(c.isdigit() for c in t) and len(t) >= 4]
    if not candidates:
        return None
    return max(candidates, key=len)


def _find_order(db: Session, user: User, message: str) -> AskOut:
    from app.routers.orders import _apply_order_visibility, _vendor_ids_for_user

    token = _extract_order_token(message)
    if not token:
        return AskOut(text="Tell me an order number or part of it, e.g. \"where is order GEMC-761\".")

    vendor_ids = _vendor_ids_for_user(db, user)
    stmt = select(Order).where(Order.deleted_at.is_(None), Order.order_no.ilike(f"%{token}%"))
    stmt = _apply_order_visibility(stmt, user, vendor_ids)
    order = db.scalars(stmt.limit(1)).first()
    if not order:
        return AskOut(text=f"No order found matching \"{token}\" that you have access to.")
    return AskOut(
        text="Found it:",
        card_title=order.order_no or f"Order #{order.id}",
        card_body=f"{order.status}" + (f" · {order.customer_name}" if order.customer_name else ""),
        link=f"/orders/{order.id}",
        link_label="Open order",
    )


def _ledger_balance(db: Session, party_type: str, party_id: int) -> Decimal:
    entries = db.scalars(
        select(AccountLedgerEntry).where(
            AccountLedgerEntry.party_type == party_type, AccountLedgerEntry.party_id == party_id,
        )
    ).all()
    credit = sum((Decimal(str(e.amount)) for e in entries if e.entry_type == "credit"), Decimal("0"))
    debit = sum((Decimal(str(e.amount)) for e in entries if e.entry_type == "debit"), Decimal("0"))
    return credit - debit


def _find_courier_balance(db: Session, message: str) -> AskOut:
    words = re.findall(r"[A-Za-z]+", message)
    if not words:
        return AskOut(text="Tell me the courier's name, e.g. \"delhivery balance\".")
    like = "%" + "%".join(words) + "%"
    courier = db.scalars(select(Courier).where(Courier.deleted_at.is_(None), Courier.courier_name.ilike(like)).limit(1)).first()
    if not courier:
        return AskOut(text="Couldn't match that to a courier name.")
    balance = _ledger_balance(db, "courier", courier.id)
    return AskOut(
        text="Here's the current ledger balance:",
        card_title=courier.courier_name,
        card_body=f"₹{balance:,.2f} due" if balance > 0 else f"₹{abs(balance):,.2f} credit",
        link=f"/ledger/courier/{courier.id}",
        link_label="Open ledger",
    )


def _find_vendor_balance(db: Session, user: User, message: str) -> AskOut:
    words = re.findall(r"[A-Za-z]+", message)
    if user.role == "vendor":
        vendor = db.scalars(
            select(Vendor).where(Vendor.deleted_at.is_(None), Vendor.is_active.is_(True), Vendor.email.ilike(user.email or ""))
        ).first()
    elif words:
        like = "%" + "%".join(words) + "%"
        vendor = db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None), Vendor.name_of_firm.ilike(like)).limit(1)).first()
    else:
        vendor = None
    if not vendor:
        return AskOut(text="Tell me the vendor's name, e.g. \"comtech balance\".")
    balance = _ledger_balance(db, "vendor", vendor.id)
    return AskOut(
        text="Here's the current ledger balance:",
        card_title=vendor.name_of_firm,
        card_body=f"₹{balance:,.2f} due" if balance > 0 else f"₹{abs(balance):,.2f} credit",
        link=f"/ledger/vendor/{vendor.id}",
        link_label="Open ledger",
    )


def _find_lead(db: Session, user: User, message: str) -> AskOut:
    from app.sales.db import get_sales_db, sales_enabled
    from app.sales.models import SalesLead

    if not sales_enabled():
        return AskOut(text="Sales isn't set up on this environment.")

    token = _extract_order_token(message)
    sales_db = next(get_sales_db())
    try:
        stmt = select(SalesLead)
        if token:
            stmt = stmt.where((SalesLead.phone.ilike(f"%{token}%")) | (SalesLead.name.ilike(f"%{token}%")))
        else:
            words = re.findall(r"[A-Za-z]+", message)
            if not words:
                return AskOut(text="Tell me the lead's name or phone number, e.g. \"find lead 98765...\".")
            like = "%" + "%".join(words) + "%"
            stmt = stmt.where(SalesLead.name.ilike(like))
        if not is_operations_admin(user):
            stmt = stmt.where(SalesLead.owner_user_id == user.id)
        lead = db_scalars_first(sales_db, stmt.order_by(SalesLead.id.desc()))
        if not lead:
            return AskOut(text="No matching lead found that you have access to.")
        return AskOut(
            text="Found it:",
            card_title=f"{lead.name} · {lead.phone}",
            card_body=f"{lead.status} · {lead.heat} · {lead.item or '—'}",
            link=f"/sales/leads/{lead.id}",
            link_label="Open lead",
        )
    finally:
        sales_db.close()


def db_scalars_first(db: Session, stmt):
    return db.scalars(stmt.limit(1)).first()


def _find_serial(db: Session, user: User, message: str) -> AskOut:
    from app.routers.orders import _apply_order_visibility, _vendor_ids_for_user

    token = _extract_order_token(message)
    if not token:
        return AskOut(text="Tell me the serial number, e.g. \"serial IDCACEZO26090201856\".")
    vendor_ids = _vendor_ids_for_user(db, user)
    stmt = (
        select(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.deleted_at.is_(None), (OrderItem.serial_no.ilike(f"%{token}%")) | (OrderItem.serial_no_2.ilike(f"%{token}%")))
    )
    stmt = _apply_order_visibility(stmt, user, vendor_ids)
    row = db.execute(stmt.limit(1)).first()
    if not row:
        return AskOut(text=f"No serial found matching \"{token}\" that you have access to.")
    item, order = row
    return AskOut(
        text="Found it:",
        card_title=item.serial_no or item.serial_no_2,
        card_body=f"{item.item_code or 'Item'} · Order {order.order_no or order.id} · {order.status}",
        link=f"/orders/{order.id}",
        link_label="Open order",
    )


def _find_complaint(db: Session, user: User, message: str) -> AskOut:
    token = _extract_order_token(message)
    stmt = select(Complaint).where(Complaint.deleted_at.is_(None))
    if token:
        stmt = stmt.where((Complaint.comp_no.ilike(f"%{token}%")) | (Complaint.customer_mobile.ilike(f"%{token}%")))
    else:
        words = re.findall(r"[A-Za-z]+", message)
        if not words:
            return AskOut(text="Tell me the complaint number or customer phone, e.g. \"complaint status 9876543210\".")
        stmt = stmt.where(Complaint.customer_name.ilike("%" + "%".join(words) + "%"))
    if role_key(user.role) == "engineer":
        stmt = stmt.where(Complaint.assigned_engineer == user.id)
    complaint = db.scalars(stmt.order_by(Complaint.id.desc()).limit(1)).first()
    if not complaint:
        return AskOut(text="No matching complaint found that you have access to.")
    return AskOut(
        text="Found it:",
        card_title=f"{complaint.comp_no} · {complaint.customer_name}",
        card_body=f"{complaint.status} · {complaint.query_type or ''}",
        link=f"/complaints/{complaint.id}",
        link_label="Open complaint",
    )


def _find_installation(db: Session, user: User, message: str) -> AskOut:
    token = _extract_order_token(message)
    stmt = select(InstallationRequest)
    if token:
        stmt = stmt.where(
            (InstallationRequest.contact_number.ilike(f"%{token}%"))
            | (InstallationRequest.engineer_entered_serial_no.ilike(f"%{token}%"))
            | (InstallationRequest.engineer_entered_serial_no_2.ilike(f"%{token}%"))
        )
    else:
        words = re.findall(r"[A-Za-z]+", message)
        if not words:
            return AskOut(text="Tell me the customer phone or serial number, e.g. \"installation status 9876543210\".")
        stmt = stmt.where(InstallationRequest.customer_name.ilike("%" + "%".join(words) + "%"))
    if role_key(user.role) == "engineer":
        stmt = stmt.where(InstallationRequest.assigned_engineer == user.id)
    inst = db.scalars(stmt.order_by(InstallationRequest.id.desc()).limit(1)).first()
    if not inst:
        return AskOut(text="No matching installation request found that you have access to.")
    return AskOut(
        text="Found it:",
        card_title=f"{inst.customer_name} · {inst.contact_number}",
        card_body=f"{inst.status}",
        link=f"/installations/{inst.id}",
        link_label="Open installation request",
    )


@router.post("/ask", response_model=AskOut)
def ask(body: AskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = body.message.strip()
    if not message:
        return AskOut(text="Ask me where to find something, or how to do a task — e.g. \"how to find leads\" or \"where is order GEMC-761\".")

    lookup = _best_match(message, LOOKUP_INTENTS)
    guide = _best_match(message, GUIDE_INTENTS)

    # A lookup intent wins only if it scored at least as well as the best guide match --
    # otherwise a guide question that happens to mention "order" (e.g. "how to process return order")
    # would get routed to a raw order search instead of the guide.
    raw_words = set(re.findall(r"[a-z0-9]+", message.lower()))
    scored_words = raw_words | {_stem(w) for w in raw_words}
    lookup_score = _score(scored_words, lookup["keywords"]) if lookup else 0
    guide_score = _score(scored_words, guide["keywords"]) if guide else 0

    if lookup and lookup_score > 0 and lookup_score >= guide_score:
        if lookup["id"] == "find_order":
            return _find_order(db, user, message)
        if lookup["id"] == "courier_ledger":
            return _find_courier_balance(db, message)
        if lookup["id"] == "vendor_ledger":
            return _find_vendor_balance(db, user, message)
        if lookup["id"] == "find_lead":
            return _find_lead(db, user, message)
        if lookup["id"] == "find_serial":
            return _find_serial(db, user, message)
        if lookup["id"] == "find_complaint":
            return _find_complaint(db, user, message)
        if lookup["id"] == "find_installation":
            return _find_installation(db, user, message)

    if guide and guide_score > 0:
        return AskOut(text=guide["text"], steps=guide["steps"], link=guide["link"], link_label=guide["link_label"])

    return AskOut(text="I don't have a guide for that yet. Try \"how to find leads\", \"process a return\", \"add courier\", or \"where is order ...\".")
