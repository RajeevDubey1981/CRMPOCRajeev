"""Product Details (complaint model) dropdown — always available in every environment."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.complaint_models import COMPLAINT_MODEL_CATEGORY, COMPLAINT_MODEL_ITEMS
from app.models.item_master import ItemMaster
from app.schemas.complaint import ComplaintModelOption


def ensure_complaint_model_masters(db: Session) -> int:
    """Insert or repair rows in item_masters used by the Product Details dropdown."""
    changed = 0
    for code, name in COMPLAINT_MODEL_ITEMS:
        row = db.scalar(select(ItemMaster).where(ItemMaster.item_code == code))
        if row is None:
            db.add(
                ItemMaster(
                    item_code=code,
                    item_name=name,
                    category=COMPLAINT_MODEL_CATEGORY,
                    is_active=True,
                )
            )
            changed += 1
            continue
        repaired = False
        if row.category != COMPLAINT_MODEL_CATEGORY:
            row.category = COMPLAINT_MODEL_CATEGORY
            repaired = True
        if (row.item_name or "").strip() != name:
            row.item_name = name
            repaired = True
        if not row.is_active:
            row.is_active = True
            repaired = True
        if row.deleted_at is not None:
            row.deleted_at = None
            repaired = True
        if repaired:
            changed += 1
    if changed:
        db.commit()
    return changed


def list_complaint_model_options(db: Session) -> list[ComplaintModelOption]:
    ensure_complaint_model_masters(db)
    rows = db.scalars(
        select(ItemMaster)
        .where(
            ItemMaster.deleted_at.is_(None),
            ItemMaster.is_active.is_(True),
            ItemMaster.category == COMPLAINT_MODEL_CATEGORY,
        )
        .order_by(ItemMaster.item_name)
    ).all()
    if rows:
        return [
            ComplaintModelOption(id=row.id, item_code=row.item_code, item_name=row.item_name)
            for row in rows
        ]
    return [
        ComplaintModelOption(id=-(index + 1), item_code=code, item_name=name)
        for index, (code, name) in enumerate(COMPLAINT_MODEL_ITEMS)
    ]
