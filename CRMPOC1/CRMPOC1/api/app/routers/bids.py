from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.bid import Bid, BidEvent, BidLine, BidRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.bid import (
    AllocateIn,
    BidEventOut,
    BidIn,
    BidLineIn,
    BidLineOut,
    BidMini,
    BidNumberCheck,
    BidOut,
    BidRequestOut,
    BidUpdate,
    ReasonIn,
    RequestDecisionIn,
    RequestIn,
    ResultIn,
    SubmitIn,
    VendorLookupOut,
    VendorPick,
)
from app.services import bid_service as svc
from app.services.bid_access import BidAccess, bid_access
from app.services.bid_service import BidError

router = APIRouter(prefix="/api/bids", tags=["bids"])


# --------------------------------------------------------------------------- access

def _commit(db: Session) -> None:
    db.commit()
    svc.flush_outbox()


def get_access(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> BidAccess:
    access = bid_access(db, user)
    if access is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bid management is not available for your account")
    svc.discard_outbox()  # mails queued by an earlier request on this thread are never ours
    return access


def manager_access(access: BidAccess = Depends(get_access)) -> BidAccess:
    if not access.is_manager:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the bid team can do this")
    return access


def _fail(exc: BidError):
    raise HTTPException(exc.status, exc.message)


# --------------------------------------------------------------------------- shaping

def _lines_for(db: Session, bid_ids: list[int]) -> dict[int, list[BidLine]]:
    """Tonnage lines of many bids in one query."""
    out: dict[int, list[BidLine]] = {}
    if not bid_ids:
        return out
    for row in db.scalars(select(BidLine).where(BidLine.bid_id.in_(bid_ids)).order_by(BidLine.position, BidLine.id)).all():
        out.setdefault(row.bid_id, []).append(row)
    return out


def _line_text(rows: list[BidLine]) -> str:
    """The item names, so a search for an item or a tonnage finds the bid."""
    return " ".join(r.item for r in rows)


def _save_lines(db: Session, bid: Bid, lines: list[BidLineIn]) -> bool:
    """Replace the bid's item lines. The bid's quantity becomes their total. Returns True when something changed."""
    seen: set[str] = set()
    for line in lines:
        key = svc.norm(line.item)
        if key in seen:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"\"{line.item}\" is listed twice. Put the whole quantity on one line")
        seen.add(key)
    old = [(r.item, r.quantity) for r in db.scalars(select(BidLine).where(BidLine.bid_id == bid.id).order_by(BidLine.position, BidLine.id)).all()]
    new = [(l.item, l.quantity) for l in lines]
    if old == new:
        return False
    for row in db.scalars(select(BidLine).where(BidLine.bid_id == bid.id)).all():
        db.delete(row)
    db.flush()
    for i, line in enumerate(lines):
        db.add(BidLine(bid_id=bid.id, position=i, item=line.item, quantity=line.quantity))
    quantities = [l.quantity for l in lines if l.quantity is not None]
    if quantities:
        bid.quantity = sum(quantities)
    return True


def _bid_out(db: Session, bid: Bid, access: BidAccess, *, with_events: bool = False, pending: dict[int, int] | None = None, lines_map: dict[int, list[BidLine]] | None = None) -> BidOut:
    vendor = db.get(Vendor, bid.vendor_id) if bid.vendor_id else None
    out = BidOut.model_validate(bid, from_attributes=True)
    out.vendor_name = svc.vendor_label(bid, vendor)
    out.days_left = (bid.end_date - svc.today_ist()).days
    rows = (lines_map if lines_map is not None else _lines_for(db, [bid.id])).get(bid.id, [])
    out.lines = [BidLineOut(item=r.item, quantity=r.quantity) for r in rows]
    if access.is_manager:
        if pending is not None:
            out.pending_requests = pending.get(bid.id, 0)
    else:
        out.notes = None
        out.vendor_name = vendor.name_of_firm if vendor else None
        out.pending_requests = 0
    if with_events:
        stmt = select(BidEvent).where(BidEvent.bid_id == bid.id)
        if not access.is_manager:
            stmt = stmt.where(BidEvent.vendor_id == access.vendor.id, BidEvent.action.notin_(("requested",)))
        out.events = [BidEventOut.model_validate(e, from_attributes=True) for e in db.scalars(stmt.order_by(BidEvent.id)).all()]
    return out


