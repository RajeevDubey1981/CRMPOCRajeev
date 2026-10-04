from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.courier import Courier
from app.models.item_master import ItemMaster
from app.models.order import Order
from app.models.store import (
    CONDITIONS,
    GRN_SOURCES,
    STOCK_TYPES,
    StoreDispatch,
    StoreGrn,
    StoreGrnLine,
    StoreLedger,
    StoreStock,
)
from app.models.user import User
from app.schemas.store import (
    CourierLookup,
    DispatchIn,
    FreeStock,
    GrnIn,
    GrnLineOut,
    GrnListItem,
    GrnListResponse,
    GrnOut,
    LedgerResponse,
    LedgerRow,
    OrderUnitOut,
    RejectIn,
    ReserveOut,
    SerialCheckIn,
    SerialCheckOut,
    StockSummaryItem,
    StockUnit,
    StockUnitsResponse,
    StoreItemLookup,
    StoreOrderListItem,
    StoreOrderListResponse,
    StoreOrderOut,
)
from app.services import store_dispatch_service, store_service
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/store", tags=["store"])


def _need(db: Session, user: User, module: str, flag: str, message: str) -> None:
    if not can_act_on(db, user, module, flag, None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


def _can_see_grns(db: Session, user: User) -> bool:
    return can_act_on(db, user, "store_receiving", "can_view", None) or can_act_on(db, user, "store_approval", "can_view", None)


def _user_name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    u = db.get(User, user_id)
    return u.name if u else None


def _hydrate(db: Session, grn: StoreGrn, user: User) -> GrnOut:
    rows = db.execute(
        select(StoreGrnLine, ItemMaster)
        .join(ItemMaster, ItemMaster.id == StoreGrnLine.item_id)
        .where(StoreGrnLine.grn_id == grn.id)
        .order_by(StoreGrnLine.id)
    ).all()
    lines = [
        GrnLineOut(
            id=ln.id,
            item_id=ln.item_id,
            item_code=item.item_code,
            item_name=item.item_name,
            serial_count=int(item.serial_count or 0),
            stock_type=ln.stock_type,
            serial_no=ln.serial_no,
            serial_no_2=ln.serial_no_2,
            qty=ln.qty,
            unit_cost=ln.unit_cost,
            condition=ln.condition,
            bin_location=ln.bin_location,
        )
        for ln, item in rows
    ]
    can_approve = (
        grn.status == "Pending Approval"
        and can_act_on(db, user, "store_approval", "can_edit", None)
        and store_service.can_user_approve_own(user, grn)
    )
    return GrnOut(
        id=grn.id,
        grn_no=grn.grn_no,
        source_type=grn.source_type,
        supplier_name=grn.supplier_name,
        reference_no=grn.reference_no,
        status=grn.status,
        remarks=grn.remarks,
        reject_reason=grn.reject_reason,
        created_by=grn.created_by,
        created_by_name=_user_name(db, grn.created_by),
        approved_by=grn.approved_by,
        approved_by_name=_user_name(db, grn.approved_by),
        created_at=grn.created_at,
        submitted_at=grn.submitted_at,
        approved_at=grn.approved_at,
        total_units=sum(ln.qty for ln in lines),
        lines=lines,
        can_approve=can_approve,
    )


def _load(db: Session, grn_id: int) -> StoreGrn:
    grn = db.get(StoreGrn, grn_id)
    if grn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "GRN not found")
    return grn


