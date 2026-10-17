from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.installation import HistoricalInstallationCompletion, InstallationRequest, InstallationStatusLog
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.payment import PaymentTransaction
from app.models.user import User
from app.services.file_service import save_upload
from app.services.pending_action_sync import sync_installation_pending_actions
from app.services.permissions import can_act_on
from app.services.serial_history import EVENT_TYPES, create_serial_history_event

router = APIRouter(prefix="/api/historical-installations", tags=["historical-installations"])


def _require_access(db: Session, user: User, action: str = "can_view") -> None:
    if not can_act_on(db, user, "historical_installations", action, None):
        message = "Your role cannot complete historical installations" if action == "can_edit" else "Your role cannot view historical installations"
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


def _serial(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _snapshot(order: Order, items: list[OrderItem], requests: list[InstallationRequest]) -> dict:
    return {
        "order_status": order.status,
        "order_updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": [
            {"id": row.id, "serial_no": row.serial_no, "serial_no_2": row.serial_no_2,
             "installation_status": row.installation_status,
             "updated_at": row.updated_at.isoformat() if row.updated_at else None}
            for row in items
        ],
        "installation_requests": [
            {"id": row.id, "order_item_id": row.order_item_id, "status": row.status,
             "payment_amount_requested": str(row.payment_amount_requested) if row.payment_amount_requested is not None else None,
             "payment_amount_paid": str(row.payment_amount_paid) if row.payment_amount_paid is not None else None,
             "payment_type_requested": row.payment_type_requested, "payment_type_paid": row.payment_type_paid,
             "updated_at": row.updated_at.isoformat() if row.updated_at else None}
            for row in requests
        ],
    }


def _token(snapshot: dict) -> str:
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load(db: Session, order_id: int, *, lock: bool = False):
    order_stmt = select(Order).where(Order.id == order_id, Order.deleted_at.is_(None))
    item_stmt = select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
    if lock:
        order_stmt, item_stmt = order_stmt.with_for_update(), item_stmt.with_for_update()
    order = db.scalar(order_stmt)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    items = list(db.scalars(item_stmt).all())
    item_ids = [row.id for row in items]
    request_stmt = select(InstallationRequest).where(
        or_(InstallationRequest.order_id == order_id, InstallationRequest.order_item_id.in_(item_ids))
    ).order_by(InstallationRequest.id)
    if lock:
        request_stmt = request_stmt.with_for_update()
    return order, items, list(db.scalars(request_stmt).all())


def _preview(db: Session, order_id: int) -> dict:
    order, items, requests = _load(db, order_id)
    by_item: dict[int, list[InstallationRequest]] = {}
    for request in requests:
        if request.order_item_id:
            by_item.setdefault(request.order_item_id, []).append(request)
    engineer_ids = {r.assigned_engineer for r in requests if r.assigned_engineer}
    item_master_ids = {i.item_id for i in items if i.item_id}
    users = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_(engineer_ids))).all()} if engineer_ids else {}
    masters = {m.id: m.item_name for m in db.scalars(select(ItemMaster).where(ItemMaster.id.in_(item_master_ids))).all()} if item_master_ids else {}
    rows = []
    active_count = completed_count = create_count = missing_count = 0
    requested_total = Decimal("0")
    for item in items:
        serial1, serial2 = _serial(item.serial_no), _serial(item.serial_no_2)
        linked = by_item.get(item.id, [])
        missing = not (serial1 or serial2)
        if missing:
            missing_count += 1
        elif not linked:
            create_count += 1
        for req in linked:
            if req.status == "Completed":
                completed_count += 1
            else:
                active_count += 1
                requested_total += Decimal(str(req.payment_amount_requested or 0))
        rows.append({
            "id": item.id, "item_code": item.item_code, "item_name": masters.get(item.item_id),
            "serial_no": serial1, "serial_no_2": serial2, "installation_status": item.installation_status,
            "missing_serial": missing,
            "installation_requests": [{
                "id": req.id, "status": req.status, "engineer_id": req.assigned_engineer,
                "engineer_name": users.get(req.assigned_engineer),
                "payment_amount_requested": float(req.payment_amount_requested) if req.payment_amount_requested is not None else None,
                "payment_amount_paid": float(req.payment_amount_paid) if req.payment_amount_paid is not None else None,
                "payment_type": req.payment_type_paid or req.payment_type_requested,
            } for req in linked],
        })
    snap = _snapshot(order, items, requests)
    return {
        "preview_token": _token(snap),
        "order": {"id": order.id, "order_no": order.order_no, "order_date": order.order_date,
                  "status": order.status, "customer_name": order.customer_name,
                  "customer_contact": order.customer_contact, "customer_city": order.customer_city,
                  "expected_delivery_date": order.expected_delivery_date,
                  "actual_delivery_date": order.actual_delivery_date},
        "items": rows,
        "summary": {"serial_items": len(items) - missing_count, "missing_serial_items": missing_count,
                    "requests_to_create": create_count, "requests_to_complete": active_count,
                    "requests_already_completed": completed_count,
                    "suggested_payment_total": float(requested_total)},
        "blocking_errors": [message for missing, message in (
            (not (order.customer_name or "").strip() and create_count > 0, "Customer name is required before historical requests can be created."),
            (not (order.customer_contact or "").strip() and create_count > 0, "Customer contact is required before historical requests can be created."),
            (len(items) - missing_count == 0, "The order has no serial-bearing item rows."),
        ) if missing],
    }