def _pending_counts(db: Session) -> dict[int, int]:
    counts: dict[int, int] = {}
    for bid_id in db.scalars(select(BidRequest.bid_id).where(BidRequest.status == "Requested", BidRequest.bid_id.isnot(None))).all():
        counts[bid_id] = counts.get(bid_id, 0) + 1
    return counts


def _request_out(db: Session, req: BidRequest, access: BidAccess) -> BidRequestOut:
    bid = db.get(Bid, req.bid_id) if req.bid_id else None
    vendor = db.get(Vendor, req.vendor_id)
    out = BidRequestOut(
        id=req.id, bid_id=req.bid_id, bid_number=req.bid_number, vendor_id=req.vendor_id,
        vendor_name=vendor.name_of_firm if vendor else None, note=req.note, status=req.status,
        decision_note=req.decision_note, created_at=req.created_at, decided_at=req.decided_at,
    )
    if access.is_manager and bid is not None:
        out.bid_title = bid.title
        out.bid_status = bid.status
        if bid.status in svc.HELD_STATUSES:
            holder = db.get(Vendor, bid.vendor_id) if bid.vendor_id else None
            out.holder = svc.vendor_label(bid, holder)
        out.asked_by_others = len(db.scalars(
            select(BidRequest.id).where(BidRequest.bid_id == bid.id, BidRequest.status == "Requested", BidRequest.id != req.id)
        ).all())
    elif not access.is_manager:
        if req.status == "Not available":
            out.decision_note = "Not available, already allocated"
    return out


def _get_bid(db: Session, bid_id: int, access: BidAccess) -> Bid:
    bid = db.get(Bid, bid_id)
    if bid is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bid not found")
    if not access.is_manager and (bid.vendor_id != access.vendor.id or bid.is_self):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bid not found")
    return bid


def _check_bid_type(value: str | None) -> None:
    if value is not None and value not in svc.BID_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bid category must be GeM or State govt")


def _check_dates(publish: date | None, end: date | None) -> None:
    if publish and end and end < publish:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The end date cannot be before the publish date")


# --------------------------------------------------------------------------- meta, detect, vendors

@router.get("/meta")
def meta(access: BidAccess = Depends(get_access)):
    return {
        "mode": access.mode,
        "can_override": access.can_override,
        "vendor_name": access.vendor.name_of_firm if access.vendor else None,
        "types": svc.TYPES,
        "bid_types": list(svc.BID_TYPES),
        "self_name": svc.SELF_NAME,
        "confirm_days": settings.bid_confirm_days,
        "submit_buffer_days": settings.bid_submit_buffer_days,
        "reminder_hour_ist": settings.bid_reminder_hour_ist,
        "today": svc.today_ist().isoformat(),
    }


@router.get("/detect")
def detect(text: str = Query(""), _: BidAccess = Depends(manager_access)):
    return svc.detect_category(text)


@router.get("/check-number", response_model=BidNumberCheck)
def check_number(
    number: str = Query("", max_length=120),
    exclude_id: int | None = Query(None),
    _: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
):
    """Is this bid number already entered? Used while typing in the bid form, before anything is saved."""
    exact = svc.find_bid_by_number(db, number)
    if exact is not None and exclude_id is not None and exact.id == exclude_id:
        exact = None
    return BidNumberCheck(
        exact=BidMini.model_validate(exact, from_attributes=True) if exact else None,
        similar=[BidMini.model_validate(b, from_attributes=True) for b in svc.similar_bids(db, number, exclude_id)],
    )


