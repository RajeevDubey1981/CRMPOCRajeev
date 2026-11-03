import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.courier import Courier
from app.models.order import Order
from app.models.user import User
from app.schemas.courier import (
    CourierCreate,
    CourierListItem,
    CourierListResponse,
    CourierOut,
    CourierUpdate,
)
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/couriers", tags=["couriers"])


from app.services.role_access import is_operations_admin


def _is_courier_admin(user: User) -> bool:
    return is_operations_admin(user)


def _require_courier_admin(user: User):
    if not _is_courier_admin(user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only Admin or Indcool users can access Courier Master.",
        )


def _normalize_courier_name(value: str | None) -> str:
    return (value or "").strip()


def _ensure_unique_courier_name(
    db: Session,
    courier_name: str,
    *,
    exclude_id: int | None = None,
):
    normalized = _normalize_courier_name(courier_name)
    stmt = select(Courier).where(
        Courier.deleted_at.is_(None),
        func.lower(Courier.courier_name) == normalized.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Courier.id != exclude_id)
    existing = db.scalar(stmt.limit(1))
    if existing is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A courier with this name already exists.",
        )


def _to_out(c: Courier) -> CourierOut:
    return CourierOut(
        id=c.id,
        courier_name=c.courier_name,
        contact_name=c.contact_name,
        contact_mobile=c.contact_mobile,
        email=c.email,
        address=c.address,
        courier_type=c.courier_type,
        gst_number=c.gst_number,
        pan_number=c.pan_number,
        cin=c.cin,
        registered_state=c.registered_state,
        bank_account_holder=c.bank_account_holder,
        bank_name=c.bank_name,
        bank_account_number=c.bank_account_number,
        bank_ifsc=c.bank_ifsc,
        bank_branch=c.bank_branch,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _to_list_item(c: Courier) -> CourierListItem:
    return CourierListItem(
        id=c.id,
        courier_name=c.courier_name,
        contact_name=c.contact_name,
        contact_mobile=c.contact_mobile,
        email=c.email,
        address=c.address,
        courier_type=c.courier_type,
        is_active=c.is_active,
        created_at=c.created_at,
    )


def _load(db: Session, user: User, courier_id: int) -> Courier:
    _require_courier_admin(user)
    c = db.get(Courier, courier_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Courier not found")
    return c


@router.get("", response_model=CourierListResponse)
def list_couriers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_courier_admin(user)
    if not can_act_on(db, user, "couriers", "can_view", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view couriers")

    stmt = select(Courier).where(Courier.deleted_at.is_(None))

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Courier.courier_name.ilike(like),
                Courier.contact_name.ilike(like),
                Courier.contact_mobile.ilike(like),
            )
        )

    stmt = stmt.order_by(desc(Courier.created_at))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    return CourierListResponse(
        items=[_to_list_item(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/export")
def export_csv(
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_courier_admin(user)
    if not can_act_on(db, user, "couriers", "can_export", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot export couriers")

    stmt = select(Courier).where(Courier.deleted_at.is_(None))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Courier.courier_name.ilike(like),
                Courier.contact_name.ilike(like),
                Courier.contact_mobile.ilike(like),
            )
        )
    stmt = stmt.order_by(desc(Courier.created_at))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Courier Name", "Contact Name", "Mobile", "Email", "Address", "Created At",
    ])
    for c in db.scalars(stmt).all():
        writer.writerow([
            c.id,
            c.courier_name,
            c.contact_name or "",
            c.contact_mobile or "",
            c.email or "",
            c.address or "",
            c.created_at.isoformat(),
        ])
    buf.seek(0)
    filename = f"couriers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{courier_id}", response_model=CourierOut)
def get_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_courier_admin(user)
    return _to_out(_load(db, user, courier_id))


@router.post("", response_model=CourierOut, status_code=status.HTTP_201_CREATED)
def create_courier(
    body: CourierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_courier_admin(user)
    if not can_act_on(db, user, "couriers", "can_create", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create couriers")

    courier_name = _normalize_courier_name(body.courier_name)
    if not courier_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Courier name is required.")
    _ensure_unique_courier_name(db, courier_name)

    courier = Courier(
        courier_name=courier_name,
        contact_name=(body.contact_name or "").strip() or None,
        contact_mobile=(body.contact_mobile or "").strip() or None,
        email=body.email,
        address=(body.address or "").strip() or None,
        courier_type=body.courier_type,
        gst_number=(body.gst_number or "").strip() or None,
        pan_number=(body.pan_number or "").strip() or None,
        cin=(body.cin or "").strip() or None,
        registered_state=(body.registered_state or "").strip() or None,
        bank_account_holder=(body.bank_account_holder or "").strip() or None,
        bank_name=(body.bank_name or "").strip() or None,
        bank_account_number=(body.bank_account_number or "").strip() or None,
        bank_ifsc=(body.bank_ifsc or "").strip() or None,
        bank_branch=(body.bank_branch or "").strip() or None,
    )
    db.add(courier)
    db.commit()
    db.refresh(courier)
    return _to_out(courier)


@router.put("/{courier_id}", response_model=CourierOut)
def update_courier(
    courier_id: int,
    body: CourierUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    courier = _load(db, user, courier_id)
    _require_courier_admin(user)
    if not can_act_on(db, user, "couriers", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit couriers")

    data = body.model_dump(exclude_unset=True)
    if "courier_name" in data:
        courier_name = _normalize_courier_name(data["courier_name"])
        if not courier_name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Courier name is required.")
        _ensure_unique_courier_name(db, courier_name, exclude_id=courier.id)
        data["courier_name"] = courier_name
    if "contact_name" in data:
        data["contact_name"] = (data["contact_name"] or "").strip() or None
    if "contact_mobile" in data:
        data["contact_mobile"] = (data["contact_mobile"] or "").strip() or None
    if "address" in data:
        data["address"] = (data["address"] or "").strip() or None

    for field, value in data.items():
        setattr(courier, field, value)

    db.commit()
    db.refresh(courier)
    return _to_out(courier)


@router.delete("/{courier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    courier = _load(db, user, courier_id)
    _require_courier_admin(user)
    if not can_act_on(db, user, "couriers", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete couriers")

    active_order = db.scalar(
        select(Order.id).where(
            Order.deleted_at.is_(None),
            Order.courier_id == courier.id,
            Order.status != "Delivered",
        ).limit(1)
    )
    if active_order is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This courier cannot be deleted because it is associated with one or more orders that have not been delivered.",
        )

    courier.deleted_at = datetime.now(timezone.utc)
    db.commit()
