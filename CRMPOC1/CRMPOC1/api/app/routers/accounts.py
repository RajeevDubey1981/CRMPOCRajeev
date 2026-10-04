from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
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
from app.models.user import User
from app.schemas.accounts import (
    AccItemLookup,
    AssemblyCompleteIn,
    AssemblyIn,
    AssemblyListItem,
    AssemblyListResponse,
    AssemblyNeedOut,
    AssemblyOut,
    AssemblyPartOut,
    BomIn,
    BomLineOut,
    BomListItem,
    BomListResponse,
    BomOut,
    OpenPo,
    OpenPoLine,
    PassportOut,
    PoIn,
    PoLineOut,
    PoListItem,
    PoListResponse,
    PoOut,
    PoReasonIn,
    SupplierIn,
    SupplierListResponse,
    SupplierOut,
)
from app.services import accounts_service as svc
from app.services.gst_service import GSTINValidator
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _can(db: Session, user: User, module: str, flag: str) -> bool:
    return can_act_on(db, user, module, flag, None)


def _need(db: Session, user: User, module: str, flag: str, message: str) -> None:
    if not _can(db, user, module, flag):
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


def _need_any_view(db: Session, user: User, modules: tuple[str, ...], message: str) -> None:
    if not any(_can(db, user, m, "can_view") for m in modules):
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


