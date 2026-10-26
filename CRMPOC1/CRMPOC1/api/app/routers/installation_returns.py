"""Audited row-level returns. A returned row stays in the installation history."""
import json
from html import escape
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models.installation import InstallationRequest, InstallationStatusLog
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.vendor import Vendor
from app.services.role_access import role_key
from app.services.installation_workflow import log_installation_action
from app.services.email_service import send_email

router = APIRouter(prefix="/api/installation-returns", tags=["installation returns"])
PENDING = "Pending Return Approval"
RETURNED = "Return Approved - Closed"
REVIEW_ROLES = {"admin", "sub_admin", "service", "service_manager", "indcool", "incool", "indcool_service", "indcool service"}
RETURNABLE = {"Assigned", "In Progress", "Serial Pending Verification", "Returned", "Rejected"}

class ReturnIn(BaseModel):
    installation_ids: list[int] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=2, max_length=4000)

class DecisionIn(BaseModel):
    decision: str
    remark: str = Field(min_length=2, max_length=4000)

def reviewer(user):
    return role_key(user.role) in REVIEW_ROLES

def visible(db, user, inst):
    if reviewer(user):
        return True
    if role_key(user.role) == "engineer":
        return inst.assigned_engineer == user.id
    if role_key(user.role) == "vendor":
        order = db.get(Order, inst.order_id) if inst.order_id else None
        if not order and inst.order_item_id:
            item = db.get(OrderItem, inst.order_item_id)
            order = db.get(Order, item.order_id) if item else None
        from app.routers.orders import _vendor_ids_for_user
        return bool(order and order.vendor_id in _vendor_ids_for_user(db, user))
    return False

def logs(db, inst_id):
    return db.scalars(select(InstallationStatusLog).where(InstallationStatusLog.installation_request_id == inst_id, InstallationStatusLog.action.like("Location Return%" )).order_by(InstallationStatusLog.id)).all()

@router.get("")
def queue(order_id: int | None = None, installation_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = select(InstallationStatusLog.installation_request_id).where(InstallationStatusLog.action == "Location Return Requested")
    stmt = select(InstallationRequest).where(InstallationRequest.id.in_(ids))
    if installation_id is not None:
        stmt = stmt.where(InstallationRequest.id == installation_id)
    rows = db.scalars(stmt.order_by(InstallationRequest.id.desc())).all()
    result = []
    for inst in rows:
        if not visible(db, user, inst):
            continue
        item = db.get(OrderItem, inst.order_item_id) if inst.order_item_id else None
        order = db.get(Order, inst.order_id or (item.order_id if item else 0))
        if order_id and (not order or order.id != order_id):
            continue
        engineer = db.get(User, inst.assigned_engineer) if inst.assigned_engineer else None
        history = logs(db, inst.id)
        result.append(dict(id=inst.id, order_no=order.order_no if order else None, item_code=item.item_code if item else None, product_name=inst.product_name, serial_no=inst.serial_no, serial_no_2=inst.serial_no_2, engineer_name=engineer.name if engineer else None, status=inst.status, can_review=reviewer(user), history=[dict(action=h.action, remark=h.remarks, at=h.created_at, actor_id=h.performed_by, actor_name=(db.get(User, h.performed_by).name if h.performed_by and db.get(User, h.performed_by) else "System")) for h in history]))
    return result

@router.post("")
def request_return(body: ReturnIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if role_key(user.role) != "engineer":
        raise HTTPException(403, "Only the assigned engineer can request a return")
    reason = body.reason.strip()
    if len(reason) < 2:
        raise HTTPException(400, "Enter a return reason")
    ids = sorted(set(body.installation_ids))
    rows = db.scalars(select(InstallationRequest).where(InstallationRequest.id.in_(ids)).order_by(InstallationRequest.id).with_for_update()).all()
    if len(rows) != len(ids) or any(r.assigned_engineer != user.id for r in rows):
        raise HTTPException(404, "Assigned installation row not found")
    for inst in rows:
        if inst.status not in RETURNABLE or not inst.serial_no:
            raise HTTPException(409, f"Installation #{inst.id} cannot be returned at its current stage")
    for inst in rows:
        previous = inst.status
        inst.status = PENDING
        log_installation_action(db, inst, action="Location Return Requested", user=user, old_status=previous, new_status=PENDING, remarks=reason, metadata={"previous_status": previous, "serial_no": inst.serial_no, "serial_no_2": inst.serial_no_2})
    db.commit()
    return {"returned_ids": ids}

@router.post("/{installation_id}/decision")
def decide(installation_id: int, body: DecisionIn, tasks: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not reviewer(user):
        raise HTTPException(403, "Only authorized service reviewers can decide returns")
    if body.decision not in {"approve", "reject"} or len(body.remark.strip()) < 2:
        raise HTTPException(400, "Choose a valid decision and enter a remark")
    inst = db.scalar(select(InstallationRequest).where(InstallationRequest.id == installation_id).with_for_update())
    if not inst:
        raise HTTPException(404, "Installation not found")
    history = logs(db, inst.id)
    requested = next((h for h in reversed(history) if h.action == "Location Return Requested"), None)
    if not requested:
        raise HTTPException(409, "No return request exists")
    item = db.scalar(select(OrderItem).where(OrderItem.id == inst.order_item_id).with_for_update()) if inst.order_item_id else None
    order = db.get(Order, inst.order_id or (item.order_id if item else 0))
    old = inst.status
    if old != PENDING:
        raise HTTPException(409, "Return is no longer awaiting approval")
    if body.decision == "reject":
        inst.status = json.loads(requested.metadata_json)["previous_status"]
        action = "Location Return Rejected"
    else:
        if not item:
            raise HTTPException(409, "Link this serial pair to its order item before approving its return")
        if tuple((v or "").strip().upper() for v in (item.serial_no, item.serial_no_2)) != tuple((v or "").strip().upper() for v in (inst.serial_no, inst.serial_no_2)):
            raise HTTPException(409, "Order serial pair changed; resolve the order linkage before approving this return")
        if not (inst.customer_email or (order.customer_email if order else None)):
            raise HTTPException(409, "Add a customer email before approving the return notification")
        inst.status = RETURNED
        item.installation_status = "Not Requested"
        action = "Location Return Approved"
    log_installation_action(db, inst, action=action, user=user, old_status=old, new_status=inst.status, remarks=body.remark.strip())
    db.commit()
    if body.decision == "approve":
        recipient = inst.customer_email or (order.customer_email if order else None)
        if recipient:
            text = f"Dear {inst.customer_name},\nOrder: {order.order_no if order else '-'}\nInstallation: #{inst.id}\nProduct: {inst.product_name or '-'} / {item.item_code or '-'}\nSerial 1: {inst.serial_no}\nSerial 2: {inst.serial_no_2 or '-'}\nReturn reason: {requested.remarks}\nThese products were not found at the installation location. Please verify the order details and confirm their actual location. The serial has been released from this installation request and can be submitted in a new installation request."
            tasks.add_task(send_email, recipient, f"Installation #{inst.id}: return approved", "<pre>" + escape(text) + "</pre>", text)
    return {"id": inst.id, "status": inst.status}