def _need_draft_owner(user: User, grn: StoreGrn, db: Session) -> None:
    _need(db, user, "store_receiving", "can_create", "Your role cannot create or edit GRNs")
    # Only the creator changes a draft. Overriding someone else's draft needs the Delete flag (Admin by default).
    if grn.created_by != user.id and not can_act_on(db, user, "store_receiving", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who created this GRN can change it")


@router.get("/meta")
def meta(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "sources": list(GRN_SOURCES),
        "stock_types": list(STOCK_TYPES),
        "conditions": list(CONDITIONS),
        "maker_checker": bool(settings.store_maker_checker),
        "can_receive": can_act_on(db, user, "store_receiving", "can_create", None),
        "can_approve": can_act_on(db, user, "store_approval", "can_edit", None),
        "can_view_stock": can_act_on(db, user, "store_stock", "can_view", None),
        "can_view_dispatch": can_act_on(db, user, "store_dispatch", "can_view", None),
        "can_dispatch": can_act_on(db, user, "store_dispatch", "can_create", None),
    }


@router.get("/lookup/items", response_model=list[StoreItemLookup])
def lookup_items(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (_can_see_grns(db, user) or can_act_on(db, user, "store_stock", "can_view", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot use the store")
    stmt = select(ItemMaster).where(ItemMaster.is_active.is_(True), ItemMaster.deleted_at.is_(None))
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(ItemMaster.item_code.ilike(like), ItemMaster.item_name.ilike(like)))
    rows = db.scalars(stmt.order_by(ItemMaster.item_name).limit(50)).all()
    return [StoreItemLookup(id=r.id, item_code=r.item_code, item_name=r.item_name, serial_count=int(r.serial_count or 0)) for r in rows]


@router.post("/serials/check", response_model=SerialCheckOut)
def check_serial(body: SerialCheckIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_receiving", "can_create", "Your role cannot receive goods")
    s = store_service.normalize_serial(body.serial)
    why = store_service.serial_conflict(db, s, exclude_grn_id=body.grn_id)
    return SerialCheckOut(serial=s, ok=why is None, reason=why)


@router.get("/grns", response_model=GrnListResponse)
def list_grns(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _can_see_grns(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view GRNs")
    stmt = select(StoreGrn)
    if status_filter:
        stmt = stmt.where(StoreGrn.status == status_filter)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(StoreGrn.grn_no.ilike(like), StoreGrn.reference_no.ilike(like), StoreGrn.supplier_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(StoreGrn.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    items = []
    for g in rows:
        units = db.scalar(select(func.coalesce(func.sum(StoreGrnLine.qty), 0)).where(StoreGrnLine.grn_id == g.id)) or 0
        items.append(
            GrnListItem(
                id=g.id,
                grn_no=g.grn_no,
                source_type=g.source_type,
                supplier_name=g.supplier_name,
                reference_no=g.reference_no,
                status=g.status,
                created_by_name=_user_name(db, g.created_by),
                created_at=g.created_at,
                total_units=int(units),
            )
        )
    return GrnListResponse(items=items, total=total)


@router.post("/grns", response_model=GrnOut, status_code=status.HTTP_201_CREATED)
def create_grn(body: GrnIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_receiving", "can_create", "Your role cannot create GRNs")
    grn = store_service.create_grn(db, user, body)
    db.commit()
    db.refresh(grn)
    return _hydrate(db, grn, user)


@router.get("/grns/{grn_id}", response_model=GrnOut)
def get_grn(grn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not _can_see_grns(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view GRNs")
    return _hydrate(db, _load(db, grn_id), user)


@router.put("/grns/{grn_id}", response_model=GrnOut)
def update_grn(grn_id: int, body: GrnIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    grn = _load(db, grn_id)
    _need_draft_owner(user, grn, db)
    store_service.update_draft(db, grn, body)
    db.commit()
    db.refresh(grn)
    return _hydrate(db, grn, user)


@router.delete("/grns/{grn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grn(grn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    grn = _load(db, grn_id)
    _need_draft_owner(user, grn, db)
    if grn.status != "Draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a draft GRN can be deleted")
    db.delete(grn)
    db.commit()


@router.post("/grns/{grn_id}/submit", response_model=GrnOut)
def submit_grn(grn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    grn = _load(db, grn_id)
    _need_draft_owner(user, grn, db)
    store_service.submit_grn(db, grn)
    db.commit()
    db.refresh(grn)
    return _hydrate(db, grn, user)


@router.post("/grns/{grn_id}/approve", response_model=GrnOut)
def approve_grn(grn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_approval", "can_edit", "Your role cannot approve GRNs")
    grn = _load(db, grn_id)
    store_service.approve_and_post(db, grn, user)
    db.commit()
    db.refresh(grn)
    return _hydrate(db, grn, user)


@router.post("/grns/{grn_id}/reject", response_model=GrnOut)
def reject_grn(grn_id: int, body: RejectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_approval", "can_edit", "Your role cannot approve GRNs")
    grn = _load(db, grn_id)
    store_service.reject_grn(db, grn, user, body.reason)
    db.commit()
    db.refresh(grn)
    return _hydrate(db, grn, user)


@router.get("/stock", response_model=list[StockSummaryItem])
def stock_summary(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "store_stock", "can_view", "Your role cannot view store stock")
    stmt = (
        select(
            ItemMaster.id,
            ItemMaster.item_code,
            ItemMaster.item_name,
            ItemMaster.serial_count,
            func.coalesce(func.sum(case((StoreStock.status == "Available", StoreStock.qty), else_=0)), 0),
            func.coalesce(func.sum(case((StoreStock.status == "Quarantine", StoreStock.qty), else_=0)), 0),
            func.coalesce(func.sum(case((StoreStock.status.in_(("Available", "Quarantine", "Reserved")), StoreStock.qty), else_=0)), 0),
            func.min(case((StoreStock.status == "Available", StoreStock.received_at), else_=None)),
        )
        .join(StoreStock, StoreStock.item_id == ItemMaster.id)
        .group_by(ItemMaster.id, ItemMaster.item_code, ItemMaster.item_name, ItemMaster.serial_count)
        .order_by(ItemMaster.item_name)
    )
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(ItemMaster.item_code.ilike(like), ItemMaster.item_name.ilike(like)))
    return [
        StockSummaryItem(
            item_id=r[0], item_code=r[1], item_name=r[2], serial_count=int(r[3] or 0),
            available=int(r[4]), quarantine=int(r[5]), total=int(r[6]), oldest_received=r[7],
        )
        for r in db.execute(stmt).all()
    ]


@router.get("/stock/units", response_model=StockUnitsResponse)
def stock_units(
    item_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "store_stock", "can_view", "Your role cannot view store stock")
    stmt = (
        select(StoreStock, ItemMaster, StoreGrn.grn_no)
        .join(ItemMaster, ItemMaster.id == StoreStock.item_id)
        .join(StoreGrn, StoreGrn.id == StoreStock.grn_id, isouter=True)
    )
    if item_id:
        stmt = stmt.where(StoreStock.item_id == item_id)
    if status_filter:
        stmt = stmt.where(StoreStock.status == status_filter)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(StoreStock.serial_no.ilike(like), StoreStock.serial_no_2.ilike(like), ItemMaster.item_name.ilike(like), ItemMaster.item_code.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(StoreStock.received_at.asc(), StoreStock.id.asc()).offset((page - 1) * per_page).limit(per_page)).all()
    now = datetime.now(timezone.utc)
    items = []
    for st, item, grn_no in rows:
        rec = st.received_at if st.received_at.tzinfo else st.received_at.replace(tzinfo=timezone.utc)
        items.append(
            StockUnit(
                id=st.id, item_id=st.item_id, item_code=item.item_code, item_name=item.item_name,
                serial_no=st.serial_no, serial_no_2=st.serial_no_2, stock_type=st.stock_type, condition=st.condition,
                status=st.status, qty=st.qty, unit_cost=st.unit_cost, bin_location=st.bin_location, grn_no=grn_no,
                received_at=st.received_at, age_days=max(0, (now - rec).days),
            )
        )
    return StockUnitsResponse(items=items, total=total)


@router.get("/ledger", response_model=LedgerResponse)
def ledger(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "store_stock", "can_view", "Your role cannot view the store ledger")
    stmt = select(StoreLedger, ItemMaster).join(ItemMaster, ItemMaster.id == StoreLedger.item_id)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(StoreLedger.doc_no.ilike(like), StoreLedger.serial_no.ilike(like), ItemMaster.item_name.ilike(like), ItemMaster.item_code.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(StoreLedger.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    return LedgerResponse(
        items=[
            LedgerRow(
                id=lg.id, created_at=lg.created_at, doc_type=lg.doc_type, doc_no=lg.doc_no, item_code=item.item_code,
                item_name=item.item_name, serial_no=lg.serial_no, qty_in=lg.qty_in, qty_out=lg.qty_out,
                stock_type=lg.stock_type, by_user_name=_user_name(db, lg.by_user_id), note=lg.note,
            )
            for lg, item in rows
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# Orders shipped from our own store: reserve, bill gate, dispatch
# ---------------------------------------------------------------------------

def _load_store_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.deleted_at is not None or order.fulfilment != "Store":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store order not found")
    return order


def _store_order_out(db: Session, order: Order, user: User) -> StoreOrderOut:
    lines = store_dispatch_service.order_lines(db, order)
    units = store_dispatch_service.held_units(db, order)
    wanted = {ln.item_id for ln in lines if ln.item_id}
    items = {i.id: i for i in db.scalars(select(ItemMaster).where(ItemMaster.id.in_(wanted))).all()} if wanted else {}
    out_lines = []
    needed: dict[int, int] = {}
    for ln in lines:
        u = units.get(ln.id)
        item = items.get(ln.item_id)
        if u is None and ln.item_id:
            needed[ln.item_id] = needed.get(ln.item_id, 0) + 1
        out_lines.append(
            OrderUnitOut(
                order_item_id=ln.id,
                item_id=ln.item_id,
                item_code=item.item_code if item else ln.item_code,
                item_name=item.item_name if item else None,
                serial_count=int(item.serial_count or 0) if item else 1,
                stock_id=u.id if u else None,
                serial_no=(u.serial_no if u else ln.serial_no),
                serial_no_2=(u.serial_no_2 if u else ln.serial_no_2),
                unit_status=u.status if u else None,
                received_at=u.received_at if u else None,
            )
        )
    free = store_dispatch_service.free_stock_by_item(db)
    stock_check = [
        FreeStock(item_id=iid, item_name=items[iid].item_name if iid in items else None, needed=n, available=free.get(iid, 0))
        for iid, n in needed.items()
    ]
    stage = store_dispatch_service.order_stage(db, order)
    dsp = db.scalar(select(StoreDispatch).where(StoreDispatch.order_id == order.id).order_by(StoreDispatch.id.desc()))
    courier = db.get(Courier, order.courier_id) if order.courier_id else None
    pending = order.status == "Pending"
    return StoreOrderOut(
        id=order.id,
        order_no=order.order_no,
        order_date=order.order_date,
        customer_name=order.customer_name,
        customer_city=order.customer_city,
        customer_address=order.customer_address,
        oem_bill_no=order.oem_bill_no,
        status=order.status,
        stage=stage,
        courier_name=courier.courier_name if courier else None,
        lrn_no=order.lrn_no,
        dispatch_no=dsp.dispatch_no if dsp else None,
        dispatched_at=dsp.dispatched_at if dsp else None,
        lines=out_lines,
        stock_check=stock_check,
        can_reserve=pending and stage == "Needs stock" and can_act_on(db, user, "store_dispatch", "can_create", None),
        can_release=pending and bool(units) and can_act_on(db, user, "store_dispatch", "can_edit", None),
        can_dispatch=pending and stage == "Ready to dispatch" and can_act_on(db, user, "store_dispatch", "can_create", None),
    )


@router.get("/lookup/couriers", response_model=list[CourierLookup])
def lookup_couriers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_dispatch", "can_view", "Your role cannot use store dispatch")
    rows = db.scalars(select(Courier).where(Courier.deleted_at.is_(None)).order_by(Courier.courier_name)).all()
    return [CourierLookup(id=c.id, courier_name=c.courier_name) for c in rows]


@router.get("/orders", response_model=StoreOrderListResponse)
def list_store_orders(
    stage: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _need(db, user, "store_dispatch", "can_view", "Your role cannot use store dispatch")
    stmt = select(Order).where(Order.fulfilment == "Store", Order.deleted_at.is_(None), Order.status != "Cancelled")
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(or_(Order.order_no.ilike(like), Order.customer_name.ilike(like), Order.oem_bill_no.ilike(like), Order.customer_city.ilike(like)))
    counts = {s: 0 for s in store_dispatch_service.STAGES}
    rows = []
    for o in db.scalars(stmt.order_by(Order.id.desc())).all():
        st = store_dispatch_service.order_stage(db, o)
        counts[st] += 1
        if not stage or st == stage:
            rows.append((o, st))
    total = len(rows)
    page_rows = rows[(page - 1) * per_page : page * per_page]
    items = []
    for o, st in page_rows:
        lines = store_dispatch_service.order_lines(db, o)
        units = store_dispatch_service.held_units(db, o)
        items.append(
            StoreOrderListItem(
                id=o.id, order_no=o.order_no, order_date=o.order_date, customer_name=o.customer_name,
                customer_city=o.customer_city, oem_bill_no=o.oem_bill_no, status=o.status, stage=st,
                units=len(lines), held=len(units),
            )
        )
    return StoreOrderListResponse(items=items, total=total, counts=counts)


@router.get("/orders/{order_id}", response_model=StoreOrderOut)
def get_store_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_dispatch", "can_view", "Your role cannot use store dispatch")
    return _store_order_out(db, _load_store_order(db, order_id), user)


@router.post("/orders/{order_id}/reserve", response_model=ReserveOut)
def reserve_store_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_dispatch", "can_create", "Your role cannot reserve stock")
    order = _load_store_order(db, order_id)
    result = store_dispatch_service.reserve_order(db, order, user)
    db.commit()
    db.refresh(order)
    return ReserveOut(reserved=result["reserved"], short=result["short"], order=_store_order_out(db, order, user))


@router.post("/orders/{order_id}/release", response_model=StoreOrderOut)
def release_store_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_dispatch", "can_edit", "Only a store manager can release reserved stock")
    order = _load_store_order(db, order_id)
    if order.status != "Pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Stock cannot be released once the order has left the store")
    store_dispatch_service.release_order(db, order, user)
    db.commit()
    db.refresh(order)
    return _store_order_out(db, order, user)


@router.post("/orders/{order_id}/dispatch", response_model=StoreOrderOut)
def dispatch_store_order(order_id: int, body: DispatchIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _need(db, user, "store_dispatch", "can_create", "Your role cannot dispatch orders")
    order = _load_store_order(db, order_id)
    store_dispatch_service.dispatch_order(
        db, order, user, scans=body.scans, courier_id=body.courier_id, lrn_no=body.lrn_no, remarks=body.remarks
    )
    from app.services.pending_action_sync import sync_order_pending_actions

    sync_order_pending_actions(db, order)
    db.commit()
    db.refresh(order)
    return _store_order_out(db, order, user)