@router.get("/vendors", response_model=list[VendorPick])
def vendors(_: BidAccess = Depends(manager_access), db: Session = Depends(get_db)):
    """Allocation list: one entry per active vendor login, the same vendor record that login resolves to."""
    login_emails = {
        (e or "").strip().lower()
        for e in db.scalars(
            select(User.email).where(
                func.lower(User.role) == "vendor", User.is_active.is_(True), User.deleted_at.is_(None)
            )
        ).all()
        if e
    }
    # Pick the record the login itself resolves to (newest not-deleted record with that email, see
    # vendor_accounts), and only then drop it if it is switched off: a vendor must see the bids given to it.
    rows = db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None))).all()
    best: dict[str, Vendor] = {}
    for v in rows:
        key = (v.email or "").strip().lower()
        if key in login_emails and (key not in best or v.id > best[key].id):
            best[key] = v
    picked = sorted((v for v in best.values() if v.is_active), key=lambda v: (v.name_of_firm or "").lower())
    names = [(v.name_of_firm or "").strip().lower() for v in picked]
    return [
        VendorPick(
            id=v.id,
            vendor_code=v.vendor_code,
            name=v.name_of_firm if names.count((v.name_of_firm or "").strip().lower()) == 1 else f"{v.name_of_firm} ({v.email})",
            email=v.email,
        )
        for v in picked
    ]


# --------------------------------------------------------------------------- vendor lookup and requests

@router.get("/lookup", response_model=list[VendorLookupOut])
def lookup(q: str = Query("", max_length=120), access: BidAccess = Depends(get_access), db: Session = Depends(get_db)):
    """A vendor types part of a bid number. Tells what each match is, never who holds it."""
    if access.is_manager:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the vendor search")
    if len(svc.norm(q)) < 2:
        return []
    asked = {svc.norm(r.bid_number) for r in db.scalars(
        select(BidRequest).where(BidRequest.vendor_id == access.vendor.id, BidRequest.status == "Requested")
    ).all()}
    found = []
    for bid in db.scalars(select(Bid).order_by(Bid.end_date.desc())).all():
        if not svc.fuzzy_match(q, f"{bid.bid_number} {bid.title}"):
            continue
        svc.refresh_bid(db, bid)
        state = svc.availability_for(db, bid, access.vendor)
        found.append((svc.search_rank(q, bid.bid_number), VendorLookupOut(
            bid_number=bid.bid_number, title=bid.title, bid_type=bid.bid_type, product_category=bid.product_category,
            product_type=bid.product_type, end_date=bid.end_date, availability=state,
            already_requested=svc.norm(bid.bid_number) in asked, bid_id=bid.id if state == "mine" else None,
        )))
    _commit(db)
    found.sort(key=lambda x: x[0])
    return [item for _, item in found][:20]


@router.get("/requests", response_model=list[BidRequestOut])
def list_requests(
    state: str | None = Query(None, description="Requested, Allocated, Declined, Not available"),
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
):
    stmt = select(BidRequest)
    if not access.is_manager:
        stmt = stmt.where(BidRequest.vendor_id == access.vendor.id)
    if state:
        stmt = stmt.where(BidRequest.status == state)
    rows = db.scalars(stmt.order_by(BidRequest.id.desc()).limit(500)).all()
    return [_request_out(db, r, access) for r in rows]


