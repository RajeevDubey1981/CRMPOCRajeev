"""Builds a list/get/create/update/delete router for a simple master-data table shaped like
Courier -- a name plus optional contact_name/contact_mobile/email/address -- so Manufacturer and
Insurance masters don't each need their own copy of this CRUD scaffolding."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.permissions import can_act_on
from app.services.role_access import is_operations_admin


def make_master_router(
    *,
    model: Type,
    create_schema: Type,
    update_schema: Type,
    out_schema: Type,
    list_item_schema: Type,
    list_response_schema: Type,
    prefix: str,
    tag: str,
    permission_module: str,
    display_name: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def _require_admin(user: User):
        if not is_operations_admin(user):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Only Admin or Indcool users can access {display_name} Master.",
            )

    def _normalize_name(value: str | None) -> str:
        return (value or "").strip()

    def _ensure_unique_name(db: Session, name: str, *, exclude_id: int | None = None):
        normalized = _normalize_name(name)
        stmt = select(model).where(model.deleted_at.is_(None), func.lower(model.name) == normalized.lower())
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if db.scalar(stmt.limit(1)) is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A {display_name.lower()} with this name already exists.")

    def _to_out(row):
        return out_schema(
            id=row.id, name=row.name, contact_name=row.contact_name, contact_mobile=row.contact_mobile,
            email=row.email, address=row.address, created_at=row.created_at, updated_at=row.updated_at,
        )

    def _to_list_item(row):
        return list_item_schema(
            id=row.id, name=row.name, contact_name=row.contact_name, contact_mobile=row.contact_mobile,
            email=row.email, address=row.address, created_at=row.created_at,
        )

    def _load(db: Session, user: User, row_id: int):
        _require_admin(user)
        row = db.get(model, row_id)
        if row is None or row.deleted_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{display_name} not found")
        return row

    @router.get("", response_model=list_response_schema)
    def list_rows(
        page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200), search: str | None = None,
        db: Session = Depends(get_db), user: User = Depends(get_current_user),
    ):
        _require_admin(user)
        if not can_act_on(db, user, permission_module, "can_view", None):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot view {permission_module}")
        stmt = select(model).where(model.deleted_at.is_(None))
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(model.name.ilike(like), model.contact_name.ilike(like), model.contact_mobile.ilike(like)))
        stmt = stmt.order_by(desc(model.created_at))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
        return list_response_schema(items=[_to_list_item(r) for r in rows], total=total, page=page, per_page=per_page)

    @router.get("/export")
    def export_csv(search: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        _require_admin(user)
        if not can_act_on(db, user, permission_module, "can_export", None):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot export {permission_module}")
        stmt = select(model).where(model.deleted_at.is_(None))
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(model.name.ilike(like), model.contact_name.ilike(like), model.contact_mobile.ilike(like)))
        stmt = stmt.order_by(desc(model.created_at))
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Name", "Contact Name", "Mobile", "Email", "Address", "Created At"])
        for r in db.scalars(stmt).all():
            writer.writerow([r.id, r.name, r.contact_name or "", r.contact_mobile or "", r.email or "", r.address or "", r.created_at.isoformat()])
        buf.seek(0)
        filename = f"{permission_module}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(iter([buf.read()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @router.get("/{row_id}", response_model=out_schema)
    def get_row(row_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        _require_admin(user)
        return _to_out(_load(db, user, row_id))

    @router.post("", response_model=out_schema, status_code=status.HTTP_201_CREATED)
    def create_row(body: create_schema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        _require_admin(user)
        if not can_act_on(db, user, permission_module, "can_create", None):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot create {permission_module}")
        name = _normalize_name(body.name)
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required.")
        _ensure_unique_name(db, name)
        row = model(
            name=name,
            contact_name=(body.contact_name or "").strip() or None,
            contact_mobile=(body.contact_mobile or "").strip() or None,
            email=body.email,
            address=(body.address or "").strip() or None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_out(row)

    @router.put("/{row_id}", response_model=out_schema)
    def update_row(row_id: int, body: update_schema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        row = _load(db, user, row_id)
        _require_admin(user)
        if not can_act_on(db, user, permission_module, "can_edit", None):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot edit {permission_module}")
        data = body.model_dump(exclude_unset=True)
        if "name" in data:
            name = _normalize_name(data["name"])
            if not name:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required.")
            _ensure_unique_name(db, name, exclude_id=row.id)
            data["name"] = name
        if "contact_name" in data:
            data["contact_name"] = (data["contact_name"] or "").strip() or None
        if "contact_mobile" in data:
            data["contact_mobile"] = (data["contact_mobile"] or "").strip() or None
        if "address" in data:
            data["address"] = (data["address"] or "").strip() or None
        for field, value in data.items():
            setattr(row, field, value)
        db.commit()
        db.refresh(row)
        return _to_out(row)

    @router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_row(row_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        row = _load(db, user, row_id)
        _require_admin(user)
        if not can_act_on(db, user, permission_module, "can_delete", None):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot delete {permission_module}")
        row.deleted_at = datetime.now(timezone.utc)
        db.commit()

    return router
