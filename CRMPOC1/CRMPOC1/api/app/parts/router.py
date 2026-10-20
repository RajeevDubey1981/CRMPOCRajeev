"""HTTP endpoints for Parts: the spare-parts catalogue and the unified request/approval queue."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.parts import service as svc
from app.parts.access import Ctx, get_ctx, require_approvals_access, require_catalogue_edit
from app.parts.db import get_parts_db
from app.parts.models import ItemRequest, ItemRequestEvent, ItemRequestPhoto, SparePart, SparePartFitment
from app.parts.rules import KINDS, effective_required_photos, required_photos, stage_label
from app.services import date_range as dr
from app.services.file_service import save_upload
from app.services.serial_history import create_serial_history_event

router = APIRouter(prefix="/api/parts", tags=["parts"])

IMAGE_EXT = {".jpg", ".jpeg", ".png"}
IMAGE_MIME = {"image/jpeg", "image/jpg", "image/png"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024


def commit(db: Session, pdb: Session) -> None:
    pdb.commit()
    db.commit()


def _part_out(p: SparePart, fits: list[str]) -> dict:
    return {
        "id": p.id, "part_code": p.part_code, "part_name": p.part_name, "part_ean": p.part_ean,
        "category": p.category, "price": float(p.price) if p.price is not None else None,
        "engineer_visible": p.engineer_visible, "is_active": p.is_active, "fits": fits,
    }


def _req_out(r: ItemRequest, ctx: Ctx) -> dict:
    return {
        "id": r.id, "request_no": r.request_no, "kind": r.kind, "kind_label": KINDS.get(r.kind, r.kind),
        "crm_service_request_id": r.crm_service_request_id, "crm_service_request_no": r.crm_service_request_no,
        "crm_installation_request_id": r.crm_installation_request_id, "crm_installation_request_no": r.crm_installation_request_no,
        "crm_item_code": r.crm_item_code, "crm_item_name_cache": r.crm_item_name_cache, "crm_serial_no": r.crm_serial_no,
        "spare_part_id": r.spare_part_id, "part_name_cache": r.part_name_cache,
        "description": r.description,
        "amount": (float(r.amount) if r.amount is not None else None) if ctx.can_see_amounts else None,
        "stage": r.stage, "stage_label": stage_label(r.kind, r.amount, r.stage),
        "required_photos": effective_required_photos(r),
        "crm_query_id": r.crm_query_id,
        "crm_raised_by_user_id": r.crm_raised_by_user_id, "crm_raised_by_name": r.crm_raised_by_name,
        "request_date": r.request_date.isoformat(), "created_at": r.created_at, "decided_at": r.decided_at,
        "can_act": ctx.can_act_on_stage(r.stage),
    }


def _log_part_history(db: Session, req: ItemRequest, user: User, *, event_subtype: str, offset: int, event_at: datetime | None, title: str, description: str, extra: dict | None = None) -> None:
    """One entry on the Serial History timeline (PART_REPLACEMENT) for this request's lifecycle, so a
    serial's full history — parts/misc requests from either Service or Installation — shows in one place.
    offset keeps each lifecycle stage its own row instead of overwriting the previous one (same source_id
    would otherwise collide on the (source_table, source_id, event_type, serial_no) dedup key)."""
    if not req.crm_serial_no:
        return
    create_serial_history_event(
        db, serial_no=req.crm_serial_no, event_type="PART_REPLACEMENT", event_subtype=event_subtype,
        event_at=event_at or datetime.now(timezone.utc), performed_by_user_id=user.id, performed_by_name=user.name,
        source_table="parts_item_request", source_id=req.id + offset,
        title=title, description=description,
        metadata={"request_no": req.request_no, "kind": req.kind, "amount": float(req.amount) if req.amount is not None else None, **(extra or {})},
    )
    db.commit()


def _load_request(pdb: Session, request_id: int) -> ItemRequest:
    req = pdb.get(ItemRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return req


def _own_or_approver(ctx: Ctx, req: ItemRequest) -> None:
    if ctx.is_engineer and req.crm_raised_by_user_id != ctx.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if ctx.role == "sales":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")


# ============================================================= catalogue

@router.get("/catalogue")
def list_catalogue(
    search: str | None = None, crm_item_code: str | None = None,
    ctx: Ctx = Depends(get_ctx), pdb: Session = Depends(get_parts_db),
):
    stmt = select(SparePart).where(SparePart.is_active.is_(True))
    if ctx.is_engineer or ctx.role == "sales":
        stmt = stmt.where(SparePart.engineer_visible.is_(True))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where((SparePart.part_name.ilike(like)) | (SparePart.part_code.ilike(like)) | (SparePart.part_ean.ilike(like)))
    parts = pdb.scalars(stmt.order_by(SparePart.part_name)).all()
    if crm_item_code:
        fit_ids = set(pdb.scalars(select(SparePartFitment.spare_part_id).where(SparePartFitment.crm_item_code == crm_item_code)))
        parts = [p for p in parts if p.id in fit_ids]
    fitments = pdb.scalars(select(SparePartFitment).where(SparePartFitment.spare_part_id.in_([p.id for p in parts]))).all() if parts else []
    by_part: dict[int, list[str]] = {}
    for f in fitments:
        by_part.setdefault(f.spare_part_id, []).append(f.crm_item_code)
    return [_part_out(p, by_part.get(p.id, [])) for p in parts]


class SparePartIn(BaseModel):
    part_code: str = Field(min_length=2, max_length=100)
    part_name: str = Field(min_length=2, max_length=255)
    part_ean: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    engineer_visible: bool = True
    fits: list[str] = []


@router.post("/catalogue", status_code=status.HTTP_201_CREATED)
def create_part(body: SparePartIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    require_catalogue_edit(ctx, db, flag="can_create")
    if pdb.scalar(select(SparePart.id).where(SparePart.part_code == body.part_code)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Part code '{body.part_code}' already exists")
    part = SparePart(
        part_code=body.part_code, part_name=body.part_name, part_ean=body.part_ean, category=body.category,
        price=body.price, engineer_visible=body.engineer_visible, crm_created_by_user_id=ctx.user.id,
    )
    pdb.add(part)
    pdb.flush()
    for item_code in body.fits:
        pdb.add(SparePartFitment(spare_part_id=part.id, crm_item_code=item_code))
    pdb.commit()
    pdb.refresh(part)
    return _part_out(part, body.fits)


class SparePartPatch(BaseModel):
    part_name: Optional[str] = None
    part_ean: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    engineer_visible: Optional[bool] = None
    is_active: Optional[bool] = None


@router.put("/catalogue/{part_id}")
def update_part(part_id: int, body: SparePartPatch, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    require_catalogue_edit(ctx, db)
    part = pdb.get(SparePart, part_id)
    if part is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Part not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(part, field, value)
    pdb.commit()
    pdb.refresh(part)
    fits = list(pdb.scalars(select(SparePartFitment.crm_item_code).where(SparePartFitment.spare_part_id == part.id)))
    return _part_out(part, fits)


@router.post("/catalogue/{part_id}/fitments", status_code=status.HTTP_201_CREATED)
def add_fitment(part_id: int, crm_item_code: str = Form(...), crm_item_name_cache: str | None = Form(None), ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    require_catalogue_edit(ctx, db)
    if pdb.get(SparePart, part_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Part not found")
    if pdb.scalar(select(SparePartFitment.id).where(SparePartFitment.spare_part_id == part_id, SparePartFitment.crm_item_code == crm_item_code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Already fits this item code")
    f = SparePartFitment(spare_part_id=part_id, crm_item_code=crm_item_code, crm_item_name_cache=crm_item_name_cache)
    pdb.add(f)
    pdb.commit()
    return {"id": f.id, "crm_item_code": f.crm_item_code}


# ============================================================= requests

@router.get("/requests")
def list_requests(
    kind: str | None = None, stage: str | None = None, mine: bool = False,
    crm_service_request_id: int | None = None, crm_installation_request_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None,
    ctx: Ctx = Depends(get_ctx), pdb: Session = Depends(get_parts_db),
):
    if ctx.role == "sales":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if not ctx.is_engineer:
        require_approvals_access(ctx)
    stmt = select(ItemRequest)
    if ctx.is_engineer:
        stmt = stmt.where(ItemRequest.crm_raised_by_user_id == ctx.user.id)
    elif mine:
        stmt = stmt.where(ItemRequest.stage.in_([s for s in ("svm", "sub") if ctx.can_act_on_stage(s)]))
    if kind:
        stmt = stmt.where(ItemRequest.kind == kind)
    if stage:
        stmt = stmt.where(ItemRequest.stage == stage)
    if crm_service_request_id:
        stmt = stmt.where(ItemRequest.crm_service_request_id == crm_service_request_id)
    if crm_installation_request_id:
        stmt = stmt.where(ItemRequest.crm_installation_request_id == crm_installation_request_id)
    stmt = dr.registered_between(stmt, ItemRequest.created_at, date_from, date_to)
    rows = pdb.scalars(stmt.order_by(ItemRequest.id.desc())).all()
    return [_req_out(r, ctx) for r in rows]


class RequestIn(BaseModel):
    kind: str
    description: str = Field(min_length=3)
    crm_service_request_id: Optional[int] = None
    crm_service_request_no: Optional[str] = None
    crm_installation_request_id: Optional[int] = None
    crm_installation_request_no: Optional[str] = None
    crm_item_code: Optional[str] = None
    crm_item_name_cache: Optional[str] = None
    crm_serial_no: Optional[str] = None
    spare_part_id: Optional[int] = None
    part_name_cache: Optional[str] = None
    amount: Optional[Decimal] = None


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def raise_request(body: RequestIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    if body.kind not in KINDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown request kind")
    amount = body.amount
    if body.kind == "part" and body.spare_part_id and amount is None:
        part = pdb.get(SparePart, body.spare_part_id)
        amount = part.price if part else None
    req = svc.create_request(
        pdb, kind=body.kind, description=body.description, user=ctx.user,
        crm_service_request_id=body.crm_service_request_id, crm_service_request_no=body.crm_service_request_no,
        crm_installation_request_id=body.crm_installation_request_id, crm_installation_request_no=body.crm_installation_request_no,
        crm_item_code=body.crm_item_code, crm_item_name_cache=body.crm_item_name_cache, crm_serial_no=body.crm_serial_no,
        spare_part_id=body.spare_part_id, part_name_cache=body.part_name_cache, amount=amount,
    )
    pdb.commit()
    pdb.refresh(req)
    _log_part_history(
        db, req, ctx.user, event_subtype="REQUESTED", offset=0, event_at=req.created_at,
        title=f"{KINDS.get(req.kind, req.kind)} requested",
        description=f"{req.request_no}: {req.description[:200]}",
        extra={"service_request_no": req.crm_service_request_no, "installation_request_no": req.crm_installation_request_no},
    )
    return _req_out(req, ctx)


@router.get("/requests/{request_id}")
def get_request(request_id: int, ctx: Ctx = Depends(get_ctx), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    _own_or_approver(ctx, req)
    photos = pdb.scalars(select(ItemRequestPhoto).where(ItemRequestPhoto.item_request_id == req.id).order_by(ItemRequestPhoto.id)).all()
    events = pdb.scalars(select(ItemRequestEvent).where(ItemRequestEvent.item_request_id == req.id).order_by(ItemRequestEvent.id)).all()
    out = _req_out(req, ctx)
    out["photos"] = [{"id": p.id, "file_path": p.file_path, "label": p.label, "uploaded_at": p.uploaded_at} for p in photos]
    out["timeline"] = [{"id": e.id, "kind": e.kind, "text": e.text, "by_name": e.crm_by_name, "at": e.at} for e in events]
    return out


@router.post("/requests/{request_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(request_id: int, photo: UploadFile = File(...), label: str | None = Form(None), ctx: Ctx = Depends(get_ctx), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    if req.crm_raised_by_user_id != ctx.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who raised this request can add its photos")
    if req.stage != "svm" or svc.photo_count(pdb, req) >= 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Photos can only be added while the request is new")
    path = await save_upload(photo, module="parts", allowed_ext=IMAGE_EXT, allowed_mime=IMAGE_MIME, max_bytes=MAX_PHOTO_BYTES)
    row = svc.add_photo(pdb, req, file_path=path, label=label, user=ctx.user)
    pdb.commit()
    return {"id": row.id, "file_path": row.file_path, "label": row.label}


@router.post("/requests/{request_id}/approve")
def approve_request(request_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    if not ctx.can_act_on_stage(req.stage):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot approve this request at its current stage")
    try:
        svc.approve(pdb, req, user=ctx.user)
    except svc.NotReady as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except svc.WrongStage as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    pdb.commit()
    pdb.refresh(req)
    if req.stage == "done":
        _log_part_history(
            db, req, ctx.user, event_subtype="APPROVED", offset=1_000_000, event_at=req.decided_at,
            title=f"{KINDS.get(req.kind, req.kind)} approved", description=f"{req.request_no} approved.",
        )
    return _req_out(req, ctx)


class RejectIn(BaseModel):
    reason: str = Field(min_length=2)


@router.post("/requests/{request_id}/reject")
def reject_request(request_id: int, body: RejectIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    if not ctx.can_act_on_stage(req.stage):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot reject this request at its current stage")
    try:
        svc.reject(pdb, req, user=ctx.user, reason=body.reason)
    except svc.WrongStage as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    pdb.commit()
    pdb.refresh(req)
    _log_part_history(
        db, req, ctx.user, event_subtype="REJECTED", offset=2_000_000, event_at=req.decided_at,
        title=f"{KINDS.get(req.kind, req.kind)} rejected", description=f"{req.request_no} rejected: {body.reason}",
        extra={"reason": body.reason},
    )
    return _req_out(req, ctx)


class ResubmitIn(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None


@router.post("/requests/{request_id}/resubmit")
def resubmit_request(request_id: int, body: ResubmitIn, ctx: Ctx = Depends(get_ctx), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    if req.crm_raised_by_user_id != ctx.user.id and not ctx.is_second_stage:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who raised this request (or Admin) can resubmit it")
    try:
        svc.resubmit(pdb, req, user=ctx.user, description=body.description, amount=body.amount)
    except svc.WrongStage as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    pdb.commit()
    pdb.refresh(req)
    return _req_out(req, ctx)


class SuppliedIn(BaseModel):
    note: Optional[str] = None


@router.post("/requests/{request_id}/supplied")
def supplied_request(request_id: int, body: SuppliedIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    if ctx.is_engineer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the Service Manager, Admin or Sub Admin confirm supply")
    try:
        svc.mark_supplied(pdb, req, user=ctx.user, note=body.note)
    except svc.WrongStage as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    pdb.commit()
    pdb.refresh(req)
    _log_part_history(
        db, req, ctx.user, event_subtype="SUPPLIED", offset=3_000_000, event_at=None,
        title=f"{KINDS.get(req.kind, req.kind)} supplied",
        description=f"{req.request_no} marked supplied" + (f": {body.note}" if body.note else ""),
    )
    return _req_out(req, ctx)


class DiscussIn(BaseModel):
    message: str = Field(min_length=2)


@router.post("/requests/{request_id}/discuss")
def discuss_request(request_id: int, body: DiscussIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), pdb: Session = Depends(get_parts_db)):
    req = _load_request(pdb, request_id)
    _own_or_approver(ctx, req)
    if req.crm_query_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "A discussion is already open on this request; reply to it in Queries")
    q = svc.open_discuss(db, pdb, req, opener=ctx.user, message=body.message)
    commit(db, pdb)
    return {"crm_query_id": q.id}