@router.post("/requests", response_model=BidRequestOut, status_code=status.HTTP_201_CREATED)
def make_request(
    body: RequestIn,
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if access.is_manager:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a vendor can ask for a bid")
    try:
        req = svc.create_request(db, access.vendor, user, body.bid_number, body.note)
    except BidError as exc:
        _commit(db)  # keep any lock / close that refresh applied
        _fail(exc)
    _commit(db)
    return _request_out(db, req, access)


@router.post("/requests/{request_id}/allocate", response_model=BidOut)
def allocate_request(
    request_id: int,
    body: RequestDecisionIn | None = None,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = db.get(BidRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    try:
        bid = svc.allocate_from_request(db, req, user, can_override=access.can_override, reason=body.reason if body else None)
    except BidError as exc:
        db.rollback()
        svc.discard_outbox()
        _fail(exc)
    _commit(db)
    return _bid_out(db, bid, access, with_events=True, pending=_pending_counts(db))


@router.post("/requests/{request_id}/decline", response_model=BidRequestOut)
def decline_request(
    request_id: int,
    body: RequestDecisionIn | None = None,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = db.get(BidRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    try:
        svc.decline_request(db, req, user, body.note if body else None)
    except BidError as exc:
        db.rollback()
        svc.discard_outbox()
        _fail(exc)
    _commit(db)
    return _request_out(db, req, access)


@router.post("/run-rules")
def run_rules_now(
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
):
    """Run the lock / release / reminder rules right now (the server also runs them every 10 minutes)."""
    if not access.can_override:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin or sub admin can do this")
    return svc.run_rules(db, send_reminders=settings.bid_reminders_enabled)


# --------------------------------------------------------------------------- list, create, read, update

@router.get("", response_model=list[BidOut])
def list_bids(
    q: str | None = Query(None, max_length=120),
    state: str | None = Query(None, description="Live, or one status"),
    bid_type: str | None = Query(None),
    category: str | None = Query(None),
    product_type: str | None = Query(None),
    vendor_id: int | None = Query(None),
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
):
    stmt = select(Bid)
    if not access.is_manager:
        stmt = stmt.where(Bid.vendor_id == access.vendor.id, Bid.is_self.is_(False))
    if bid_type:
        stmt = stmt.where(Bid.bid_type == bid_type)
    if category:
        stmt = stmt.where(Bid.product_category == category)
    if product_type:
        stmt = stmt.where(Bid.product_type == product_type)
    if vendor_id and access.is_manager:
        stmt = stmt.where(Bid.vendor_id == vendor_id)
    bids = db.scalars(stmt.order_by(Bid.end_date.asc(), Bid.id.desc())).all()
    changed = False
    for bid in bids:
        if svc.refresh_bid(db, bid):
            changed = True
    if changed:
        _commit(db)
    if state == "Live":
        bids = [b for b in bids if b.status in svc.LIVE_STATUSES]
    elif state and state != "All":
        bids = [b for b in bids if b.status == state]
    lines_map = _lines_for(db, [b.id for b in bids])
    names: dict[int, str] = {}
    if access.is_manager and q:
        names = {v.id: v.name_of_firm for v in db.scalars(select(Vendor)).all()}
    if q and q.strip():
        scored = []
        for b in bids:
            text = " ".join(x for x in (
                b.bid_number, b.title, b.department, b.product_category, b.product_type,
                names.get(b.vendor_id) if b.vendor_id else None,
                svc.SELF_NAME if b.is_self else None,
                _line_text(lines_map.get(b.id, [])),
            ) if x)
            if svc.fuzzy_match(q, text):
                scored.append((svc.search_rank(q, b.bid_number), b))
        scored.sort(key=lambda x: x[0])
        bids = [b for _, b in scored]
    pending = _pending_counts(db) if access.is_manager else None
    return [_bid_out(db, b, access, pending=pending, lines_map=lines_map) for b in bids[:1000]]


@router.post("", response_model=BidOut, status_code=status.HTTP_201_CREATED)
def create_bid(
    body: BidIn,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _check_bid_type(body.bid_type)
    _check_dates(body.publish_date, body.end_date)
    number = body.bid_number.strip()
    if svc.find_bid_by_number(db, number) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This bid number is already entered")
    data = body.model_dump(exclude={"lines"})
    data["bid_number"] = number
    bid = Bid(**data, status="Open", created_by_id=user.id)
    svc.apply_category(bid)
    db.add(bid)
    db.flush()
    if body.lines:
        _save_lines(db, bid, body.lines)
    svc.add_event(db, bid, user, "entered", f"Bid entered ({bid.bid_type}{', ' + bid.portal if bid.portal else ''})")
    linked = svc.link_requests_to_bid(db, bid)
    if linked:
        svc.add_event(db, bid, user, "linked", f"{linked} vendor request{'s' if linked > 1 else ''} for this number linked to the bid")
    _commit(db)
    return _bid_out(db, bid, access, with_events=True, pending=_pending_counts(db))


@router.get("/{bid_id}", response_model=BidOut)
def get_bid(bid_id: int, access: BidAccess = Depends(get_access), db: Session = Depends(get_db)):
    bid = _get_bid(db, bid_id, access)
    if svc.refresh_bid(db, bid):
        _commit(db)
    return _bid_out(db, bid, access, with_events=True, pending=_pending_counts(db) if access.is_manager else None)


@router.put("/{bid_id}", response_model=BidOut)
def update_bid(
    bid_id: int,
    body: BidUpdate,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    data = body.model_dump(exclude_unset=True)
    new_lines = body.lines if "lines" in body.model_fields_set else None
    data.pop("lines", None)
    _check_bid_type(data.get("bid_type"))
    new_end = data.get("end_date", bid.end_date)
    _check_dates(data.get("publish_date", bid.publish_date), new_end)
    if "bid_number" in data:
        number = (data["bid_number"] or "").strip()
        other = svc.find_bid_by_number(db, number)
        if other is not None and other.id != bid.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "This bid number is already entered")
        data["bid_number"] = number
    for required in ("title", "end_date", "bid_number", "bid_type"):
        if required in data and data[required] in (None, ""):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{required.replace('_', ' ').capitalize()} cannot be empty")
    changed = [k for k, v in data.items() if getattr(bid, k) != v]
    for key, value in data.items():
        setattr(bid, key, value)
    lines_changed = _save_lines(db, bid, new_lines) if new_lines is not None else False
    if lines_changed:
        changed.append("items")
    if "product_category" in data or "product_type" in data:
        svc.apply_category(bid)
    if "end_date" in data and bid.status in ("Allocated", "Confirmed") and not bid.is_self:
        bid.submit_by = svc.dates_for_allocation(bid, svc.today_ist())[1]
    if changed:
        svc.add_event(db, bid, user, "edited", "Edited: " + ", ".join(k.replace("_", " ") for k in changed))
    _commit(db)
    return _bid_out(db, bid, access, with_events=True, pending=_pending_counts(db))


# --------------------------------------------------------------------------- workflow actions

def _act(db: Session, fn, bid: Bid, access: BidAccess, *args, **kwargs) -> BidOut:
    try:
        fn(db, bid, *args, **kwargs)
    except BidError as exc:
        _commit(db)  # keep what refresh applied (a release or a close)
        _fail(exc)
    _commit(db)
    return _bid_out(db, bid, access, with_events=True, pending=_pending_counts(db) if access.is_manager else None)


@router.post("/{bid_id}/allocate", response_model=BidOut)
def allocate(
    bid_id: int,
    body: AllocateIn,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    vendor = None
    if not body.self_bid:
        vendor = db.get(Vendor, body.vendor_id) if body.vendor_id else None
        if vendor is None or not vendor.is_active or vendor.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose an active vendor, or INDcool (Self)")
    return _act(
        db, svc.allocate_bid, bid, access,
        vendor=vendor, self_bid=body.self_bid, actor=user, can_override=access.can_override, reason=body.reason,
    )


@router.post("/{bid_id}/release", response_model=BidOut)
def release(
    bid_id: int,
    body: ReasonIn | None = None,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    if bid.status not in svc.HELD_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This bid is not allocated")
    if bid.status == "Submitted" and not access.can_override:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A submitted bid can only be taken back by an admin or sub admin")
    why = (body.reason if body else None) or "Released by the bid team"
    return _act(db, lambda d, b: svc.release_bid(d, b, why.strip(), user), bid, access)


@router.post("/{bid_id}/confirm", response_model=BidOut)
def confirm(
    bid_id: int,
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    return _act(db, svc.confirm_bid, bid, access, user, on_behalf=access.is_manager)


@router.post("/{bid_id}/decline", response_model=BidOut)
def decline(
    bid_id: int,
    body: ReasonIn | None = None,
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    return _act(db, svc.decline_bid, bid, access, user, body.reason if body else None)


@router.post("/{bid_id}/submit", response_model=BidOut)
def submit(
    bid_id: int,
    body: SubmitIn | None = None,
    access: BidAccess = Depends(get_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    return _act(db, svc.submit_bid, bid, access, user, body.reference if body else None)


@router.post("/{bid_id}/result", response_model=BidOut)
def result(
    bid_id: int,
    body: ResultIn,
    access: BidAccess = Depends(manager_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = _get_bid(db, bid_id, access)
    return _act(db, svc.set_result, bid, access, user, body.result, body.note)
