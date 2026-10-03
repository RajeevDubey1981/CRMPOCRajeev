from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.item_master import ItemMaster
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
from app.schemas.store import (
    GrnIn,
    GrnLineOut,
    GrnListItem,
    GrnListResponse,
    GrnOut,
    LedgerResponse,
    LedgerRow,
    RejectIn,
    SerialCheckIn,
    SerialCheckOut,
    StockSummaryItem,
    StockUnit,
    StockUnitsResponse,
    StoreItemLookup,
)
from app.services import store_service
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
