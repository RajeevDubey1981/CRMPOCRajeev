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
from app.models.field_photo import FieldPhoto
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
from app.services.serial_history import create_serial_history_event

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
RESP_LABEL = {"mfg": "Manufacturer", "trans": "Transporter", "ins": "Insurance", "company": "Company"}


def effective_required_photos(claim: ShortageClaim) -> int:
    """REQUIRED_PHOTOS (4), unless the claim's own override says otherwise — set to 0 when the engineer's
    serial-verification photos were already paired onto it at raise time."""
    if claim.required_photos_override is not None:
        return claim.required_photos_override
    return REQUIRED_PHOTOS


def can_act_on_stage(role: str, stage: str) -> bool:
    if stage == "svm":
        return role in SERVICE_MANAGER_ROLES or role in SERVICE_TEAM_ROLES or role in SECOND_STAGE_ROLES
    if stage == "sub":
        return role in SECOND_STAGE_ROLES
    return False


def forbid_self_decision(claim: ShortageClaim, user: User, role: str) -> None:
    """Whoever claimed it out can't also be the one who decides/approves it — Service Team and Service
    Manager must hand a claim they raised to someone else, same as everywhere else in the CRM. Admin/Sub
    Admin are the top of the chain and exempt."""
    if claim.raised_by_user_id == user.id and role not in SECOND_STAGE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You raised this claim — someone else needs to decide it")


def next_claim_no(db: Session) -> str:
    n = db.scalar(select(ShortageClaim.id).order_by(ShortageClaim.id.desc()).limit(1)) or 0
    while True:
        candidate = f"SHC-{n + 1:05d}"
        if not db.scalar(select(ShortageClaim.id).where(ShortageClaim.claim_no == candidate)):
            return candidate
        n += 1


def log(db: Session, claim: ShortageClaim, kind: str, text: str, user: User | None) -> None:
    db.add(ShortageClaimEvent(claim_id=claim.id, kind=kind, text=text, by_user_id=user.id if user else None))


def _party_given_by(db: Session, c: ShortageClaim) -> str | None:
    """Who said whom this claim is on (the Service Manager's decision), so Admin can see it."""
    if not c.responsible_type:
        return None
    event = db.scalars(
        select(ShortageClaimEvent).where(ShortageClaimEvent.claim_id == c.id, ShortageClaimEvent.kind == "decided").order_by(ShortageClaimEvent.id.desc())
    ).first()
    who = db.get(User, event.by_user_id) if event and event.by_user_id else None
    return who.name if who else None


def _out(db: Session, c: ShortageClaim, role: str, can_edit: bool, user_id: int | None = None) -> dict:
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
        "party_name": party_name, "party_given_by": _party_given_by(db, c), "resolution": c.resolution,
        "raised_by_user_id": c.raised_by_user_id, "raised_by_name": raised_by.name if raised_by else None,
        "photo_count": n_photos, "required_photos": effective_required_photos(c),
        "created_at": c.created_at, "decided_at": c.decided_at,
        "can_act": can_act_on_stage(role, c.stage) and can_edit,
        "can_approve": can_act_on_stage(role, c.stage) and can_edit and not (c.raised_by_user_id == user_id and role not in SECOND_STAGE_ROLES),
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
    item_request_id: Optional[int] = None, service_request_id: Optional[int] = None, serial_no: Optional[str] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_view", None):
        return []
    stmt = select(ShortageClaim)
    if flow:
        stmt = stmt.where(ShortageClaim.flow == flow)
    if item_request_id:
        stmt = stmt.where(ShortageClaim.item_request_id == item_request_id)
    if service_request_id:
        stmt = stmt.where(ShortageClaim.service_request_id == service_request_id)
    if serial_no:
        stmt = stmt.where(ShortageClaim.serial_no == serial_no)
    if responsible_type:
        stmt = stmt.where(ShortageClaim.responsible_type == responsible_type)
    if stage:
        stmt = stmt.where(ShortageClaim.stage == stage)
    stmt = dr.registered_between(stmt, ShortageClaim.created_at, date_from, date_to)
    rows = db.scalars(stmt.order_by(ShortageClaim.id.desc())).all()
    role = role_key(user.role)
    can_edit = can_act_on(db, user, "claims", "can_edit", None)
    out = [_out(db, c, role, can_edit, user.id) for c in rows]
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
    rows = [_out(db, c, role, can_edit, user.id) for c in db.scalars(stmt.order_by(ShortageClaim.id.desc())).all()]
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
    out = _out(db, claim, role, can_act_on(db, user, "claims", "can_edit", None), user.id)
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
    unit_id: Optional[int] = None
    item_code: Optional[str] = None
    serial_no: Optional[str] = None
    amount: Optional[float] = None
    responsible_type: Optional[str] = None
    vendor_id: Optional[int] = None
    courier_id: Optional[int] = None
    insurer_name: Optional[str] = None
    # Required for every flow except "service" — a service-flow claim is pinned on who's responsible
    # instead, right here at raise time.
    items: list[str] = Field(default_factory=list)


