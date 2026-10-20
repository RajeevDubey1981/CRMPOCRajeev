"""Missing-item claims: something that should have been in the box (copper pipe, remote, gas charge ...) wasn't
there when the technical team opened it, during installation or a later service visit. Raised from inside the
real Service/Installation step; decided (manufacturer, transporter or insurance, and on whose account) and
approved the same two-stage way as everything else in the CRM; kept as a permanent register.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
import csv
import io

from app.database import get_db
from app.deps import get_current_user
from app.models.courier import Courier
from app.models.installation import InstallationRequest
from app.models.service import ServiceRequest
from app.models.shortage_claim import (
    REQUIRED_PHOTOS,
    ShortageClaim,
    ShortageClaimEvent,
    ShortageClaimItem,
    ShortageClaimPhoto,
)
from app.models.user import User
from app.models.vendor import Vendor
from app.services import date_range as dr
from app.services.file_service import save_upload
from app.services.permissions import can_act_on
from app.services.role_access import role_key

router = APIRouter(prefix="/api/shortage-claims", tags=["shortage-claims"])

SERVICE_MANAGER_ROLES = frozenset({"service_manager"})
SECOND_STAGE_ROLES = frozenset({"admin", "incool", "sub_admin"})
# Service Team can claim it out too, same as when deciding a parts request's approval.
SERVICE_TEAM_ROLES = frozenset({"service", "indcool_service", "indcool", "indcool service"})
APPROVAL_CAP_AMOUNT = 2500
IMAGE_EXT = {".jpg", ".jpeg", ".png"}
IMAGE_MIME = {"image/jpeg", "image/jpg", "image/png"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024

ITEMS_MISSING = ["Copper pipe", "Remote control", "Gas charge", "Stabilizer", "Drain pipe", "Power cord", "Installation kit", "Other"]
RESP_LABEL = {"mfg": "Manufacturer", "trans": "Transporter", "ins": "Insurance"}


def can_act_on_stage(role: str, stage: str) -> bool:
    if stage == "svm":
        return role in SERVICE_MANAGER_ROLES or role in SERVICE_TEAM_ROLES or role in SECOND_STAGE_ROLES
    if stage == "sub":
        return role in SECOND_STAGE_ROLES
    return False


def next_claim_no(db: Session) -> str:
    n = db.scalar(select(ShortageClaim.id).order_by(ShortageClaim.id.desc()).limit(1)) or 0
    while True:
        candidate = f"SHC-{n + 1:05d}"
        if not db.scalar(select(ShortageClaim.id).where(ShortageClaim.claim_no == candidate)):
            return candidate
        n += 1


def log(db: Session, claim: ShortageClaim, kind: str, text: str, user: User | None) -> None:
    db.add(ShortageClaimEvent(claim_id=claim.id, kind=kind, text=text, by_user_id=user.id if user else None))


def _out(db: Session, c: ShortageClaim, role: str, can_edit: bool) -> dict:
    items = list(db.scalars(select(ShortageClaimItem.label).where(ShortageClaimItem.claim_id == c.id)))
    n_photos = len(db.scalars(select(ShortageClaimPhoto.id).where(ShortageClaimPhoto.claim_id == c.id)).all())
    raised_by = db.get(User, c.raised_by_user_id)
    party_name = None
    if c.responsible_type == "mfg" and c.vendor_id:
        v = db.get(Vendor, c.vendor_id)
        party_name = v.name_of_firm if v else None
    elif c.responsible_type == "trans" and c.courier_id:
        co = db.get(Courier, c.courier_id)
        party_name = co.courier_name if co else None
    elif c.responsible_type == "ins":
        party_name = c.insurer_name
    return {
        "id": c.id, "claim_no": c.claim_no, "flow": c.flow,
        "service_request_id": c.service_request_id, "installation_request_id": c.installation_request_id,
        "item_request_id": c.item_request_id, "amount": float(c.amount) if c.amount is not None else None,
        "item_code": c.item_code, "serial_no": c.serial_no, "items": items,
        "description": c.description, "stage": c.stage,
        "responsible_type": c.responsible_type, "responsible_label": RESP_LABEL.get(c.responsible_type),
        "party_name": party_name, "resolution": c.resolution,
        "raised_by_user_id": c.raised_by_user_id, "raised_by_name": raised_by.name if raised_by else None,
        "photo_count": n_photos, "required_photos": REQUIRED_PHOTOS,
        "created_at": c.created_at, "decided_at": c.decided_at,
        "can_act": can_act_on_stage(role, c.stage) and can_edit,
    }


def _load(db: Session, user: User, claim_id: int) -> ShortageClaim:
    claim = db.get(ShortageClaim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    if not can_act_on(db, user, "claims", "can_view", None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    return claim


# ============================================================= list / export

@router.get("")
def list_claims(
    flow: Optional[str] = None, item: Optional[str] = None, responsible_type: Optional[str] = None,
    stage: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_view", None):
        return []
    stmt = select(ShortageClaim)
    if flow:
        stmt = stmt.where(ShortageClaim.flow == flow)
    if responsible_type:
        stmt = stmt.where(ShortageClaim.responsible_type == responsible_type)
    if stage:
        stmt = stmt.where(ShortageClaim.stage == stage)
    stmt = dr.registered_between(stmt, ShortageClaim.created_at, date_from, date_to)
    rows = db.scalars(stmt.order_by(ShortageClaim.id.desc())).all()
    role = role_key(user.role)
    can_edit = can_act_on(db, user, "claims", "can_edit", None)
    out = [_out(db, c, role, can_edit) for c in rows]
    if item:
        out = [o for o in out if item in o["items"]]
    return out


@router.get("/export")
def export_csv(
    flow: Optional[str] = None, item: Optional[str] = None, responsible_type: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_export", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot export claims")
    role = role_key(user.role)
    can_edit = can_act_on(db, user, "claims", "can_edit", None)
    stmt = select(ShortageClaim)
    if flow:
        stmt = stmt.where(ShortageClaim.flow == flow)
    if responsible_type:
        stmt = stmt.where(ShortageClaim.responsible_type == responsible_type)
    stmt = dr.registered_between(stmt, ShortageClaim.created_at, date_from, date_to)
    rows = [_out(db, c, role, can_edit) for c in db.scalars(stmt.order_by(ShortageClaim.id.desc())).all()]
    if item:
        rows = [r for r in rows if item in r["items"]]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Claim No", "Date", "Flow", "Item(s)", "Raised by", "Responsible party", "Party name", "Status", "Resolution"])
    for r in rows:
        writer.writerow([
            r["claim_no"], r["created_at"].date().isoformat(), r["flow"], "; ".join(r["items"]), r["raised_by_name"] or "",
            r["responsible_label"] or "", r["party_name"] or "", r["stage"], r["resolution"] or "",
        ])
    buf.seek(0)
    filename = f"shortage_claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(iter([buf.read()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/parties")
def list_parties(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Vendors and couriers, for the "on whose account" picker."""
    if not can_act_on(db, user, "claims", "can_view", None):
        return {"vendors": [], "couriers": []}
    vendors = db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None)).order_by(Vendor.name_of_firm)).all()
    couriers = db.scalars(select(Courier).where(Courier.deleted_at.is_(None)).order_by(Courier.courier_name)).all()
    return {
        "vendors": [{"id": v.id, "name": v.name_of_firm} for v in vendors],
        "couriers": [{"id": c.id, "name": c.courier_name} for c in couriers],
    }


