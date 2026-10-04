import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.item_master import ItemMaster
from app.models.user import User
from app.schemas.item_master import (
    ItemMasterCreate,
    ItemMasterListItem,
    ItemMasterListResponse,
    ItemMasterOut,
    ItemMasterUpdate,
)
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/items", tags=["item-masters"])


def _to_out(item: ItemMaster) -> ItemMasterOut:
    return ItemMasterOut(
        id=item.id,
        item_code=item.item_code,
        item_name=item.item_name,
        category=item.category,
        description=item.description,
        brand=item.brand,
        unit=item.unit,
        hsn_code=item.hsn_code,
        mrp=float(item.mrp) if item.mrp is not None else None,
        serial_count=item.serial_count,
        source=item.source or "Buy",
        item_type=item.item_type,
        gst_rate=float(item.gst_rate) if item.gst_rate is not None else None,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_list_item(item: ItemMaster) -> ItemMasterListItem:
    return ItemMasterListItem(
        id=item.id,
        item_code=item.item_code,
        item_name=item.item_name,
        category=item.category,
        brand=item.brand,
        unit=item.unit,
        hsn_code=item.hsn_code,
        mrp=float(item.mrp) if item.mrp is not None else None,
        serial_count=item.serial_count,
        source=item.source or "Buy",
        item_type=item.item_type,
        gst_rate=float(item.gst_rate) if item.gst_rate is not None else None,
        is_active=item.is_active,
        created_at=item.created_at,
    )


def _load(db: Session, user: User, item_id: int) -> ItemMaster:
    item = db.get(ItemMaster, item_id)
    if item is None or item.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if not can_act_on(db, user, "items", "can_view", None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.get("", response_model=ItemMasterListResponse)
def list_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "items", "can_view", None):
        return ItemMasterListResponse(items=[], total=0, page=page, per_page=per_page)

    stmt = select(ItemMaster).where(ItemMaster.deleted_at.is_(None))

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ItemMaster.item_code.ilike(like),
                ItemMaster.item_name.ilike(like),
                ItemMaster.brand.ilike(like),
            )
        )
    if category:
        stmt = stmt.where(ItemMaster.category == category)
    if is_active is not None:
        stmt = stmt.where(ItemMaster.is_active == is_active)

    stmt = stmt.order_by(desc(ItemMaster.created_at))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    return ItemMasterListResponse(
        items=[_to_list_item(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/export")
def export_csv(
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "items", "can_export", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot export items")

    stmt = select(ItemMaster).where(ItemMaster.deleted_at.is_(None))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ItemMaster.item_code.ilike(like),
                ItemMaster.item_name.ilike(like),
                ItemMaster.brand.ilike(like),
            )
        )
    if category:
        stmt = stmt.where(ItemMaster.category == category)
    if is_active is not None:
        stmt = stmt.where(ItemMaster.is_active == is_active)
    stmt = stmt.order_by(ItemMaster.item_code)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Item Code", "Item Name", "Category", "Brand",
        "Unit", "HSN Code", "MRP", "Serial Count", "Active", "Created At",
    ])
    for item in db.scalars(stmt).all():
        writer.writerow([
            item.id, item.item_code, item.item_name,
            item.category or "", item.brand or "",
            item.unit or "", item.hsn_code or "",
            float(item.mrp) if item.mrp is not None else "",
            item.serial_count,
            "Yes" if item.is_active else "No",
            item.created_at.isoformat(),
        ])
    buf.seek(0)
    filename = f"item_masters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/categories", response_model=list[str])
def list_item_categories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Distinct category values already used on items (for dropdowns)."""
    if not can_act_on(db, user, "items", "can_view", None):
        return []
    rows = db.scalars(
        select(ItemMaster.category)
        .where(
            ItemMaster.deleted_at.is_(None),
            ItemMaster.category.is_not(None),
            ItemMaster.category != "",
        )
        .distinct()
        .order_by(ItemMaster.category)
    ).all()
    return [row for row in rows if row]


@router.get("/{item_id}", response_model=ItemMasterOut)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _to_out(_load(db, user, item_id))


@router.post("", response_model=ItemMasterOut, status_code=status.HTTP_201_CREATED)
def create_item(
    body: ItemMasterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "items", "can_create", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create items")

    existing = db.scalar(
        select(ItemMaster).where(
            ItemMaster.item_code == body.item_code,
            ItemMaster.deleted_at.is_(None),
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Item code '{body.item_code}' already exists")

    item = ItemMaster(
        item_code=body.item_code,
        item_name=body.item_name,
        category=body.category,
        description=body.description,
        brand=body.brand,
        unit=body.unit,
        hsn_code=body.hsn_code,
        mrp=body.mrp,
        serial_count=body.serial_count,
        source=body.source,
        item_type=body.item_type,
        gst_rate=body.gst_rate,
        is_active=body.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.put("/{item_id}", response_model=ItemMasterOut)
def update_item(
    item_id: int,
    body: ItemMasterUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = _load(db, user, item_id)
    if not can_act_on(db, user, "items", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit items")

    data = body.model_dump(exclude_unset=True)

    if "item_code" in data and data["item_code"] != item.item_code:
        conflict = db.scalar(
            select(ItemMaster).where(
                ItemMaster.item_code == data["item_code"],
                ItemMaster.deleted_at.is_(None),
                ItemMaster.id != item_id,
            )
        )
        if conflict:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Item code '{data['item_code']}' already exists")

    for field, value in data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = _load(db, user, item_id)
    if not can_act_on(db, user, "items", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete items")
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
