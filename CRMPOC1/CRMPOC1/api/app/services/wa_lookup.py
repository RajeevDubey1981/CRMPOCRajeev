"""Read-only look-ups the WhatsApp assistant may answer from the CRM.

Privacy rule for all of them: an order, serial or complaint is shown only when the customer's own WhatsApp mobile number
is on it. No amounts, no addresses, no other people's names. Anything else gets the same "could not find" reply, so the
answer never reveals whether a record exists for somebody else.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.courier import Courier
from app.models.installation import InstallationRequest
from app.models.order import Order, OrderConsigneeAddress, OrderItem
from app.models.user import User

NOT_FOUND = ("I could not find that for this WhatsApp number. Please check the number, or I can bring in a team member to look into it.")


def _squash(v: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", v or "").upper()


def _last10(v: str | None) -> str:
    return re.sub(r"\D", "", v or "")[-10:]


def _first_name(db: Session, user_id: int | None) -> str:
    if not user_id:
        return ""
    u = db.get(User, user_id)
    return (u.name or "").split()[0] if u and u.name else ""


def _d(v) -> str:
    if isinstance(v, datetime):
        v = v.date()
    return f"{v:%d %b %Y}" if isinstance(v, date) else ""


def _order_is_mine(db: Session, order: Order, mobile: str) -> bool:
    if _last10(order.customer_contact) == mobile:
        return True
    contacts = db.scalars(select(OrderConsigneeAddress.contact).where(OrderConsigneeAddress.order_id == order.id)).all()
    return any(_last10(c) == mobile for c in contacts)


def order_text(db: Session, mobile: str, order_no: str | None) -> str:
    key = _squash(order_no)
    if len(key) < 3:
        return "Please share your order number and I will check it."
    rows = db.scalars(select(Order).where(Order.deleted_at.is_(None), Order.order_no.is_not(None)).where(or_(Order.customer_contact.like("%" + mobile), Order.order_no.ilike("%" + (order_no or "").strip() + "%"))).order_by(desc(Order.id)).limit(50)).all()
    order = next((o for o in rows if _squash(o.order_no) == key), None) or next((o for o in rows if key in _squash(o.order_no)), None)
    if order is None or not _order_is_mine(db, order, mobile):
        return NOT_FOUND
    lines = [f"Order {order.order_no}, placed {_d(order.order_date)}: {order.status}."]
    if order.actual_delivery_date:
        lines.append(f"Delivered on {_d(order.actual_delivery_date)}.")
    elif order.expected_delivery_date:
        lines.append(f"Expected delivery: {_d(order.expected_delivery_date)}.")
    courier = db.get(Courier, order.courier_id) if order.courier_id else None
    if order.lrn_no:
        lines.append(f"Dispatched{(' with ' + courier.courier_name) if courier else ''}, tracking (LR) number {order.lrn_no}.")
    return " ".join(lines) + " For anything more, I can bring in our team."


def _install_date(db: Session, item: OrderItem) -> date | None:
    inst = db.scalar(
        select(InstallationRequest)
        .where(InstallationRequest.installation_date.is_not(None), or_(InstallationRequest.order_item_id == item.id, InstallationRequest.serial_no == item.serial_no))
        .order_by(desc(InstallationRequest.installation_date)).limit(1)
    )
    return inst.installation_date.date() if inst and inst.installation_date else None


def _plus_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


def warranty_text(db: Session, mobile: str, serial: str | None) -> str:
    key = _squash(serial)
    if len(key) < 5:
        return "Please share the serial number from the label on the product and I will check its warranty."
    items = db.scalars(select(OrderItem).where(or_(OrderItem.serial_no.ilike("%" + (serial or "").strip() + "%"), OrderItem.serial_no_2.ilike("%" + (serial or "").strip() + "%"))).limit(20)).all()
    item = next((i for i in items if key in (_squash(i.serial_no), _squash(i.serial_no_2))), None)
    if item is None:
        return NOT_FOUND
    order = db.get(Order, item.order_id)
    mine = bool(order and not order.deleted_at and _order_is_mine(db, order, mobile))
    if not mine:  # a complaint on this serial raised from the same mobile also proves it is theirs
        mine = bool(db.scalar(select(Complaint.id).where(Complaint.serial_no == item.serial_no, Complaint.customer_mobile == mobile, Complaint.deleted_at.is_(None)).limit(1)))
    if not mine:
        return NOT_FOUND
    start = _install_date(db, item)
    parts = []
    for label, years in (("Machine", item.machine_warranty_years), ("Compressor and components", item.component_warranty_years), ("PCB", item.pcb_warranty_years)):
        if years:
            parts.append(f"{label}: {years} {'year' if years == 1 else 'years'}" + (f", until {_d(_plus_years(start, years))}" if start else ""))
    if not parts:
        return "I can see this unit, but its warranty is not recorded yet. I can bring in our team to confirm it for you."
    head = f"Warranty for serial {item.serial_no or item.serial_no_2}" + (f" (installed {_d(start)})" if start else "") + ":"
    tail = "" if start else " Warranty starts from the installation date, which is not recorded yet."
    return head + " " + "; ".join(parts) + "." + tail + " The service team confirms the final warranty on a repair."


def complaint_text(db: Session, mobile: str, comp_no: str | None) -> str:
    rows = db.scalars(select(Complaint).where(Complaint.customer_mobile == mobile, Complaint.deleted_at.is_(None)).order_by(desc(Complaint.id)).limit(10)).all()
    if comp_no:
        key = _squash(comp_no)
        rows = [c for c in rows if _squash(c.comp_no) == key or _squash(c.comp_no).endswith(key)] if key else rows
    installs = db.scalars(select(InstallationRequest).where(InstallationRequest.contact_number.like("%" + mobile)).order_by(desc(InstallationRequest.id)).limit(3)).all()
    if comp_no and not rows:
        installs = []
    if not rows and not installs:
        return "I could not find a request registered with this WhatsApp number. Please tell me the complaint number, or I can bring in a team member."
    lines = []
    for c in rows[:3]:
        line = f"{c.comp_no} ({c.query_type}), registered {_d(c.comp_date)}: {c.status}"
        eng = _first_name(db, c.assigned_engineer)
        if eng and c.status not in ("Closed", "Resolved", "Completed"):
            line += f", engineer {eng} assigned"
        if c.status_date:
            line += f" (updated {_d(c.status_date)})"
        lines.append(line)
    for i in installs:
        line = f"Installation request of {_d(i.request_date)}: {i.status}"
        if i.installation_date:
            line += f", installed on {_d(i.installation_date)}"
        else:
            eng = _first_name(db, i.assigned_engineer)
            if eng:
                line += f", engineer {eng} assigned"
        lines.append(line)
    return "Here is what I can see for this number:\n" + "\n".join(lines) + "\nOur team will update you here as it progresses."
