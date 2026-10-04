"""Accounts rules: suppliers, BOM and cost roll-up, assembly orders, purchase orders and the GRN link."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.accounts import (
    AssemblyOrder,
    AssemblyPart,
    Bom,
    BomLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from app.models.item_master import ItemMaster
from app.models.store import StoreLedger, StoreStock
from app.models.user import User
from app.services.gst_service import GSTINValidator
from app.services.store_service import SERIAL_RE, normalize_serial, serial_conflict

TWO = Decimal("0.01")
USABLE_TYPES = ("Fresh", "Spare")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bad(message: str, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(code, message)


def q2(value) -> Decimal:
    return Decimal(value).quantize(TWO, rounding=ROUND_HALF_UP)


def _name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    u = db.get(User, user_id)
    return u.name if u else None


# ---------------------------------------------------------------------------
# State and GST helpers
# ---------------------------------------------------------------------------
def state_code_for(name: str | None) -> str | None:
    wanted = (name or "").strip().lower()
    if not wanted:
        return None
    for code, label in GSTINValidator.STATE_CODES.items():
        if label.lower() == wanted:
            return code
    return None


def company_state_code() -> str | None:
    return state_code_for(settings.company_state)


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
def apply_supplier(db: Session, supplier: Supplier, body) -> Supplier:
    gstin = (body.gstin or "").strip().upper() or None
    if gstin:
        fmt = GSTINValidator().validate_format(gstin)
        if not fmt["valid"]:
            _bad(f"GSTIN: {fmt['error']}")
        dup = db.scalar(select(Supplier).where(Supplier.gstin == gstin, Supplier.id != (supplier.id or 0)))
        if dup is not None:
            _bad(f"{dup.name} already uses this GSTIN.", status.HTTP_409_CONFLICT)
        supplier.gstin = gstin
        supplier.pan = fmt["pan"]
        supplier.state_code = fmt["state_code"]
        supplier.state = fmt["state"]
    else:
        code = state_code_for(body.state)
        if not code:
            _bad("Choose the supplier's state. It decides whether GST is CGST+SGST or IGST.")
        supplier.gstin = None
        supplier.pan = None
        supplier.state_code = code
        supplier.state = GSTINValidator.STATE_CODES[code]
    for field in (
        "name", "address", "city", "pincode", "contact_name", "phone", "email", "is_msme", "msme_no",
        "payment_terms_days", "bank_name", "bank_account", "bank_ifsc", "is_active",
    ):
        value = getattr(body, field)
        if isinstance(value, str):
            value = value.strip() or None
        setattr(supplier, field, value)
    if body.is_msme is False:
        supplier.msme_no = None
    if supplier.bank_ifsc:
        supplier.bank_ifsc = supplier.bank_ifsc.upper()
    return supplier


# ---------------------------------------------------------------------------
# Costs and stock figures used by BOM and PO screens
# ---------------------------------------------------------------------------
def in_store_qty(db: Session, item_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(StoreStock.qty), 0)).where(
                StoreStock.item_id == item_id,
                StoreStock.status == "Available",
                StoreStock.condition == "OK",
                StoreStock.stock_type.in_(USABLE_TYPES),
            )
        )
        or 0
    )


def latest_po_rate(db: Session, item_id: int) -> Decimal | None:
    row = db.execute(
        select(PurchaseOrderLine.rate)
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.po_id)
        .where(PurchaseOrderLine.item_id == item_id, PurchaseOrder.status.in_(("Approved", "Part received", "Received")))
        .order_by(PurchaseOrder.id.desc())
        .limit(1)
    ).first()
    return Decimal(row[0]) if row else None


def unit_cost_of(db: Session, item_id: int) -> Decimal | None:
    """What one unit costs us: the average of what is on the shelf, else the last approved PO rate."""
    row = db.execute(
        select(
            func.coalesce(func.sum(StoreStock.qty * StoreStock.unit_cost), 0),
            func.coalesce(func.sum(StoreStock.qty), 0),
        ).where(
            StoreStock.item_id == item_id,
            StoreStock.status == "Available",
            StoreStock.unit_cost.is_not(None),
        )
    ).first()
    if row and row[1]:
        return q2(Decimal(row[0]) / Decimal(row[1]))
    return latest_po_rate(db, item_id)


def per_unit_need(line: BomLine) -> Decimal:
    return Decimal(line.qty) * (Decimal(1) + Decimal(line.scrap_pct or 0) / Decimal(100))


# ---------------------------------------------------------------------------
# BOM
# ---------------------------------------------------------------------------
def _active_or_latest_bom(db: Session, item_id: int) -> Bom | None:
    return db.scalar(
        select(Bom).where(Bom.item_id == item_id, Bom.status != "Retired").order_by(Bom.status.asc(), Bom.version.desc()).limit(1)
    )


def _would_loop(db: Session, finished_id: int, component_id: int, seen: set[int] | None = None) -> bool:
    seen = seen or set()
    if component_id == finished_id:
        return True
    if component_id in seen:
        return False
    seen.add(component_id)
    bom = _active_or_latest_bom(db, component_id)
    if bom is None:
        return False
    for ln in db.scalars(select(BomLine).where(BomLine.bom_id == bom.id)):
        if _would_loop(db, finished_id, ln.component_item_id, seen):
            return True
    return False


def _check_bom_item(db: Session, item_id: int | None) -> ItemMaster:
    item = db.get(ItemMaster, item_id) if item_id else None
    if item is None or getattr(item, "deleted_at", None) is not None:
        _bad("Item not found.", status.HTTP_404_NOT_FOUND)
    if (item.source or "Buy") == "Buy":
        _bad(f"{item.item_name} is set to Buy. Change its source to Make or Both on the item before adding a BOM.", status.HTTP_409_CONFLICT)
    return item


def _clean_bom_lines(db: Session, item: ItemMaster, lines: list) -> list[dict]:
    if not lines:
        return []
    seen: set[int] = set()
    clean = []
    for idx, ln in enumerate(lines, start=1):
        comp = db.get(ItemMaster, ln.component_item_id)
        if comp is None or getattr(comp, "deleted_at", None) is not None or not comp.is_active:
            _bad(f"Line {idx}: component not found or inactive.")
        if comp.id == item.id:
            _bad(f"Line {idx}: an item cannot be a component of itself.")
        if comp.id in seen:
            _bad(f"Line {idx}: {comp.item_name} is already on this BOM.")
        seen.add(comp.id)
        if _would_loop(db, item.id, comp.id):
            _bad(f"Line {idx}: {comp.item_name} already contains {item.item_name} in its own BOM, so this would go round in a circle.")
        clean.append(dict(component_item_id=comp.id, qty=Decimal(ln.qty), scrap_pct=Decimal(ln.scrap_pct or 0), note=(ln.note or "").strip() or None))
    return clean


def create_bom(db: Session, user: User, body) -> Bom:
    item = _check_bom_item(db, body.item_id)
    lines = _clean_bom_lines(db, item, body.lines)
    version = (db.scalar(select(func.max(Bom.version)).where(Bom.item_id == item.id)) or 0) + 1
    bom = Bom(
        item_id=item.id, version=version, status="Draft", notes=body.notes, labour_cost=body.labour_cost,
        overhead_cost=body.overhead_cost, created_by=user.id,
    )
    db.add(bom)
    db.flush()
    for ln in lines:
        db.add(BomLine(bom_id=bom.id, **ln))
    db.flush()
    return bom


def update_bom_draft(db: Session, bom: Bom, body) -> Bom:
    if bom.status != "Draft":
        _bad("Only a draft BOM can be edited. Make a new version instead.", status.HTTP_409_CONFLICT)
    item = db.get(ItemMaster, bom.item_id)
    lines = _clean_bom_lines(db, item, body.lines)
    bom.notes = body.notes
    bom.labour_cost = body.labour_cost
    bom.overhead_cost = body.overhead_cost
    for old in db.scalars(select(BomLine).where(BomLine.bom_id == bom.id)):
        db.delete(old)
    db.flush()
    for ln in lines:
        db.add(BomLine(bom_id=bom.id, **ln))
    db.flush()
    return bom


def copy_bom(db: Session, user: User, bom: Bom) -> Bom:
    version = (db.scalar(select(func.max(Bom.version)).where(Bom.item_id == bom.item_id)) or 0) + 1
    new = Bom(
        item_id=bom.item_id, version=version, status="Draft", notes=bom.notes, labour_cost=bom.labour_cost,
        overhead_cost=bom.overhead_cost, created_by=user.id,
    )
    db.add(new)
    db.flush()
    for ln in db.scalars(select(BomLine).where(BomLine.bom_id == bom.id).order_by(BomLine.id)):
        db.add(BomLine(bom_id=new.id, component_item_id=ln.component_item_id, qty=ln.qty, scrap_pct=ln.scrap_pct, note=ln.note))
    db.flush()
    return new


def activate_bom(db: Session, user: User, bom: Bom) -> Bom:
    if bom.status != "Draft":
        _bad("Only a draft BOM can be activated.", status.HTTP_409_CONFLICT)
    if not db.scalars(select(BomLine.id).where(BomLine.bom_id == bom.id)).first():
        _bad("Add at least one component before activating the BOM.")
    for old in db.scalars(select(Bom).where(Bom.item_id == bom.item_id, Bom.status == "Active")):
        old.status = "Retired"
    bom.status = "Active"
    bom.activated_by = user.id
    bom.activated_at = _now()
    db.flush()
    return bom


def bom_lines(db: Session, bom: Bom) -> list[BomLine]:
    return list(db.scalars(select(BomLine).where(BomLine.bom_id == bom.id).order_by(BomLine.id)).all())


def bom_costing(db: Session, bom: Bom) -> dict:
    """Material cost per unit, whether every component had a known cost, and how many units the shelf can build."""
    rows = []
    material = Decimal(0)
    complete = True
    can_build: int | None = None
    for ln in bom_lines(db, bom):
        comp = db.get(ItemMaster, ln.component_item_id)
        need = per_unit_need(ln)
        cost = unit_cost_of(db, ln.component_item_id)
        have = in_store_qty(db, ln.component_item_id)
        line_cost = q2(cost * need) if cost is not None else None
        if line_cost is None:
            complete = False
        else:
            material += line_cost
        buildable = int(math.floor(Decimal(have) / need)) if need > 0 else 0
        can_build = buildable if can_build is None else min(can_build, buildable)
        rows.append((ln, comp, cost, line_cost, have, buildable))
    return {
        "rows": rows,
        "material": q2(material) if rows else None,
        "complete": complete,
        "unit": q2(material + Decimal(bom.labour_cost or 0) + Decimal(bom.overhead_cost or 0)) if rows else None,
        "can_build": can_build or 0,
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def next_asm_no(db: Session) -> str:
    highest = 0
    for number in db.scalars(select(AssemblyOrder.asm_no)):
        try:
            highest = max(highest, int(str(number).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"ASM-{highest + 1:04d}"


def active_bom(db: Session, item_id: int) -> Bom | None:
    return db.scalar(select(Bom).where(Bom.item_id == item_id, Bom.status == "Active"))


def create_assembly(db: Session, user: User, body) -> AssemblyOrder:
    item = _check_bom_item(db, body.item_id)
    bom = active_bom(db, item.id)
    if bom is None:
        _bad(f"{item.item_name} has no active BOM. Activate one first.", status.HTTP_409_CONFLICT)
    asm = AssemblyOrder(
        asm_no=next_asm_no(db), item_id=item.id, bom_id=bom.id, qty=body.qty, status="Planned",
        remarks=(body.remarks or "").strip() or None, created_by=user.id,
    )
    db.add(asm)
    db.flush()
    return asm


def assembly_needs(db: Session, asm: AssemblyOrder) -> list[dict]:
    bom = db.get(Bom, asm.bom_id)
    out = []
    for ln in bom_lines(db, bom):
        comp = db.get(ItemMaster, ln.component_item_id)
        needed = int(math.ceil(per_unit_need(ln) * asm.qty))
        have = in_store_qty(db, ln.component_item_id)
        out.append(
            dict(component_item_id=comp.id, item_code=comp.item_code, item_name=comp.item_name, needed=needed, in_store=have, short=max(0, needed - have))
        )
    return out


def cancel_assembly(db: Session, asm: AssemblyOrder) -> AssemblyOrder:
    if asm.status != "Planned":
        _bad("Only a planned assembly can be cancelled.", status.HTTP_409_CONFLICT)
    asm.status = "Cancelled"
    db.flush()
    return asm


def _check_units(db: Session, item: ItemMaster, qty: int, units: list) -> list[tuple[str | None, str | None]]:
    need = int(item.serial_count or 0)
    if need == 0:
        return []
    if len(units) != qty:
        _bad(f"Enter serial numbers for all {qty} unit(s). You gave {len(units)}.")
    seen: set[str] = set()
    clean = []
    for idx, u in enumerate(units, start=1):
        s1, s2 = normalize_serial(u.serial_no), normalize_serial(u.serial_no_2)
        label = f"Unit {idx}"
        if not s1:
            _bad(f"{label}: serial number 1 is required.")
        if need >= 2 and not s2:
            _bad(f"{label}: serial number 2 is required.")
        if need < 2 and s2:
            _bad(f"{label}: {item.item_name} has only one serial number.")
        if s1 and s1 == s2:
            _bad(f"{label}: serial number 1 and 2 must be different.")
        for s in (s1, s2):
            if not s:
                continue
            if not SERIAL_RE.match(s):
                _bad(f"{label}: {s} is not a valid serial. Use letters, numbers, dash, slash or dot (3 to 100 characters).")
            if s in seen:
                _bad(f"{s} appears twice in this assembly.")
            seen.add(s)
            why = serial_conflict(db, s)
            if why:
                _bad(f"{label}: {why}", status.HTTP_409_CONFLICT)
        clean.append((s1, s2 or None))
    return clean


def complete_assembly(db: Session, user: User, asm: AssemblyOrder, units: list) -> AssemblyOrder:
    if asm.status != "Planned":
        _bad("Only a planned assembly can be completed.", status.HTTP_409_CONFLICT)
    item = db.get(ItemMaster, asm.item_id)
    bom = db.get(Bom, asm.bom_id)
    clean_units = _check_units(db, item, asm.qty, units)

    lines = bom_lines(db, bom)
    shortages = [n for n in assembly_needs(db, asm) if n["short"] > 0]
    if shortages:
        text = ", ".join(f"{n['item_name']} short {n['short']}" for n in shortages)
        _bad(f"Not enough components in the store: {text}.", status.HTTP_409_CONFLICT)

    now = _now()
    material_total = Decimal(0)
    costs_known = True
    parts: list[tuple[BomLine, StoreStock, int]] = []
    for ln in lines:
        need_left = int(math.ceil(per_unit_need(ln) * asm.qty))
        rows = db.scalars(
            select(StoreStock)
            .where(
                StoreStock.item_id == ln.component_item_id,
                StoreStock.status == "Available",
                StoreStock.condition == "OK",
                StoreStock.stock_type.in_(USABLE_TYPES),
            )
            .order_by(StoreStock.received_at.asc(), StoreStock.id.asc())
        ).all()
        for row in rows:
            if need_left <= 0:
                break
            take = min(need_left, row.qty)
            if take == row.qty:
                issued = row
            else:
                row.qty -= take
                issued = StoreStock(
                    item_id=row.item_id, grn_line_id=row.grn_line_id, grn_id=row.grn_id, stock_type=row.stock_type,
                    condition=row.condition, qty=take, unit_cost=row.unit_cost, bin_location=row.bin_location,
                    received_at=row.received_at,
                )
                db.add(issued)
            issued.status = "Issued"
            issued.issued_at = now
            db.flush()
            db.add(
                StoreLedger(
                    doc_type="ASM", doc_no=asm.asm_no, item_id=issued.item_id, stock_id=issued.id, serial_no=issued.serial_no,
                    qty_out=take, stock_type=issued.stock_type, note=f"Used to build {item.item_code}", by_user_id=user.id,
                )
            )
            if issued.unit_cost is None:
                costs_known = False
            else:
                material_total += Decimal(issued.unit_cost) * take
            parts.append((ln, issued, take))
            need_left -= take

    per_unit_cost = None
    if costs_known:
        per_unit_cost = q2(material_total / asm.qty + Decimal(bom.labour_cost or 0) + Decimal(bom.overhead_cost or 0))

    serial_slots: dict[int, int] = {}
    for ln, issued, take in parts:
        per_unit = max(1, int(math.ceil(Decimal(ln.qty))))
        finished_serial = None
        if issued.serial_no:
            idx = serial_slots.get(ln.id, 0)
            serial_slots[ln.id] = idx + 1
            unit_idx = idx // per_unit
            if clean_units and unit_idx < len(clean_units):
                finished_serial = clean_units[unit_idx][0]
        db.add(
            AssemblyPart(
                assembly_id=asm.id, finished_serial=finished_serial, component_item_id=issued.item_id,
                component_serial=issued.serial_no, qty=take, unit_cost=issued.unit_cost,
            )
        )

    if clean_units:
        for s1, s2 in clean_units:
            st = StoreStock(
                item_id=item.id, serial_no=s1, serial_no_2=s2, stock_type="Fresh", condition="OK", status="Available",
                qty=1, unit_cost=per_unit_cost, received_at=now,
            )
            db.add(st)
            db.flush()
            db.add(
                StoreLedger(
                    doc_type="ASM", doc_no=asm.asm_no, item_id=item.id, stock_id=st.id, serial_no=s1, qty_in=1,
                    stock_type="Fresh", note=f"Built from BOM v{bom.version}", by_user_id=user.id,
                )
            )
    else:
        st = StoreStock(
            item_id=item.id, stock_type="Fresh", condition="OK", status="Available", qty=asm.qty, unit_cost=per_unit_cost, received_at=now,
        )
        db.add(st)
        db.flush()
        db.add(
            StoreLedger(
                doc_type="ASM", doc_no=asm.asm_no, item_id=item.id, stock_id=st.id, qty_in=asm.qty, stock_type="Fresh",
                note=f"Built from BOM v{bom.version}", by_user_id=user.id,
            )
        )
    asm.status = "Completed"
    asm.completed_by = user.id
    asm.completed_at = now
    db.flush()
    return asm


# ---------------------------------------------------------------------------
# Purchase orders
# ---------------------------------------------------------------------------
def fy_prefix(on: date) -> str:
    start = on.year if on.month >= 4 else on.year - 1
    return f"PO/{start % 100:02d}-{(start + 1) % 100:02d}/"


def next_po_no(db: Session, on: date) -> str:
    prefix = fy_prefix(on)
    highest = 0
    for number in db.scalars(select(PurchaseOrder.po_no).where(PurchaseOrder.po_no.like(f"{prefix}%"))):
        try:
            highest = max(highest, int(str(number).rsplit("/", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"{prefix}{highest + 1:04d}"


def _load_supplier(db: Session, supplier_id: int) -> Supplier:
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        _bad("Supplier not found.", status.HTTP_404_NOT_FOUND)
    if not sup.is_active:
        _bad(f"{sup.name} is not active. Pick another supplier.")
    return sup


def _price_lines(db: Session, lines: list, intra: bool) -> tuple[list[dict], dict]:
    clean = []
    taxable_sum = cgst = sgst = igst = Decimal(0)
    for idx, ln in enumerate(lines, start=1):
        item = db.get(ItemMaster, ln.item_id)
        if item is None or getattr(item, "deleted_at", None) is not None or not item.is_active:
            _bad(f"Line {idx}: item not found or inactive.")
        rate = q2(ln.rate)
        gst = Decimal(ln.gst_rate) if ln.gst_rate is not None else (Decimal(item.gst_rate) if item.gst_rate is not None else Decimal(18))
        taxable = q2(rate * ln.qty)
        tax = q2(taxable * gst / Decimal(100))
        taxable_sum += taxable
        if intra:
            half = q2(tax / 2)
            cgst += half
            sgst += tax - half
        else:
            igst += tax
        clean.append(dict(item_id=item.id, description=item.item_name, hsn_code=item.hsn_code, qty=ln.qty, rate=rate, gst_rate=gst, taxable=taxable))
    totals = dict(taxable_value=q2(taxable_sum), cgst=q2(cgst), sgst=q2(sgst), igst=q2(igst))
    totals["total"] = q2(totals["taxable_value"] + totals["cgst"] + totals["sgst"] + totals["igst"])
    return clean, totals


def _apply_po(db: Session, po: PurchaseOrder, body) -> None:
    sup = _load_supplier(db, body.supplier_id)
    intra = bool(sup.state_code) and sup.state_code == company_state_code()
    clean, totals = _price_lines(db, body.lines, intra)
    po.supplier_id = sup.id
    po.po_date = body.po_date or po.po_date or date.today()
    po.expected_date = body.expected_date
    po.payment_terms_days = body.payment_terms_days if body.payment_terms_days is not None else sup.payment_terms_days
    po.terms = (body.terms or "").strip() or None
    po.remarks = (body.remarks or "").strip() or None
    po.place_of_supply = sup.state
    po.intra_state = intra
    for k, v in totals.items():
        setattr(po, k, v)
    if po.id:
        for old in db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id)):
            db.delete(old)
        db.flush()
    else:
        db.add(po)
        db.flush()
    for ln in clean:
        db.add(PurchaseOrderLine(po_id=po.id, **ln))
    db.flush()


def create_po(db: Session, user: User, body) -> PurchaseOrder:
    on = body.po_date or date.today()
    po = PurchaseOrder(po_no=next_po_no(db, on), po_date=on, supplier_id=body.supplier_id, status="Draft", created_by=user.id)
    _apply_po(db, po, body)
    return po


def update_po_draft(db: Session, po: PurchaseOrder, body) -> PurchaseOrder:
    if po.status != "Draft":
        _bad("Only a draft purchase order can be edited.", status.HTTP_409_CONFLICT)
    _apply_po(db, po, body)
    return po


def po_lines(db: Session, po: PurchaseOrder) -> list[PurchaseOrderLine]:
    return list(db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id).order_by(PurchaseOrderLine.id)).all())


def submit_po(db: Session, po: PurchaseOrder) -> PurchaseOrder:
    if po.status != "Draft":
        _bad("Only a draft purchase order can be submitted.", status.HTTP_409_CONFLICT)
    lines = po_lines(db, po)
    if not lines:
        _bad("Add at least one line before submitting.")
    if any(Decimal(ln.rate) <= 0 for ln in lines):
        _bad("Enter a rate for every line before submitting.")
    po.status = "Pending Approval"
    po.submitted_at = _now()
    po.reject_reason = None
    db.flush()
    return po


def can_approve_own(user: User, po: PurchaseOrder) -> bool:
    return (not settings.acc_maker_checker) or po.created_by != user.id


def approve_po(db: Session, po: PurchaseOrder, user: User) -> PurchaseOrder:
    if po.status != "Pending Approval":
        _bad("Only a purchase order waiting for approval can be approved.", status.HTTP_409_CONFLICT)
    if not can_approve_own(user, po):
        _bad("You raised this purchase order, so someone else must approve it.", status.HTTP_403_FORBIDDEN)
    po.status = "Approved"
    po.approved_by = user.id
    po.approved_at = _now()
    db.flush()
    return po


def reject_po(db: Session, po: PurchaseOrder, user: User, reason: str) -> PurchaseOrder:
    if po.status != "Pending Approval":
        _bad("Only a purchase order waiting for approval can be sent back.", status.HTTP_409_CONFLICT)
    po.status = "Draft"
    po.reject_reason = f"{reason.strip()} (sent back by {user.name})"
    po.submitted_at = None
    db.flush()
    return po


def cancel_po(db: Session, po: PurchaseOrder, reason: str) -> PurchaseOrder:
    if po.status in ("Cancelled", "Received"):
        _bad(f"A {po.status.lower()} purchase order cannot be cancelled.", status.HTTP_409_CONFLICT)
    if any(ln.received_qty for ln in po_lines(db, po)):
        _bad("Goods have already been received against this purchase order.", status.HTTP_409_CONFLICT)
    po.status = "Cancelled"
    po.remarks = f"{po.remarks + chr(10) if po.remarks else ''}Cancelled: {reason.strip()}"
    db.flush()
    return po


def outstanding_by_item(db: Session, po: PurchaseOrder) -> dict[int, int]:
    out: dict[int, int] = {}
    for ln in po_lines(db, po):
        out[ln.item_id] = out.get(ln.item_id, 0) + max(0, ln.qty - ln.received_qty)
    return out


def check_receipt(db: Session, po_id: int, grn_lines: list, *, posting: bool = False) -> PurchaseOrder:
    """A GRN against a PO may only bring items on that PO, and no more than is still outstanding."""
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        _bad("Purchase order not found.", status.HTTP_404_NOT_FOUND)
    if po.status not in ("Approved", "Part received"):
        _bad(f"{po.po_no} is {po.status}. Goods can only be received against an approved purchase order.", status.HTTP_409_CONFLICT)
    outstanding = outstanding_by_item(db, po)
    wanted: dict[int, int] = {}
    for ln in grn_lines:
        wanted[ln.item_id] = wanted.get(ln.item_id, 0) + int(ln.qty or 1)
    for item_id, qty in wanted.items():
        if item_id not in outstanding:
            item = db.get(ItemMaster, item_id)
            _bad(f"{item.item_name if item else item_id} is not on {po.po_no}.", status.HTTP_409_CONFLICT)
        if qty > outstanding[item_id]:
            item = db.get(ItemMaster, item_id)
            _bad(f"{item.item_name}: {qty} received but only {outstanding[item_id]} still outstanding on {po.po_no}.", status.HTTP_409_CONFLICT)
    return po


def po_rate_for(db: Session, po: PurchaseOrder, item_id: int) -> Decimal | None:
    """The price we agreed on the PO, used as the cost of stock received against it when the GRN has none."""
    for ln in po_lines(db, po):
        if ln.item_id == item_id:
            return Decimal(ln.rate)
    return None


def apply_receipt(db: Session, po: PurchaseOrder, grn_lines: list) -> None:
    wanted: dict[int, int] = {}
    for ln in grn_lines:
        wanted[ln.item_id] = wanted.get(ln.item_id, 0) + int(ln.qty or 1)
    for ln in po_lines(db, po):
        left = wanted.get(ln.item_id, 0)
        if left <= 0:
            continue
        take = min(left, max(0, ln.qty - ln.received_qty))
        ln.received_qty += take
        wanted[ln.item_id] = left - take
    db.flush()
    po.status = "Received" if all(ln.received_qty >= ln.qty for ln in po_lines(db, po)) else "Part received"
    db.flush()
