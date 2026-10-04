"""Store dispatch rules: reserve oldest stock for an order, hold dispatch until the bill number is on the order,
check every serial by scan, then issue the units and write the serials onto the order lines."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.courier import Courier
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.store import StoreDispatch, StoreLedger, StoreStock
from app.models.user import User
from app.services.serial_history import EVENT_TYPES, create_serial_history_event
from app.services.store_service import normalize_serial

STAGES = ("Needs stock", "Waiting for bill", "Ready to dispatch", "Dispatched")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bad(message: str, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(code, message)


def order_lines(db: Session, order: Order) -> list[OrderItem]:
    return list(db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)).all())


def held_units(db: Session, order: Order) -> dict[int, StoreStock]:
    """Map order_item_id to the unit held for it (Reserved) or already sent out for it (Issued)."""
    ids = [ln.id for ln in order_lines(db, order)]
    if not ids:
        return {}
    rows = db.scalars(
        select(StoreStock).where(StoreStock.order_item_id.in_(ids), StoreStock.status.in_(("Reserved", "Issued")))
    ).all()
    return {r.order_item_id: r for r in rows}


def order_stage(db: Session, order: Order) -> str:
    lines = order_lines(db, order)
    units = held_units(db, order)
    if lines and all(u.status == "Issued" for u in units.values()) and len(units) == len(lines):
        return "Dispatched"
    if len(units) < len(lines):
        return "Needs stock"
    if not (order.oem_bill_no or "").strip():
        return "Waiting for bill"
    return "Ready to dispatch"


def _need_store_order(order: Order) -> None:
    if order.fulfilment != "Store":
        _bad("This order is shipped by its vendor, not from our store.", status.HTTP_409_CONFLICT)
    if order.deleted_at is not None:
        _bad("Order not found.", status.HTTP_404_NOT_FOUND)


def check_can_change_fulfilment(db: Session, order: Order) -> None:
    if order.status != "Pending":
        _bad("The fulfilment mode can only change while the order is Pending.", status.HTTP_409_CONFLICT)
    if held_units(db, order):
        _bad("Release the reserved stock before changing the fulfilment mode.", status.HTTP_409_CONFLICT)
    if any((ln.serial_no or ln.serial_no_2) for ln in order_lines(db, order)):
        _bad("This order already has serial numbers, so its fulfilment mode cannot change.", status.HTTP_409_CONFLICT)


def _split_one(db: Session, row: StoreStock) -> StoreStock:
    """Take one unit out of a quantity batch. A batch of one is used as it is."""
    if row.qty <= 1:
        return row
    row.qty -= 1
    one = StoreStock(
        item_id=row.item_id,
        grn_line_id=row.grn_line_id,
        grn_id=row.grn_id,
        stock_type=row.stock_type,
        condition=row.condition,
        status="Available",
        qty=1,
        unit_cost=row.unit_cost,
        bin_location=row.bin_location,
        received_at=row.received_at,
    )
    db.add(one)
    db.flush()
    return one


def reserve_order(db: Session, order: Order, user: User) -> dict:
    """Hold the oldest finished units for every line that has none yet. Returns what is still short."""
    _need_store_order(order)
    if order.status != "Pending":
        _bad("Stock can only be reserved while the order is Pending.", status.HTTP_409_CONFLICT)
    held = held_units(db, order)
    now = _now()
    reserved = 0
    short: dict[int, int] = {}
    for ln in order_lines(db, order):
        if ln.id in held:
            continue
        if ln.item_id is None:
            _bad("An order line has no item, so stock cannot be reserved for it.")
        row = db.scalars(
            select(StoreStock)
            .where(
                StoreStock.item_id == ln.item_id,
                StoreStock.stock_type == "Fresh",
                StoreStock.condition == "OK",
                StoreStock.status == "Available",
                StoreStock.order_item_id.is_(None),
            )
            .order_by(StoreStock.received_at.asc(), StoreStock.id.asc())
            .limit(1)
        ).first()
        if row is None:
            short[ln.item_id] = short.get(ln.item_id, 0) + 1
            continue
        row = _split_one(db, row)
        row.status = "Reserved"
        row.order_item_id = ln.id
        row.reserved_at = now
        reserved += 1
        db.flush()  # autoflush is off, so the next line must not be handed this same unit
    db.flush()
    shortages = []
    for item_id, missing in short.items():
        item = db.get(ItemMaster, item_id)
        shortages.append({"item_id": item_id, "item_code": item.item_code if item else None, "item_name": item.item_name if item else None, "missing": missing})
    return {"reserved": reserved, "short": shortages}


def release_order(db: Session, order: Order, user: User) -> int:
    """Put every unit that is only reserved (not yet sent out) back on the shelf."""
    ids = [ln.id for ln in order_lines(db, order)]
    if not ids:
        return 0
    rows = db.scalars(select(StoreStock).where(StoreStock.order_item_id.in_(ids), StoreStock.status == "Reserved")).all()
    for r in rows:
        r.status = "Available"
        r.order_item_id = None
        r.reserved_at = None
    db.flush()
    return len(rows)


def next_dispatch_no(db: Session) -> str:
    highest = 0
    for number in db.scalars(select(StoreDispatch.dispatch_no)):
        try:
            highest = max(highest, int(str(number).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"DSP-{highest + 1:04d}"


def dispatch_order(db: Session, order: Order, user: User, *, scans: list[str], courier_id: int | None, lrn_no: str | None, remarks: str | None) -> StoreDispatch:
    _need_store_order(order)
    if order.status != "Pending":
        _bad("Only a Pending order can be dispatched.", status.HTTP_409_CONFLICT)
    bill = (order.oem_bill_no or "").strip()
    if not bill:
        _bad("No bill number, no issue. Enter the bill or invoice number on the order first.", status.HTTP_409_CONFLICT)
    lines = order_lines(db, order)
    if not lines:
        _bad("This order has no lines.")
    units = held_units(db, order)
    missing = [ln for ln in lines if ln.id not in units]
    if missing:
        _bad(f"{len(missing)} line(s) have no reserved stock yet. Reserve stock first.", status.HTTP_409_CONFLICT)
    if any(u.status == "Issued" for u in units.values()):
        _bad("This order has already been dispatched.", status.HTTP_409_CONFLICT)

    lrn = (lrn_no or "").strip()
    if not courier_id or not lrn:
        _bad("Choose the courier and enter the LR number.")
    courier = db.get(Courier, courier_id)
    if courier is None or courier.deleted_at is not None:
        _bad("Courier not found.")

    scanned = {normalize_serial(s) for s in scans if normalize_serial(s)}
    expected: dict[str, int] = {}
    for ln in lines:
        u = units[ln.id]
        for s in (u.serial_no, u.serial_no_2):
            if s:
                expected[normalize_serial(s)] = ln.id
    stray = sorted(s for s in scanned if s not in expected)
    if stray:
        _bad(f"{', '.join(stray)} is not reserved for this order.", status.HTTP_409_CONFLICT)
    not_scanned = []
    for ln in lines:
        u = units[ln.id]
        serials = [normalize_serial(s) for s in (u.serial_no, u.serial_no_2) if s]
        if serials and not (set(serials) & scanned):
            not_scanned.append(serials[0])
    if not_scanned:
        _bad(f"Scan every unit before dispatch. Not scanned yet: {', '.join(not_scanned)}.", status.HTTP_409_CONFLICT)

    now = _now()
    dsp = StoreDispatch(
        dispatch_no=next_dispatch_no(db),
        order_id=order.id,
        bill_no=bill,
        courier_id=courier.id,
        lrn_no=lrn,
        remarks=(remarks or "").strip() or None,
        dispatched_by=user.id,
        dispatched_at=now,
    )
    db.add(dsp)
    db.flush()
    for ln in lines:
        u = units[ln.id]
        u.status = "Issued"
        u.issued_at = now
        u.dispatch_id = dsp.id
        db.add(
            StoreLedger(
                doc_type="DSP",
                doc_no=dsp.dispatch_no,
                item_id=u.item_id,
                stock_id=u.id,
                serial_no=u.serial_no,
                qty_out=u.qty,
                stock_type=u.stock_type,
                note=f"Order {order.order_no or order.id}, bill {bill}",
                by_user_id=user.id,
            )
        )
        if u.serial_no:
            ln.serial_no = u.serial_no
            ln.serial_no_2 = u.serial_no_2
            create_serial_history_event(
                db,
                serial_no=u.serial_no,
                serial_no_2=u.serial_no_2,
                order_item_id=ln.id,
                event_type=EVENT_TYPES["ORDER"],
                event_subtype="STORE_DISPATCHED",
                event_at=now,
                performed_by_user_id=user.id,
                performed_by_name=user.name,
                source_table="store_dispatches",
                source_id=dsp.id,
                title="Dispatched from store",
                description=f"{dsp.dispatch_no} against bill {bill}, order {order.order_no or order.id}.",
                metadata={"dispatch_no": dsp.dispatch_no, "bill_no": bill, "lrn_no": lrn, "order_no": order.order_no},
            )
    order.status = "Shipped"
    order.courier_id = courier.id
    order.lrn_no = lrn
    db.flush()
    return dsp


def count_by_stage(db: Session) -> dict[str, int]:
    out = {s: 0 for s in STAGES}
    for order in db.scalars(
        select(Order).where(Order.fulfilment == "Store", Order.deleted_at.is_(None), Order.status.notin_(("Cancelled",)))
    ).all():
        out[order_stage(db, order)] += 1
    return out


def free_stock_by_item(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(StoreStock.item_id, func.coalesce(func.sum(StoreStock.qty), 0))
        .where(StoreStock.status == "Available", StoreStock.stock_type == "Fresh", StoreStock.condition == "OK")
        .group_by(StoreStock.item_id)
    ).all()
    return {r[0]: int(r[1]) for r in rows}
