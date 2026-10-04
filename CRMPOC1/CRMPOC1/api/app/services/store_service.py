"""Store rules: unique serials, GRN lifecycle (draft, submit, approve and post) and the stock ledger."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.store import (
    CONDITIONS,
    GRN_SOURCES,
    STOCK_TYPES,
    StoreGrn,
    StoreGrnLine,
    StoreLedger,
    StoreStock,
)
from app.models.user import User

SERIAL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_/.]{2,99}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_serial(value: str | None) -> str:
    return (value or "").strip().upper()


def serial_conflict(db: Session, serial: str | None, *, exclude_grn_id: int | None = None) -> str | None:
    """Return why a serial cannot be received, or None when it is free."""
    s = normalize_serial(serial)
    if not s:
        return None
    if not SERIAL_RE.match(s):
        return f"{s} is not a valid serial. Use letters, numbers, dash, slash or dot (3 to 100 characters)."
    in_stock = db.scalar(select(StoreStock).where(or_(StoreStock.serial_no == s, StoreStock.serial_no_2 == s)))
    if in_stock is not None:
        return f"{s} is already in the store (status {in_stock.status})."
    on_order = db.execute(
        select(OrderItem.id, Order.order_no)
        .join(Order, Order.id == OrderItem.order_id, isouter=True)
        .where(or_(func.upper(OrderItem.serial_no) == s, func.upper(OrderItem.serial_no_2) == s))
    ).first()
    if on_order is not None:
        return f"{s} is already on order {on_order.order_no or on_order.id}. Return or release it first."
    stmt = (
        select(StoreGrn.grn_no)
        .join(StoreGrnLine, StoreGrnLine.grn_id == StoreGrn.id)
        .where(StoreGrn.status != "Posted", or_(StoreGrnLine.serial_no == s, StoreGrnLine.serial_no_2 == s))
    )
    if exclude_grn_id:
        stmt = stmt.where(StoreGrn.id != exclude_grn_id)
    open_grn = db.scalar(stmt)
    if open_grn:
        return f"{s} is already on {open_grn}."
    return None


def _bad(message: str, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(code, message)


def next_grn_no(db: Session) -> str:
    """Continue from the highest number in use (counting rows breaks as soon as a draft is deleted)."""
    highest = 0
    for number in db.scalars(select(StoreGrn.grn_no)):
        try:
            highest = max(highest, int(str(number).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"GRN-{highest + 1:04d}"


def validate_lines(db: Session, lines: list, *, grn_id: int | None = None) -> list[dict]:
    """Check every line and return clean dicts ready to store."""
    if not lines:
        _bad("Add at least one line.")
    clean: list[dict] = []
    seen: dict[str, int] = {}
    for idx, ln in enumerate(lines, start=1):
        label = f"Line {idx}"
        item = db.get(ItemMaster, ln.item_id)
        if item is None or not item.is_active or getattr(item, "deleted_at", None) is not None:
            _bad(f"{label}: item not found or inactive.")
        if ln.stock_type not in STOCK_TYPES:
            _bad(f"{label}: invalid stock type.")
        if ln.condition not in CONDITIONS:
            _bad(f"{label}: invalid condition.")
        need = int(item.serial_count or 0)
        s1, s2 = normalize_serial(ln.serial_no), normalize_serial(ln.serial_no_2)
        qty = int(ln.qty or 1)
        if need == 0:
            if s1 or s2:
                _bad(f"{label}: {item.item_name} is counted by quantity, so no serial number is needed.")
        else:
            if not s1:
                _bad(f"{label}: serial number 1 is required for {item.item_name}.")
            if need >= 2 and not s2:
                _bad(f"{label}: serial number 2 is required for {item.item_name}.")
            if need < 2 and s2:
                _bad(f"{label}: {item.item_name} has only one serial number.")
            if qty != 1:
                _bad(f"{label}: a serial-tracked unit is received one at a time (quantity 1).")
            if s1 and s1 == s2:
                _bad(f"{label}: serial number 1 and 2 must be different.")
        for s in (s1, s2):
            if not s:
                continue
            if s in seen:
                _bad(f"{s} appears twice on this GRN (lines {seen[s]} and {idx}).")
            seen[s] = idx
            if not SERIAL_RE.match(s):
                _bad(f"{label}: {s} is not a valid serial. Use letters, numbers, dash, slash or dot (3 to 100 characters).")
            why = serial_conflict(db, s, exclude_grn_id=grn_id)
            if why:
                _bad(f"{label}: {why}", status.HTTP_409_CONFLICT)
        clean.append(
            dict(
                item_id=item.id,
                stock_type=ln.stock_type,
                serial_no=s1 or None,
                serial_no_2=s2 or None,
                qty=qty,
                unit_cost=ln.unit_cost,
                condition=ln.condition,
                bin_location=(ln.bin_location or "").strip() or None,
            )
        )
    return clean


def _check_header(source_type: str, reference_no: str | None, *, strict: bool) -> None:
    if source_type not in GRN_SOURCES:
        _bad("Invalid GRN source.")
    if strict and not (reference_no or "").strip():
        _bad("Enter the bill, challan or LR number before submitting.")


def _po_header(db: Session, payload) -> tuple[int | None, str | None]:
    """A GRN can name the purchase order it is received against. Returns the PO id and a supplier name to fill in."""
    if not getattr(payload, "po_id", None):
        return None, None
    from app.models.accounts import PurchaseOrder, Supplier

    po = db.get(PurchaseOrder, payload.po_id)
    if po is None:
        _bad("Purchase order not found.", status.HTTP_404_NOT_FOUND)
    if po.status not in ("Approved", "Part received"):
        _bad(f"{po.po_no} is {po.status}. Goods can only be received against an approved purchase order.", status.HTTP_409_CONFLICT)
    if payload.source_type != "Purchase":
        _bad("Only a Purchase GRN can be received against a purchase order.")
    sup = db.get(Supplier, po.supplier_id)
    return po.id, (sup.name if sup else None)


def create_grn(db: Session, user: User, payload) -> StoreGrn:
    _check_header(payload.source_type, payload.reference_no, strict=False)
    lines = validate_lines(db, payload.lines) if payload.lines else []
    po_id, po_supplier = _po_header(db, payload)
    grn = StoreGrn(
        grn_no=next_grn_no(db),
        source_type=payload.source_type,
        po_id=po_id,
        supplier_name=(payload.supplier_name or "").strip() or po_supplier,
        reference_no=(payload.reference_no or "").strip() or None,
        remarks=payload.remarks,
        status="Draft",
        created_by=user.id,
    )
    db.add(grn)
    db.flush()
    for ln in lines:
        db.add(StoreGrnLine(grn_id=grn.id, **ln))
    db.flush()
    return grn


def update_draft(db: Session, grn: StoreGrn, payload) -> StoreGrn:
    if grn.status != "Draft":
        _bad("Only a draft GRN can be edited.", status.HTTP_409_CONFLICT)
    _check_header(payload.source_type, payload.reference_no, strict=False)
    lines = validate_lines(db, payload.lines, grn_id=grn.id) if payload.lines else []
    po_id, po_supplier = _po_header(db, payload)
    grn.source_type = payload.source_type
    grn.po_id = po_id
    grn.supplier_name = (payload.supplier_name or "").strip() or po_supplier
    grn.reference_no = (payload.reference_no or "").strip() or None
    grn.remarks = payload.remarks
    for old in db.scalars(select(StoreGrnLine).where(StoreGrnLine.grn_id == grn.id)):
        db.delete(old)
    db.flush()
    for ln in lines:
        db.add(StoreGrnLine(grn_id=grn.id, **ln))
    db.flush()
    return grn


def submit_grn(db: Session, grn: StoreGrn) -> StoreGrn:
    if grn.status != "Draft":
        _bad("Only a draft GRN can be submitted.", status.HTTP_409_CONFLICT)
    _check_header(grn.source_type, grn.reference_no, strict=True)
    lines = db.scalars(select(StoreGrnLine).where(StoreGrnLine.grn_id == grn.id)).all()
    if not lines:
        _bad("Add at least one line before submitting.")
    # re-check serials: another GRN may have been posted since the draft was saved
    for ln in lines:
        for s in (ln.serial_no, ln.serial_no_2):
            why = serial_conflict(db, s, exclude_grn_id=grn.id)
            if why:
                _bad(why, status.HTTP_409_CONFLICT)
    if grn.po_id:
        from app.services import accounts_service

        accounts_service.check_receipt(db, grn.po_id, lines)
    grn.status = "Pending Approval"
    grn.submitted_at = _now()
    grn.reject_reason = None
    db.flush()
    return grn


def reject_grn(db: Session, grn: StoreGrn, user: User, reason: str) -> StoreGrn:
    if grn.status != "Pending Approval":
        _bad("Only a GRN waiting for approval can be sent back.", status.HTTP_409_CONFLICT)
    grn.status = "Draft"
    grn.reject_reason = f"{reason.strip()} (sent back by {user.name})"
    grn.submitted_at = None
    db.flush()
    return grn


def can_user_approve_own(user: User, grn: StoreGrn) -> bool:
    return (not settings.store_maker_checker) or grn.created_by != user.id


def approve_and_post(db: Session, grn: StoreGrn, user: User) -> StoreGrn:
    if grn.status != "Pending Approval":
        _bad("Only a GRN waiting for approval can be approved.", status.HTTP_409_CONFLICT)
    if not can_user_approve_own(user, grn):
        _bad("You created this GRN, so someone else must approve it.", status.HTTP_403_FORBIDDEN)
    lines = db.scalars(select(StoreGrnLine).where(StoreGrnLine.grn_id == grn.id).order_by(StoreGrnLine.id)).all()
    for ln in lines:
        for s in (ln.serial_no, ln.serial_no_2):
            why = serial_conflict(db, s, exclude_grn_id=grn.id)
            if why:
                _bad(why, status.HTTP_409_CONFLICT)
    po = None
    if grn.po_id:
        from app.services import accounts_service

        po = accounts_service.check_receipt(db, grn.po_id, lines, posting=True)
    now = _now()
    for ln in lines:
        stock = StoreStock(
            item_id=ln.item_id,
            grn_line_id=ln.id,
            grn_id=grn.id,
            serial_no=ln.serial_no,
            serial_no_2=ln.serial_no_2,
            stock_type=ln.stock_type,
            condition=ln.condition,
            status="Available" if ln.condition == "OK" else "Quarantine",
            qty=ln.qty,
            unit_cost=ln.unit_cost,
            bin_location=ln.bin_location,
            received_at=now,
        )
        db.add(stock)
        db.flush()
        db.add(
            StoreLedger(
                doc_type="GRN",
                doc_no=grn.grn_no,
                item_id=ln.item_id,
                stock_id=stock.id,
                serial_no=ln.serial_no,
                qty_in=ln.qty,
                stock_type=ln.stock_type,
                note=f"{grn.source_type} {grn.reference_no or ''}".strip(),
                by_user_id=user.id,
            )
        )
    grn.status = "Posted"
    grn.approved_by = user.id
    grn.approved_at = now
    db.flush()
    if po is not None:
        from app.services import accounts_service

        accounts_service.apply_receipt(db, po, lines)
    return grn
