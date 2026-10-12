import csv
import io
import secrets
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.services.date_range import registered_between
from app.models.claim import Claim
from app.models.order import OrderItem
from app.models.user import User
from app.schemas.claim import (
    STATUSES,
    ClaimCreate,
    ClaimListItem,
    ClaimListResponse,
    ClaimOut,
    ClaimStatusUpdate,
    ClaimUpdate,
)
from app.services.permissions import can_act_on
from app.services.serial_history import EVENT_TYPES, create_serial_history_event

router = APIRouter(prefix="/api/claims", tags=["claims"])


def _generate_claim_id() -> str:
    return f"IND-CLM-{datetime.now().strftime('%Y%m%d')}-{secrets.randbelow(1_000_000):06d}"


def _hydrate(db: Session, claim: Claim) -> dict:
    processed_by_name = None
    if claim.processed_by:
        u = db.get(User, claim.processed_by)
        processed_by_name = u.name if u else None
    return {
        **{k: getattr(claim, k) for k in (
            "id", "claim_id", "order_no", "serial_number",
            "customer_name", "customer_contact", "customer_email",
            "status", "submitted_at", "processed_by", "notes",
            "bank_name", "account_holder_name", "account_number",
            "ifsc_code", "admin_remark", "created_at", "updated_at",
        )},
        "processed_by_name": processed_by_name,
    }


def _load(db: Session, user: User, claim_id: int) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    if not can_act_on(db, user, "claims", "can_view", None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    return claim


@router.get("", response_model=ClaimListResponse)
def list_claims(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: Literal[STATUSES] | None = Query(None, alias="status"),  # type: ignore[valid-type]
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_view", None):
        return ClaimListResponse(items=[], total=0, page=page, per_page=per_page)

    stmt = select(Claim)

    if status_filter:
        stmt = stmt.where(Claim.status == status_filter)

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Claim.claim_id.ilike(like),
                Claim.customer_name.ilike(like),
                Claim.customer_contact.ilike(like),
                Claim.order_no.ilike(like),
                Claim.serial_number.ilike(like),
            )
        )

    stmt = registered_between(stmt, Claim.created_at, date_from, date_to)
    stmt = stmt.order_by(desc(Claim.submitted_at))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    return ClaimListResponse(
        items=[
            ClaimListItem(
                id=c.id,
                claim_id=c.claim_id,
                order_no=c.order_no,
                serial_number=c.serial_number,
                customer_name=c.customer_name,
                customer_contact=c.customer_contact,
                status=c.status,
                submitted_at=c.submitted_at,
            )
            for c in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/export")
def export_csv(
    status_filter: Literal[STATUSES] | None = Query(None, alias="status"),  # type: ignore[valid-type]
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_export", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot export claims")

    stmt = select(Claim)

    if status_filter:
        stmt = stmt.where(Claim.status == status_filter)

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Claim.claim_id.ilike(like),
                Claim.customer_name.ilike(like),
                Claim.customer_contact.ilike(like),
                Claim.order_no.ilike(like),
                Claim.serial_number.ilike(like),
            )
        )

    stmt = registered_between(stmt, Claim.created_at, date_from, date_to)
    stmt = stmt.order_by(desc(Claim.submitted_at))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Claim ID", "Order No", "Serial No", "Customer", "Contact",
        "Email", "Status", "Submitted At",
    ])
    for c in db.scalars(stmt).all():
        writer.writerow([
            c.claim_id,
            c.order_no or "",
            c.serial_number or "",
            c.customer_name or "",
            c.customer_contact or "",
            c.customer_email or "",
            c.status,
            c.submitted_at.isoformat(),
        ])
    buf.seek(0)
    filename = f"claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    claim = _load(db, user, claim_id)
    return ClaimOut(**_hydrate(db, claim))


@router.post("", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def create_claim(
    body: ClaimCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "claims", "can_create", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create claims")

    linked_item_id = None
    if body.serial_number:
        linked_item = db.scalar(
            select(OrderItem).where(
                or_(
                    func.lower(OrderItem.serial_no) == func.lower(body.serial_number),
                    func.lower(OrderItem.serial_no_2) == func.lower(body.serial_number),
                )
            )
        )
        linked_item_id = linked_item.id if linked_item else None

    claim = Claim(
        claim_id=_generate_claim_id(),
        order_no=body.order_no,
        serial_number=body.serial_number,
        order_item_id=linked_item_id,
        customer_name=body.customer_name,
        customer_contact=body.customer_contact,
        customer_email=body.customer_email,
        notes=body.notes,
        bank_name=body.bank_name,
        account_holder_name=body.account_holder_name,
        account_number=body.account_number,
        ifsc_code=body.ifsc_code,
        status="Processing",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(claim)
    db.flush()
    if claim.serial_number:
        create_serial_history_event(
            db,
            serial_no=claim.serial_number,
            order_item_id=claim.order_item_id,
            event_type=EVENT_TYPES["CLAIM"],
            event_subtype="SUBMITTED",
            event_at=claim.submitted_at,
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="claims",
            source_id=claim.id,
            title="Warranty claim submitted",
            description=f"Claim {claim.claim_id} submitted with status {claim.status}.",
            remarks=claim.notes,
            metadata={"claim_id": claim.claim_id, "status": claim.status, "order_no": claim.order_no},
        )
    from app.services.pending_action_sync import sync_claim_pending_actions

    sync_claim_pending_actions(db, claim)
    db.commit()
    db.refresh(claim)
    return ClaimOut(**_hydrate(db, claim))


@router.put("/{claim_id}/status", response_model=ClaimOut)
def update_claim_status(
    claim_id: int,
    body: ClaimStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    claim = _load(db, user, claim_id)
    if not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this claim")

    claim.status = body.status
    if body.admin_remark is not None:
        claim.admin_remark = body.admin_remark
    claim.processed_by = user.id
    if claim.serial_number:
        create_serial_history_event(
            db,
            serial_no=claim.serial_number,
            order_item_id=claim.order_item_id,
            event_type=EVENT_TYPES["CLAIM"],
            event_subtype="STATUS_UPDATED",
            event_at=datetime.now(timezone.utc),
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="claims",
            source_id=claim.id + 1000000,
            title="Warranty claim updated",
            description=f"Claim {claim.claim_id} updated to status {claim.status}.",
            remarks=claim.admin_remark,
            metadata={"claim_id": claim.claim_id, "status": claim.status},
        )
    from app.services.pending_action_sync import sync_claim_pending_actions

    sync_claim_pending_actions(db, claim)
    db.commit()
    db.refresh(claim)
    return ClaimOut(**_hydrate(db, claim))


@router.put("/{claim_id}", response_model=ClaimOut)
def update_claim(
    claim_id: int,
    body: ClaimUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    claim = _load(db, user, claim_id)
    if not can_act_on(db, user, "claims", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this claim")

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(claim, field, value)
    db.commit()
    db.refresh(claim)
    return ClaimOut(**_hydrate(db, claim))


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    claim = _load(db, user, claim_id)
    if not can_act_on(db, user, "claims", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete this claim")
    db.delete(claim)
    db.commit()