def _owner_or_override(db: Session, user: User, module: str, created_by: int | None, what: str) -> None:
    _need(db, user, module, "can_create", f"Your role cannot create or change {what}")
    if created_by != user.id and not _can(db, user, module, "can_delete"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Only the person who created this {what.rstrip('s')} can change it")


@router.get("/meta")
def meta(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "company_state": settings.company_state,
        "maker_checker": bool(settings.acc_maker_checker),
        "can_items": _can(db, user, "acc_items", "can_view"),
        "can_purchase": _can(db, user, "acc_purchase", "can_view"),
        "can_assembly": _can(db, user, "acc_assembly", "can_view"),
        "can_approve_po": _can(db, user, "acc_po_approval", "can_edit"),
        "states": [{"code": c, "name": n} for c, n in GSTINValidator.STATE_CODES.items()],
    }


# ---------------------------------------------------------------------------
# Item picker
# ---------------------------------------------------------------------------
@router.get("/lookup/items", response_model=list[AccItemLookup])
def lookup_items(
    q: str | None = Query(None),
    make_only: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need_any_view(db, user, ("acc_items", "acc_purchase", "acc_assembly"), "Your role cannot use Accounts")
    stmt = select(ItemMaster).where(ItemMaster.is_active.is_(True), ItemMaster.deleted_at.is_(None))
    if make_only:
        stmt = stmt.where(ItemMaster.source.in_(("Make", "Both")))
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(ItemMaster.item_code.ilike(like), ItemMaster.item_name.ilike(like)))
    rows = db.scalars(stmt.order_by(ItemMaster.item_name).limit(100)).all()
    return [
        AccItemLookup(
            id=r.id, item_code=r.item_code, item_name=r.item_name, serial_count=int(r.serial_count or 0),
            source=r.source or "Buy", item_type=r.item_type, gst_rate=float(r.gst_rate) if r.gst_rate is not None else None,
            hsn_code=r.hsn_code,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
def _supplier_out(s: Supplier) -> SupplierOut:
    return SupplierOut(
        id=s.id, name=s.name, gstin=s.gstin, pan=s.pan, state=s.state, state_code=s.state_code, address=s.address, city=s.city,
        pincode=s.pincode, contact_name=s.contact_name, phone=s.phone, email=s.email, is_msme=s.is_msme, msme_no=s.msme_no,
        payment_terms_days=s.payment_terms_days, bank_name=s.bank_name, bank_account=s.bank_account, bank_ifsc=s.bank_ifsc,
        is_active=s.is_active, registered=bool(s.gstin),
    )


@router.get("/suppliers", response_model=SupplierListResponse)
def list_suppliers(
    search: str | None = Query(None),
    active_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need_any_view(db, user, ("acc_purchase", "acc_po_approval"), "Your role cannot view suppliers")
    stmt = select(Supplier)
    if active_only:
        stmt = stmt.where(Supplier.is_active.is_(True))
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(Supplier.name.ilike(like), Supplier.gstin.ilike(like), Supplier.city.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Supplier.name).offset((page - 1) * per_page).limit(per_page)).all()
    return SupplierListResponse(items=[_supplier_out(s) for s in rows], total=total)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need_any_view(db, user, ("acc_purchase", "acc_po_approval"), "Your role cannot view suppliers")
    s = db.get(Supplier, supplier_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return _supplier_out(s)


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(body: SupplierIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_purchase", "can_create", "Your role cannot add suppliers")
    s = svc.apply_supplier(db, Supplier(), body)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _supplier_out(s)


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, body: SupplierIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_purchase", "can_edit", "Your role cannot edit suppliers")
    s = db.get(Supplier, supplier_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    svc.apply_supplier(db, s, body)
    db.commit()
    db.refresh(s)
    return _supplier_out(s)


# ---------------------------------------------------------------------------
# BOM
# ---------------------------------------------------------------------------
def _bom_out(db: Session, bom: Bom, user: User) -> BomOut:
    item = db.get(ItemMaster, bom.item_id)
    cost = svc.bom_costing(db, bom)
    lines = [
        BomLineOut(
            id=ln.id, component_item_id=ln.component_item_id, item_code=comp.item_code if comp else None,
            item_name=comp.item_name if comp else None, serial_count=int(comp.serial_count or 0) if comp else 0, qty=ln.qty,
            scrap_pct=ln.scrap_pct, note=ln.note, unit_cost=unit, line_cost=line_cost, in_store=have, can_build=buildable,
        )
        for ln, comp, unit, line_cost, have, buildable in cost["rows"]
    ]
    draft = bom.status == "Draft"
    owner_ok = bom.created_by == user.id or _can(db, user, "acc_items", "can_delete") or _can(db, user, "acc_items", "can_edit")
    return BomOut(
        id=bom.id, item_id=bom.item_id, item_code=item.item_code if item else None, item_name=item.item_name if item else None,
        version=bom.version, status=bom.status, notes=bom.notes, labour_cost=bom.labour_cost, overhead_cost=bom.overhead_cost,
        material_cost=cost["material"], unit_cost=cost["unit"], cost_complete=cost["complete"], can_build=cost["can_build"],
        buy_price_hint=svc.latest_po_rate(db, bom.item_id), created_by_name=svc._name(db, bom.created_by),
        activated_by_name=svc._name(db, bom.activated_by), activated_at=bom.activated_at, lines=lines,
        can_edit=draft and _can(db, user, "acc_items", "can_create") and owner_ok,
        can_activate=draft and _can(db, user, "acc_items", "can_edit"),
    )


def _load_bom(db: Session, bom_id: int) -> Bom:
    bom = db.get(Bom, bom_id)
    if bom is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BOM not found")
    return bom


@router.get("/boms", response_model=BomListResponse)
def list_boms(
    item_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "acc_items", "can_view", "Your role cannot view BOMs")
    stmt = select(Bom, ItemMaster).join(ItemMaster, ItemMaster.id == Bom.item_id)
    if item_id:
        stmt = stmt.where(Bom.item_id == item_id)
    if status_filter:
        stmt = stmt.where(Bom.status == status_filter)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(ItemMaster.item_code.ilike(like), ItemMaster.item_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(ItemMaster.item_name, Bom.version.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    items = []
    for bom, item in rows:
        cost = svc.bom_costing(db, bom)
        items.append(
            BomListItem(
                id=bom.id, item_id=item.id, item_code=item.item_code, item_name=item.item_name, version=bom.version,
                status=bom.status, lines=len(cost["rows"]), unit_cost=cost["unit"], activated_at=bom.activated_at,
            )
        )
    return BomListResponse(items=items, total=total)


@router.get("/boms/{bom_id}", response_model=BomOut)
def get_bom(bom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_items", "can_view", "Your role cannot view BOMs")
    return _bom_out(db, _load_bom(db, bom_id), user)


@router.post("/boms", response_model=BomOut, status_code=status.HTTP_201_CREATED)
def create_bom(body: BomIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_items", "can_create", "Your role cannot create BOMs")
    bom = svc.create_bom(db, user, body)
    db.commit()
    db.refresh(bom)
    return _bom_out(db, bom, user)


@router.put("/boms/{bom_id}", response_model=BomOut)
def update_bom(bom_id: int, body: BomIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bom = _load_bom(db, bom_id)
    _owner_or_override_bom(db, user, bom)
    svc.update_bom_draft(db, bom, body)
    db.commit()
    db.refresh(bom)
    return _bom_out(db, bom, user)


def _owner_or_override_bom(db: Session, user: User, bom: Bom) -> None:
    _need(db, user, "acc_items", "can_create", "Your role cannot change BOMs")
    if bom.created_by != user.id and not (_can(db, user, "acc_items", "can_edit") or _can(db, user, "acc_items", "can_delete")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who drafted this BOM can change it")


@router.post("/boms/{bom_id}/copy", response_model=BomOut, status_code=status.HTTP_201_CREATED)
def copy_bom(bom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_items", "can_create", "Your role cannot create BOMs")
    new = svc.copy_bom(db, user, _load_bom(db, bom_id))
    db.commit()
    db.refresh(new)
    return _bom_out(db, new, user)


@router.post("/boms/{bom_id}/activate", response_model=BomOut)
def activate_bom(bom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_items", "can_edit", "Only an accounts manager can activate a BOM")
    bom = svc.activate_bom(db, user, _load_bom(db, bom_id))
    db.commit()
    db.refresh(bom)
    return _bom_out(db, bom, user)


@router.delete("/boms/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom(bom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bom = _load_bom(db, bom_id)
    _owner_or_override_bom(db, user, bom)
    if bom.status != "Draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a draft BOM can be deleted")
    db.delete(bom)
    db.commit()


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def _parts_out(db: Session, asm: AssemblyOrder) -> list[AssemblyPartOut]:
    out = []
    for p in db.scalars(select(AssemblyPart).where(AssemblyPart.assembly_id == asm.id).order_by(AssemblyPart.id)):
        comp = db.get(ItemMaster, p.component_item_id)
        out.append(
            AssemblyPartOut(
                finished_serial=p.finished_serial, component_item_id=p.component_item_id, item_code=comp.item_code if comp else None,
                item_name=comp.item_name if comp else None, component_serial=p.component_serial, qty=p.qty, unit_cost=p.unit_cost,
            )
        )
    return out


def _asm_out(db: Session, asm: AssemblyOrder, user: User) -> AssemblyOut:
    item = db.get(ItemMaster, asm.item_id)
    bom = db.get(Bom, asm.bom_id)
    planned = asm.status == "Planned"
    needs = [AssemblyNeedOut(**n) for n in svc.assembly_needs(db, asm)] if planned else []
    unit_cost = None
    if bom is not None:
        unit_cost = svc.bom_costing(db, bom)["unit"]
    return AssemblyOut(
        id=asm.id, asm_no=asm.asm_no, item_id=asm.item_id, item_code=item.item_code if item else None,
        item_name=item.item_name if item else None, serial_count=int(item.serial_count or 0) if item else 1, bom_id=asm.bom_id,
        bom_version=bom.version if bom else None, qty=asm.qty, status=asm.status, remarks=asm.remarks,
        created_by_name=svc._name(db, asm.created_by), completed_by_name=svc._name(db, asm.completed_by),
        created_at=asm.created_at, completed_at=asm.completed_at, needs=needs, parts=_parts_out(db, asm), unit_cost=unit_cost,
        can_complete=planned and _can(db, user, "acc_assembly", "can_edit") and not any(n.short for n in needs),
        can_cancel=planned and _can(db, user, "acc_assembly", "can_edit"),
    )


def _load_asm(db: Session, asm_id: int) -> AssemblyOrder:
    asm = db.get(AssemblyOrder, asm_id)
    if asm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assembly order not found")
    return asm


@router.get("/assemblies", response_model=AssemblyListResponse)
def list_assemblies(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "acc_assembly", "can_view", "Your role cannot view assembly orders")
    stmt = select(AssemblyOrder, ItemMaster).join(ItemMaster, ItemMaster.id == AssemblyOrder.item_id)
    if status_filter:
        stmt = stmt.where(AssemblyOrder.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(AssemblyOrder.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    return AssemblyListResponse(
        items=[
            AssemblyListItem(id=a.id, asm_no=a.asm_no, item_code=i.item_code, item_name=i.item_name, qty=a.qty, status=a.status, created_at=a.created_at)
            for a, i in rows
        ],
        total=total,
    )


@router.post("/assemblies", response_model=AssemblyOut, status_code=status.HTTP_201_CREATED)
def create_assembly(body: AssemblyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_assembly", "can_create", "Your role cannot plan assemblies")
    asm = svc.create_assembly(db, user, body)
    db.commit()
    db.refresh(asm)
    return _asm_out(db, asm, user)


@router.get("/assemblies/{asm_id}", response_model=AssemblyOut)
def get_assembly(asm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_assembly", "can_view", "Your role cannot view assembly orders")
    return _asm_out(db, _load_asm(db, asm_id), user)


@router.post("/assemblies/{asm_id}/complete", response_model=AssemblyOut)
def complete_assembly(asm_id: int, body: AssemblyCompleteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_assembly", "can_edit", "Your role cannot complete assemblies")
    asm = svc.complete_assembly(db, user, _load_asm(db, asm_id), body.units)
    db.commit()
    db.refresh(asm)
    return _asm_out(db, asm, user)


@router.post("/assemblies/{asm_id}/cancel", response_model=AssemblyOut)
def cancel_assembly(asm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_assembly", "can_edit", "Your role cannot cancel assemblies")
    asm = svc.cancel_assembly(db, _load_asm(db, asm_id))
    db.commit()
    db.refresh(asm)
    return _asm_out(db, asm, user)


@router.get("/passport/{serial}", response_model=PassportOut)
def passport(serial: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (_can(db, user, "acc_assembly", "can_view") or _can(db, user, "store_stock", "can_view")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view unit passports")
    s = svc.normalize_serial(serial)
    rows = db.scalars(select(AssemblyPart).where(AssemblyPart.finished_serial == s).order_by(AssemblyPart.id)).all()
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No assembly record for this serial")
    asm = db.get(AssemblyOrder, rows[0].assembly_id)
    item = db.get(ItemMaster, asm.item_id) if asm else None
    return PassportOut(
        serial=s, asm_no=asm.asm_no if asm else None, item_name=item.item_name if item else None,
        built_at=asm.completed_at if asm else None, parts=_parts_out_for(db, rows),
    )


def _parts_out_for(db: Session, rows) -> list[AssemblyPartOut]:
    out = []
    for p in rows:
        comp = db.get(ItemMaster, p.component_item_id)
        out.append(
            AssemblyPartOut(
                finished_serial=p.finished_serial, component_item_id=p.component_item_id, item_code=comp.item_code if comp else None,
                item_name=comp.item_name if comp else None, component_serial=p.component_serial, qty=p.qty, unit_cost=p.unit_cost,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Purchase orders
# ---------------------------------------------------------------------------
def _po_out(db: Session, po: PurchaseOrder, user: User) -> PoOut:
    sup = db.get(Supplier, po.supplier_id)
    lines = []
    for ln in svc.po_lines(db, po):
        item = db.get(ItemMaster, ln.item_id)
        tax = svc.q2(ln.taxable * ln.gst_rate / 100)
        lines.append(
            PoLineOut(
                id=ln.id, item_id=ln.item_id, item_code=item.item_code if item else None, item_name=ln.description or (item.item_name if item else None),
                hsn_code=ln.hsn_code, qty=ln.qty, rate=ln.rate, gst_rate=ln.gst_rate, taxable=ln.taxable, tax=tax,
                received_qty=ln.received_qty, outstanding=max(0, ln.qty - ln.received_qty),
            )
        )
    draft = po.status == "Draft"
    return PoOut(
        id=po.id, po_no=po.po_no, po_date=po.po_date, supplier_id=po.supplier_id, supplier_name=sup.name if sup else None,
        supplier_gstin=sup.gstin if sup else None, supplier_is_msme=bool(sup and sup.is_msme), expected_date=po.expected_date,
        status=po.status, place_of_supply=po.place_of_supply, intra_state=po.intra_state, payment_terms_days=po.payment_terms_days,
        terms=po.terms, remarks=po.remarks, taxable_value=po.taxable_value, cgst=po.cgst, sgst=po.sgst, igst=po.igst, total=po.total,
        reject_reason=po.reject_reason, created_by_name=svc._name(db, po.created_by), approved_by_name=svc._name(db, po.approved_by),
        created_at=po.created_at, submitted_at=po.submitted_at, approved_at=po.approved_at, lines=lines,
        can_edit=draft and _can(db, user, "acc_purchase", "can_create") and (po.created_by == user.id or _can(db, user, "acc_purchase", "can_delete")),
        can_submit=draft and _can(db, user, "acc_purchase", "can_create") and (po.created_by == user.id or _can(db, user, "acc_purchase", "can_delete")),
        can_approve=po.status == "Pending Approval" and _can(db, user, "acc_po_approval", "can_edit") and svc.can_approve_own(user, po),
        can_cancel=po.status in ("Draft", "Pending Approval", "Approved") and _can(db, user, "acc_purchase", "can_edit"),
    )


def _load_po(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po


@router.get("/pos/open", response_model=list[OpenPo])
def open_pos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (_can(db, user, "store_receiving", "can_create") or _can(db, user, "acc_purchase", "can_view")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot see purchase orders")
    out = []
    for po in db.scalars(select(PurchaseOrder).where(PurchaseOrder.status.in_(("Approved", "Part received"))).order_by(PurchaseOrder.id.desc())):
        sup = db.get(Supplier, po.supplier_id)
        lines = []
        for item_id, left in svc.outstanding_by_item(db, po).items():
            if left > 0:
                item = db.get(ItemMaster, item_id)
                lines.append(OpenPoLine(item_id=item_id, item_code=item.item_code if item else None, item_name=item.item_name if item else None, outstanding=left))
        out.append(OpenPo(id=po.id, po_no=po.po_no, supplier_name=sup.name if sup else None, status=po.status, lines=lines))
    return out


@router.get("/pos", response_model=PoListResponse)
def list_pos(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need_any_view(db, user, ("acc_purchase", "acc_po_approval"), "Your role cannot view purchase orders")
    stmt = select(PurchaseOrder, Supplier).join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(PurchaseOrder.po_no.ilike(like), Supplier.name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(PurchaseOrder.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    return PoListResponse(
        items=[
            PoListItem(id=p.id, po_no=p.po_no, po_date=p.po_date, supplier_name=s.name, status=p.status, total=p.total, created_by_name=svc._name(db, p.created_by))
            for p, s in rows
        ],
        total=total,
    )


@router.post("/pos", response_model=PoOut, status_code=status.HTTP_201_CREATED)
def create_po(body: PoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_purchase", "can_create", "Your role cannot raise purchase orders")
    po = svc.create_po(db, user, body)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)


@router.get("/pos/{po_id}", response_model=PoOut)
def get_po(po_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need_any_view(db, user, ("acc_purchase", "acc_po_approval"), "Your role cannot view purchase orders")
    return _po_out(db, _load_po(db, po_id), user)


@router.put("/pos/{po_id}", response_model=PoOut)
def update_po(po_id: int, body: PoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    po = _load_po(db, po_id)
    _owner_or_override(db, user, "acc_purchase", po.created_by, "purchase orders")
    svc.update_po_draft(db, po, body)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)


@router.post("/pos/{po_id}/submit", response_model=PoOut)
def submit_po(po_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    po = _load_po(db, po_id)
    _owner_or_override(db, user, "acc_purchase", po.created_by, "purchase orders")
    svc.submit_po(db, po)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)


@router.post("/pos/{po_id}/approve", response_model=PoOut)
def approve_po(po_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_po_approval", "can_edit", "Your role cannot approve purchase orders")
    po = svc.approve_po(db, _load_po(db, po_id), user)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)


@router.post("/pos/{po_id}/reject", response_model=PoOut)
def reject_po(po_id: int, body: PoReasonIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_po_approval", "can_edit", "Your role cannot approve purchase orders")
    po = svc.reject_po(db, _load_po(db, po_id), user, body.reason)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)


@router.post("/pos/{po_id}/cancel", response_model=PoOut)
def cancel_po(po_id: int, body: PoReasonIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "acc_purchase", "can_edit", "Your role cannot cancel purchase orders")
    po = svc.cancel_po(db, _load_po(db, po_id), body.reason)
    db.commit()
    db.refresh(po)
    return _po_out(db, po, user)