@router.get("/search")
def search_orders(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=20),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_access(db, user)
    pattern = f"%{q.strip()}%"
    rows = db.scalars(select(Order).where(Order.deleted_at.is_(None), func.lower(func.coalesce(Order.order_no, "")).like(func.lower(pattern))).order_by(Order.order_no).limit(limit)).all()
    return [{"order_id": row.id, "order_no": row.order_no, "customer_name": row.customer_name,
             "customer_contact": row.customer_contact, "status": row.status,
             "display_label": " | ".join(v for v in (row.order_no, row.customer_name, row.status) if v)} for row in rows]


@router.get("/{order_id}/preview")
def preview(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_access(db, user)
    return _preview(db, order_id)


def _allocate(total: Decimal, count: int) -> list[Decimal]:
    if count <= 0:
        return []
    paise = int((total * 100).quantize(Decimal("1"), rounding=ROUND_DOWN))
    base, remainder = divmod(paise, count)
    return [Decimal(base + (1 if index < remainder else 0)) / 100 for index in range(count)]


@router.post("/complete")
async def complete(
    payload: str = Form(...), proof: UploadFile | None = File(None),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require_access(db, user, "can_edit")
    try:
        body = json.loads(payload)
        order_id = int(body["order_id"])
        operation_key = str(body["operation_key"]).strip()
        preview_token = str(body["preview_token"]).strip()
        completion_date = date.fromisoformat(body["installation_date"])
        reason = str(body["reason"]).strip()
        payment_total = Decimal(str(body["payment_total"])).quantize(Decimal("0.01"))
        payment_type = str(body["payment_type"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid completion details")
    if not operation_key or len(operation_key) > 100 or not reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Operation key and reason are required")
    if completion_date > date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Installation date cannot be in the future")
    if payment_total < 0 or payment_type not in {"Cash", "UPI"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Enter a valid payment total and type")

    existing = db.scalar(select(HistoricalInstallationCompletion).where(HistoricalInstallationCompletion.operation_key == operation_key))
    if existing:
        return {"audit_id": existing.id, "order_id": existing.order_id, "idempotent": True,
                "created_count": existing.created_count, "completed_count": existing.completed_count,
                "skipped_count": existing.skipped_count, "incomplete_count": existing.incomplete_count}

    proof_path = await save_upload(proof, "historical_installations") if proof and proof.filename else None
    saved_file = settings.resolved_upload_dir / proof_path.removeprefix("/uploads/") if proof_path else None
    try:
        order, items, requests = _load(db, order_id, lock=True)
        before = _snapshot(order, items, requests)
        if _token(before) != preview_token:
            raise HTTPException(status.HTTP_409_CONFLICT, "Order data changed after preview. Reload and review it again.")
        serial_items = [row for row in items if _serial(row.serial_no) or _serial(row.serial_no_2)]
        if not serial_items:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The order has no serial-bearing item rows")
        by_item: dict[int, list[InstallationRequest]] = {}
        for request in requests:
            if request.order_item_id:
                by_item.setdefault(request.order_item_id, []).append(request)
        master_ids = {row.item_id for row in serial_items if row.item_id}
        item_names = {row.id: row.item_name for row in db.scalars(select(ItemMaster).where(ItemMaster.id.in_(master_ids))).all()} if master_ids else {}
        missing_request_items = [row for row in serial_items if not by_item.get(row.id)]
        if missing_request_items and (not (order.customer_name or "").strip() or not (order.customer_contact or "").strip()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer name and contact are required before historical requests can be created")

        event_at = datetime.combine(completion_date, time(hour=12), tzinfo=timezone.utc)
        affected: list[InstallationRequest] = []
        created_requests: list[InstallationRequest] = []
        status_logs: list[tuple[InstallationStatusLog, dict]] = []
        created_count = completed_count = skipped_count = 0
        for item in serial_items:
            linked = by_item.get(item.id, [])
            created = False
            if not linked:
                linked = [InstallationRequest(
                    source="historical", order_id=order.id, order_item_id=item.id,
                    customer_name=order.customer_name.strip(), contact_number=order.customer_contact.strip(),
                    customer_email=order.customer_email, address=order.customer_address,
                    state=order.customer_state, product_name=item_names.get(item.item_id) or item.item_code,
                    serial_no=_serial(item.serial_no), serial_no_2=_serial(item.serial_no_2),
                    request_date=event_at, created_by=user.id, status="Completed",
                    installation_date=event_at, work_report=reason,
                )]
                db.add(linked[0])
                db.flush()
                created_count += 1
                created = True
                created_requests.append(linked[0])
            if created:
                affected.append(linked[0])
                metadata = {"historical": True}
                log = InstallationStatusLog(
                    installation_request_id=linked[0].id, action="Historical request created",
                    old_status=None, new_status="Completed", performed_by=user.id,
                    performed_role=user.role, remarks=reason,
                    metadata_json=json.dumps(metadata),
                )
                db.add(log)
                status_logs.append((log, metadata))
            else:
                for inst in linked:
                    if inst.status == "Completed":
                        skipped_count += 1
                        continue
                    inst.order_id = inst.order_id or order.id
                    inst.serial_no = inst.serial_no or _serial(item.serial_no)
                    inst.serial_no_2 = inst.serial_no_2 or _serial(item.serial_no_2)
                    old_status = inst.status
                    old_payment = {"requested": str(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None,
                                   "paid": str(inst.payment_amount_paid) if inst.payment_amount_paid is not None else None,
                                   "type": inst.payment_type_paid or inst.payment_type_requested}
                    inst.status = "Completed"
                    inst.installation_date = event_at
                    inst.work_report = reason
                    metadata = {"historical": True, "old_payment": old_payment}
                    log = InstallationStatusLog(
                        installation_request_id=inst.id, action="Historical completion", old_status=old_status,
                        new_status="Completed", performed_by=user.id, performed_role=user.role, remarks=reason,
                        metadata_json=json.dumps(metadata),
                    )
                    db.add(log)
                    status_logs.append((log, metadata))
                    completed_count += 1
                    affected.append(inst)
            item.installation_status = "Completed"

        order.status = "Completed"
        allocations = _allocate(payment_total, len(affected))
        transaction = None
        if not affected and payment_total != 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment total must be zero when every installation request is already completed")
        if affected:
            transaction = PaymentTransaction(payment_type=payment_type, total_amount=payment_total,
                                             request_count=len(affected), recorded_by_user_id=user.id)
            db.add(transaction)
            db.flush()
            recorded_at = datetime.now(timezone.utc)
            for inst, amount in zip(sorted(affected, key=lambda row: row.id), allocations):
                inst.payment_amount_paid = amount
                inst.payment_type_paid = payment_type
                inst.payment_recorded_at = recorded_at
                inst.payment_recorded_by = user.id
                inst.payment_transaction_id = transaction.id
                inst.payment_approval_status = "Approved"
                inst.payment_approval_stage_label = "Completed"
                inst.payment_next_approver_role = None
                if proof_path:
                    inst.payment_proof_file_path = proof_path
                sync_installation_pending_actions(db, inst)

        audit = HistoricalInstallationCompletion(
            operation_key=operation_key, order_id=order.id, performed_by_user_id=user.id,
            performed_role=user.role, installation_date=event_at, reason=reason,
            payment_total=payment_total, payment_type=payment_type,
            payment_transaction_id=transaction.id if transaction else None, proof_file_path=proof_path,
            before_json=json.dumps(before, sort_keys=True), after_json="{}",
            created_count=created_count, completed_count=completed_count, skipped_count=skipped_count,
            incomplete_count=len(items) - len(serial_items),
        )
        db.add(audit)
        db.flush()
        for log, metadata in status_logs:
            log.metadata_json = json.dumps({**metadata, "audit_id": audit.id})
        for item in serial_items:
            serial = _serial(item.serial_no) or _serial(item.serial_no_2)
            create_serial_history_event(
                db, serial_no=serial, serial_no_2=_serial(item.serial_no_2), order_item_id=item.id,
                event_type=EVENT_TYPES["INSTALLATION"], event_subtype="HISTORICAL_COMPLETION",
                event_at=event_at, performed_by_user_id=user.id, performed_by_name=user.name,
                source_table="historical_installation_completions", source_id=audit.id,
                title="Historical installation completed",
                description=f"Order {order.order_no or order.id} was completed through the historical installation tool.",
                remarks=reason, metadata={"audit_id": audit.id, "payment_transaction_id": transaction.id if transaction else None},
            )
        db.flush()
        audit.after_json = json.dumps(_snapshot(order, items, list(requests) + created_requests), sort_keys=True)
        db.commit()
        return {"audit_id": audit.id, "order_id": order.id, "order_no": order.order_no,
                "created_count": created_count, "completed_count": completed_count,
                "skipped_count": skipped_count, "incomplete_count": len(items) - len(serial_items),
                "payment_transaction_id": transaction.id if transaction else None, "idempotent": False}
    except Exception:
        db.rollback()
        if saved_file and saved_file.exists():
            saved_file.unlink()
        raise