@router.post("", status_code=status.HTTP_201_CREATED)
def raise_claim(body: ClaimIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.flow not in ("service", "installation", "parts"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown flow")
    if body.flow == "service" and body.service_request_id is not None and db.get(ServiceRequest, body.service_request_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    if body.flow == "installation" and body.installation_request_id is not None and db.get(InstallationRequest, body.installation_request_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    if body.flow == "service" and body.unit_id is not None:
        # One claim per unit — raising a second one just duplicates the first instead of saying anything new.
        already = db.scalar(
            select(ShortageClaim.id)
            .where(ShortageClaim.service_request_id == body.service_request_id, ShortageClaim.serial_no == body.serial_no)
            .limit(1)
        )
        if already:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A claim has already been raised for this unit")
    if body.flow in ("parts", "service"):
        # Only whoever can act on the approval (Service Team, Service Manager, Admin/Sub Admin) may claim
        # it out — never the engineer, whether it's a parts request or a service unit's recommendation.
        role = role_key(user.role)
        if role not in SERVICE_MANAGER_ROLES and role not in SERVICE_TEAM_ROLES and role not in SECOND_STAGE_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot raise this claim")
    if body.flow != "service" and not body.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick what's missing")
    if body.flow in ("parts", "service") and not body.responsible_type:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick who this claim is on before sending it")
    if body.responsible_type is not None and body.responsible_type not in ("mfg", "trans", "ins", "company"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown responsible party type")
    if body.responsible_type == "mfg" and not body.vendor_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick the manufacturer")
    if body.responsible_type == "trans" and not body.courier_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick the transporter")
    if body.responsible_type == "ins" and not body.insurer_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name the insurer / policy")

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
    if body.flow == "service" and body.unit_id is not None:
        # The engineer already photographed this exact unit to verify its serial — pair those photos
        # onto the claim instead of making whoever's claiming it out take a fresh set of the same machine.
        field_photos = db.scalars(
            select(FieldPhoto).where(FieldPhoto.service_request_unit_id == body.unit_id).order_by(FieldPhoto.id)
        ).all()
        if field_photos:
            for fp in field_photos:
                db.add(ShortageClaimPhoto(claim_id=claim.id, file_path=fp.file_path, label="From serial verification", uploaded_by_user_id=fp.uploaded_by_user_id))
            claim.required_photos_override = 0
            log(db, claim, "photos_paired", f"{len(field_photos)} photo(s) from serial verification paired onto this claim", user)
    if claim.responsible_type:
        party = {"mfg": lambda: db.get(Vendor, claim.vendor_id).name_of_firm if claim.vendor_id else None,
                 "trans": lambda: db.get(Courier, claim.courier_id).courier_name if claim.courier_id else None,
                 "ins": lambda: claim.insurer_name,
                 "company": lambda: None}[claim.responsible_type]()
        log(db, claim, "decided", f"{user.name} pinned this on {RESP_LABEL[claim.responsible_type]}" + (f" — {party}" if party else ""), user)
    db.commit()
    db.refresh(claim)
    if claim.serial_no:
        create_serial_history_event(
            db, serial_no=claim.serial_no, event_type="CLAIM", event_subtype="MISSING_ITEM_RAISED",
            event_at=claim.created_at, performed_by_user_id=user.id, performed_by_name=user.name,
            source_table="shortage_claims", source_id=claim.id,
            title="Missing-item claim raised",
            description=f"{claim.claim_no}: {claim.description[:200]}",
            metadata={"claim_no": claim.claim_no, "flow": claim.flow, "amount": float(claim.amount) if claim.amount is not None else None},
        )
        db.commit()
    return _out(db, claim, role_key(user.role), can_act_on(db, user, "claims", "can_edit", None), user.id)


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
    forbid_self_decision(claim, user, role)
    if body.responsible_type not in ("mfg", "trans", "ins", "company"):
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
    party = {"mfg": lambda: db.get(Vendor, body.vendor_id).name_of_firm, "trans": lambda: db.get(Courier, body.courier_id).courier_name, "ins": lambda: body.insurer_name, "company": lambda: None}[body.responsible_type]()
    log(db, claim, "decided", f"{user.name} pinned this on {RESP_LABEL[body.responsible_type]}" + (f" — {party}" if party else ""), user)
    db.commit()
    db.refresh(claim)
    return _out(db, claim, role, True, user.id)  # can_edit already required to reach this point


@router.post("/{claim_id}/approve")
def approve(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = _load(db, user, claim_id)
    role = role_key(user.role)
    if not can_act_on_stage(role, claim.stage) or not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot approve this claim at its current stage")
    forbid_self_decision(claim, user, role)
    if claim.stage not in ("svm", "sub"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"This claim is already {claim.stage}")
    n_photos = len(db.scalars(select(ShortageClaimPhoto.id).where(ShortageClaimPhoto.claim_id == claim.id)).all())
    need = effective_required_photos(claim)
    if n_photos < need:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This claim needs {need} photos before it can be approved; it has {n_photos}")
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
    if claim.serial_no and claim.stage == "done":
        create_serial_history_event(
            db, serial_no=claim.serial_no, event_type="CLAIM", event_subtype="MISSING_ITEM_CLOSED",
            event_at=claim.decided_at, performed_by_user_id=user.id, performed_by_name=user.name,
            source_table="shortage_claims", source_id=claim.id + 1_000_000,
            title="Missing-item claim closed",
            description=f"{claim.claim_no} closed" + (f" — on {RESP_LABEL.get(claim.responsible_type)}" if claim.responsible_type else ""),
            metadata={"claim_no": claim.claim_no, "amount": float(claim.amount) if claim.amount is not None else None, "responsible_type": claim.responsible_type},
        )
        db.commit()
    return _out(db, claim, role, True, user.id)  # can_edit already required to reach this point


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
    if claim.serial_no:
        create_serial_history_event(
            db, serial_no=claim.serial_no, event_type="CLAIM", event_subtype="MISSING_ITEM_REJECTED",
            event_at=claim.decided_at, performed_by_user_id=user.id, performed_by_name=user.name,
            source_table="shortage_claims", source_id=claim.id + 2_000_000,
            title="Missing-item claim rejected",
            description=f"{claim.claim_no} rejected: {body.reason}",
            metadata={"claim_no": claim.claim_no, "reason": body.reason},
        )
        db.commit()
    return _out(db, claim, role, True, user.id)  # can_edit already required to reach this point