# ============================================================= detail

@router.get("/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = _load(db, user, claim_id)
    role = role_key(user.role)
    out = _out(db, claim, role, can_act_on(db, user, "claims", "can_edit", None))
    photos = db.scalars(select(ShortageClaimPhoto).where(ShortageClaimPhoto.claim_id == claim.id).order_by(ShortageClaimPhoto.id)).all()
    events = db.scalars(select(ShortageClaimEvent).where(ShortageClaimEvent.claim_id == claim.id).order_by(ShortageClaimEvent.id)).all()
    out["photos"] = [{"id": p.id, "file_path": p.file_path, "label": p.label, "uploaded_at": p.uploaded_at} for p in photos]
    names = {}
    for e in events:
        if e.by_user_id and e.by_user_id not in names:
            u = db.get(User, e.by_user_id)
            names[e.by_user_id] = u.name if u else None
    out["timeline"] = [{"id": e.id, "kind": e.kind, "text": e.text, "by_name": names.get(e.by_user_id), "at": e.at} for e in events]
    return out


# ============================================================= raise

class ClaimIn(BaseModel):
    flow: str
    description: str = Field(min_length=3)
    service_request_id: Optional[int] = None
    installation_request_id: Optional[int] = None
    item_request_id: Optional[int] = None
    item_code: Optional[str] = None
    serial_no: Optional[str] = None
    amount: Optional[float] = None
    responsible_type: Optional[str] = None
    vendor_id: Optional[int] = None
    courier_id: Optional[int] = None
    insurer_name: Optional[str] = None
    items: list[str] = Field(min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def raise_claim(body: ClaimIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.flow not in ("service", "installation", "parts"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown flow")
    if body.flow == "service" and body.service_request_id is not None and db.get(ServiceRequest, body.service_request_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    if body.flow == "installation" and body.installation_request_id is not None and db.get(InstallationRequest, body.installation_request_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    if body.flow == "parts":
        # Only whoever can act on a parts request's approval (Service Team, Service Manager, Admin/Sub Admin)
        # may claim it out from there — never the engineer who raised the request.
        role = role_key(user.role)
        if role not in SERVICE_MANAGER_ROLES and role not in SERVICE_TEAM_ROLES and role not in SECOND_STAGE_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot claim out a parts request")
    if body.responsible_type is not None and body.responsible_type not in ("mfg", "trans", "ins"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown responsible party type")

    claim = ShortageClaim(
        claim_no=next_claim_no(db), flow=body.flow, service_request_id=body.service_request_id,
        installation_request_id=body.installation_request_id, item_request_id=body.item_request_id,
        item_code=body.item_code, serial_no=body.serial_no, amount=body.amount,
        responsible_type=body.responsible_type,
        vendor_id=body.vendor_id if body.responsible_type == "mfg" else None,
        courier_id=body.courier_id if body.responsible_type == "trans" else None,
        insurer_name=body.insurer_name if body.responsible_type == "ins" else None,
        description=body.description, stage="svm", raised_by_user_id=user.id,
    )
    db.add(claim)
    db.flush()
    for label in body.items:
        db.add(ShortageClaimItem(claim_id=claim.id, label=label))
    log(db, claim, "raised", f"Claim raised by {user.name}", user)
    if claim.responsible_type:
        party = {"mfg": lambda: db.get(Vendor, claim.vendor_id).name_of_firm if claim.vendor_id else None,
                 "trans": lambda: db.get(Courier, claim.courier_id).courier_name if claim.courier_id else None,
                 "ins": lambda: claim.insurer_name}[claim.responsible_type]()
        log(db, claim, "decided", f"{user.name} pinned this on {RESP_LABEL[claim.responsible_type]}" + (f" — {party}" if party else ""), user)
    db.commit()
    db.refresh(claim)
    return _out(db, claim, role_key(user.role), can_act_on(db, user, "claims", "can_edit", None))


@router.post("/{claim_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(claim_id: int, photo: UploadFile = File(...), label: Optional[str] = Form(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.get(ShortageClaim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    if claim.raised_by_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who raised this claim can add its photos")
    if claim.stage != "svm":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Photos can only be added while the claim is new")
    existing = len(db.scalars(select(ShortageClaimPhoto.id).where(ShortageClaimPhoto.claim_id == claim.id)).all())
    if existing >= 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many photos on this claim")
    path = await save_upload(photo, module="shortage_claims", allowed_ext=IMAGE_EXT, allowed_mime=IMAGE_MIME, max_bytes=MAX_PHOTO_BYTES)
    row = ShortageClaimPhoto(claim_id=claim.id, file_path=path, label=label, uploaded_by_user_id=user.id)
    db.add(row)
    db.commit()
    return {"id": row.id, "file_path": row.file_path, "label": row.label}


# ============================================================= decide / approve / reject

class DecideIn(BaseModel):
    responsible_type: str
    vendor_id: Optional[int] = None
    courier_id: Optional[int] = None
    insurer_name: Optional[str] = None
    amount: Optional[float] = None


@router.post("/{claim_id}/decide")
def decide(claim_id: int, body: DecideIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = _load(db, user, claim_id)
    role = role_key(user.role)
    if not can_act_on_stage(role, claim.stage) or not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot decide this claim at its current stage")
    if body.responsible_type not in ("mfg", "trans", "ins"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown responsible party type")
    if body.responsible_type == "mfg" and not body.vendor_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick the manufacturer")
    if body.responsible_type == "trans" and not body.courier_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick the transporter")
    if body.responsible_type == "ins" and not body.insurer_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name the insurer / policy")
    claim.responsible_type = body.responsible_type
    claim.vendor_id = body.vendor_id if body.responsible_type == "mfg" else None
    claim.courier_id = body.courier_id if body.responsible_type == "trans" else None
    claim.insurer_name = body.insurer_name if body.responsible_type == "ins" else None
    if body.amount is not None:
        claim.amount = body.amount
    party = {"mfg": lambda: db.get(Vendor, body.vendor_id).name_of_firm, "trans": lambda: db.get(Courier, body.courier_id).courier_name, "ins": lambda: body.insurer_name}[body.responsible_type]()
    log(db, claim, "decided", f"{user.name} pinned this on {RESP_LABEL[body.responsible_type]} — {party}", user)
    db.commit()
    db.refresh(claim)
    return _out(db, claim, role, True)  # can_edit already required to reach this point


@router.post("/{claim_id}/approve")
def approve(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = _load(db, user, claim_id)
    role = role_key(user.role)
    if not can_act_on_stage(role, claim.stage) or not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot approve this claim at its current stage")
    if claim.stage not in ("svm", "sub"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"This claim is already {claim.stage}")
    n_photos = len(db.scalars(select(ShortageClaimPhoto.id).where(ShortageClaimPhoto.claim_id == claim.id)).all())
    if n_photos < REQUIRED_PHOTOS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This claim needs {REQUIRED_PHOTOS} photos before it can be approved; it has {n_photos}")
    if not claim.responsible_type:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decide who is responsible before approving")
    if claim.stage == "svm":
        # Service Manager can close a claim outright at or under the cap; above it, or with no amount
        # recorded, it still needs Admin/Sub Admin — same rule as the service-unit recommendation chain.
        # Service Team always forwards: they recommend, they never finalize.
        can_finalize_at_svm = role in SERVICE_MANAGER_ROLES and claim.amount is not None and float(claim.amount) <= APPROVAL_CAP_AMOUNT
        claim.stage = "done" if can_finalize_at_svm else "sub"
    else:
        claim.stage = "done"
    if claim.stage == "done":
        claim.decided_at = datetime.now(timezone.utc)
        claim.decided_by_user_id = user.id
    text = f"Claimed by {user.name}" + (" (forwarded to Admin/Sub Admin)" if claim.stage == "sub" else " — closed")
    log(db, claim, "approved", text, user)
    db.commit()
    db.refresh(claim)
    return _out(db, claim, role, True)  # can_edit already required to reach this point


class RejectIn(BaseModel):
    reason: str = Field(min_length=2)


@router.post("/{claim_id}/reject")
def reject(claim_id: int, body: RejectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = _load(db, user, claim_id)
    role = role_key(user.role)
    if not can_act_on_stage(role, claim.stage) or not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot reject this claim at its current stage")
    if claim.stage not in ("svm", "sub"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"This claim is already {claim.stage}")
    claim.stage = "rejected"
    claim.decided_at = datetime.now(timezone.utc)
    claim.decided_by_user_id = user.id
    log(db, claim, "rejected", f"Rejected by {user.name}: {body.reason}", user)
    db.commit()
    db.refresh(claim)
    return _out(db, claim, role, True)  # can_edit already required to reach this point
