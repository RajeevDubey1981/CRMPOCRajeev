"""Call-center installation workflow helpers."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.complaint import Complaint
from app.models.installation import InstallationDocument, InstallationEngineerSerial, InstallationRequest, InstallationStatusLog
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.serial_history import SerialHistoryEvent
from app.models.user import User
from app.services.file_service import save_upload, to_public_upload_path
from app.services.role_access import is_operations_admin
from app.services.service_documents import (
    CUSTOMER_DOCUMENT_EXTENSIONS,
    CUSTOMER_DOCUMENT_MIME_TYPES,
    CUSTOMER_DOCUMENT_TYPES,
    build_public_upload_url,
)

INSTALLATION_SOURCES = {"vendor", "callcenter"}
BILLING_TYPES = {"Free", "Paid"}
COMPLETION_PROOF_SERIAL_2_TYPE = "Completion Proof - Serial 2"
CUSTOMER_DOCUMENT_OPTIONS = sorted(CUSTOMER_DOCUMENT_TYPES)
PRE_ORDER_VERIFIED_STATUSES = {"Pending", "Document Requested", "Admin Review Document"}
CALLCENTER_ASSIGNABLE_STATUSES = {
    "Pending",
    "Document Requested",
    "Admin Review Document",
    "Order Verified",
    "Assigned",
    "In Progress",
    "Serial Pending Verification",
}
CALLCENTER_NON_ASSIGNABLE_STATUSES = {
    "Installation Completed",
    "Payment Pending",
    "Completed",
    "Settlement Pending",
    "Settlement Approved",
    "Returned",
    "Rejected",
}


def callcenter_can_assign_engineer(inst: InstallationRequest) -> bool:
    """Allow (re)assignment until admin verifies serials — same engineer may hold multiple units on one order."""
    if inst.serial_verified_at:
        return False
    return inst.status not in CALLCENTER_NON_ASSIGNABLE_STATUSES


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_access_token() -> str:
    return secrets.token_urlsafe(24)


def is_callcenter_source(inst: InstallationRequest) -> bool:
    return (inst.source or "vendor").lower() == "callcenter"


def is_vendor_source(inst: InstallationRequest) -> bool:
    return (inst.source or "vendor").lower() == "vendor"


def is_vendor_initiated_workflow(inst: InstallationRequest) -> bool:
    return is_vendor_source(inst) and bool(inst.order_item_id or inst.order_id)


def is_vendor_assigned_engineer_workflow(inst: InstallationRequest) -> bool:
    return is_vendor_initiated_workflow(inst) and inst.assigned_engineer is not None


def supports_engineer_installation_workflow(inst: InstallationRequest) -> bool:
    """Call-center requests and vendor requests assigned to an engineer share post-assign workflow APIs."""
    return is_callcenter_source(inst) or is_vendor_assigned_engineer_workflow(inst)


def prepare_vendor_installation_for_engineer_workflow(
    db: Session,
    inst: InstallationRequest,
    *,
    actor: User | None = None,
) -> bool:
    """Vendor order submissions already include order + serials — unlock engineer workflow on assign."""
    if not is_vendor_assigned_engineer_workflow(inst):
        return False

    changed = False
    now = now_utc()
    if not inst.order_id and inst.order_item_id:
        item = db.get(OrderItem, inst.order_item_id)
        if item is not None:
            inst.order_id = item.order_id
            changed = True
    if inst.order_id and not inst.order_verified_at:
        inst.order_verified_at = now
        if actor is not None:
            inst.order_verified_by = actor.id
        changed = True
    if (inst.serial_no or "").strip() and not inst.serial_verified_at:
        inst.serial_verified_at = now
        if actor is not None:
            inst.serial_verified_by = actor.id
        if not (inst.engineer_entered_serial_no or "").strip():
            inst.engineer_entered_serial_no = inst.serial_no
        changed = True
    if (inst.admin_billing_type or "Free").strip() != "Paid" and (inst.status or "") not in {"Completed", "Rejected"}:
        inst.admin_billing_type = "Paid"
        changed = True
    elif not inst.admin_billing_type:
        inst.admin_billing_type = "Paid"
        changed = True
    return changed


def log_installation_action(
    db: Session,
    inst: InstallationRequest,
    *,
    action: str,
    user: User | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
    remarks: str | None = None,
    metadata: dict | None = None,
    performed_role: str | None = None,
) -> None:
    db.add(
        InstallationStatusLog(
            installation_request_id=inst.id,
            action=action,
            old_status=old_status if old_status is not None else inst.status,
            new_status=new_status if new_status is not None else inst.status,
            performed_by=user.id if user else None,
            performed_role=performed_role or (user.role if user else None),
            remarks=remarks,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=now_utc(),
        )
    )
    from app.services.pending_action_sync import sync_installation_pending_actions

    sync_installation_pending_actions(db, inst)


def resolve_order_context(db: Session, inst: InstallationRequest) -> tuple[str | None, int | None]:
    if inst.order_item_id:
        item = db.get(OrderItem, inst.order_item_id)
        if item is not None:
            order = db.get(Order, item.order_id)
            if order is not None:
                return order.order_no, order.id
    if inst.order_id:
        order = db.get(Order, inst.order_id)
        if order is not None:
            return order.order_no, order.id
    return None, inst.order_id


def ensure_document_token(inst: InstallationRequest) -> str:
    if not inst.document_access_token:
        inst.document_access_token = generate_access_token()
    return inst.document_access_token


def validate_customer_document_upload(document_type: str, file: UploadFile) -> None:
    if document_type not in CUSTOMER_DOCUMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid document type: {document_type}")
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is required")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    content_type = (file.content_type or "").lower()
    if ext not in CUSTOMER_DOCUMENT_EXTENSIONS and content_type not in CUSTOMER_DOCUMENT_MIME_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF, JPG, JPEG, and PNG files are allowed")


def find_order_item_by_serial_on_order(db: Session, order_id: int, serial_no: str, serial_no_2: str | None = None) -> OrderItem | None:
    serial = serial_no.strip()
    serial2 = (serial_no_2 or "").strip()
    terms = [func.lower(OrderItem.serial_no) == func.lower(serial)]
    if serial2:
        terms.append(func.lower(OrderItem.serial_no_2) == func.lower(serial2))
        terms.append(func.lower(OrderItem.serial_no) == func.lower(serial2))
        terms.append(func.lower(OrderItem.serial_no_2) == func.lower(serial))
    return db.scalar(
        select(OrderItem).where(
            OrderItem.order_id == order_id,
            or_(*terms),
        )
    )


def associate_serial_with_order(
    db: Session,
    *,
    order_id: int,
    serial_no: str,
    serial_no_2: str | None = None,
    actor: User,
    inst: InstallationRequest,
) -> OrderItem:
    existing = find_order_item_by_serial_on_order(db, order_id, serial_no, serial_no_2)
    if existing is not None:
        return existing

    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
    ).all()
    for item in items:
        if not (item.serial_no or "").strip() and not (item.serial_no_2 or "").strip():
            item.serial_no = serial_no.strip()
            if serial_no_2 and serial_no_2.strip():
                item.serial_no_2 = serial_no_2.strip()
            item.installation_status = "Submitted"
            log_installation_action(
                db,
                inst,
                action="Serial Associated With Order",
                user=actor,
                remarks=f"Serial {serial_no} associated with order item #{item.id}",
                metadata={"order_item_id": item.id, "serial_no": serial_no, "serial_no_2": serial_no_2},
            )
            return item

    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order has no line items to attach a serial number")

    template = items[0]
    new_item = OrderItem(
        order_id=order_id,
        item_id=template.item_id,
        item_code=template.item_code,
        serial_no=serial_no.strip(),
        serial_no_2=(serial_no_2 or "").strip() or None,
        item_qty=template.item_qty,
        pcb_warranty_years=template.pcb_warranty_years,
        component_warranty_years=template.component_warranty_years,
        machine_warranty_years=template.machine_warranty_years,
        free_service_count=template.free_service_count,
        dry_free_service_count=template.dry_free_service_count,
        wet_free_service_count=template.wet_free_service_count,
        service_consume_count=template.service_consume_count,
        installation_status="Submitted",
    )
    db.add(new_item)
    db.flush()
    log_installation_action(
        db,
        inst,
        action="Serial Added To Order",
        user=actor,
        remarks=f"New order line created with serial {serial_no}",
        metadata={"order_item_id": new_item.id, "serial_no": serial_no, "serial_no_2": serial_no_2},
    )
    return new_item


def _normalize_serial(value: str | None) -> str:
    return (value or "").strip().lower()


def _serial_slots_on_item(item: OrderItem) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []
    if (item.serial_no or "").strip():
        slots.append(("serial1", item.serial_no.strip()))
    if (item.serial_no_2 or "").strip():
        slots.append(("serial2", item.serial_no_2.strip()))
    return slots


def _clone_order_item_row(
    source: OrderItem,
    *,
    serial_no: str | None,
    serial_no_2: str | None,
    installation_status: str,
) -> OrderItem:
    return OrderItem(
        order_id=source.order_id,
        item_id=source.item_id,
        item_code=source.item_code,
        serial_no=serial_no,
        serial_no_2=serial_no_2,
        item_qty=source.item_qty,
        pcb_warranty_years=source.pcb_warranty_years,
        component_warranty_years=source.component_warranty_years,
        machine_warranty_years=source.machine_warranty_years,
        free_service_count=source.free_service_count,
        dry_free_service_count=source.dry_free_service_count,
        wet_free_service_count=source.wet_free_service_count,
        service_consume_count=source.service_consume_count,
        installation_status=installation_status,
    )


def _serial_values_from_slots(slots: list[tuple[str, str]]) -> tuple[str | None, str | None]:
    serial_no = next((value for slot, value in slots if slot == "serial1"), None)
    serial_no_2 = next((value for slot, value in slots if slot == "serial2"), None)
    return serial_no, serial_no_2


def _assert_order_item_can_be_rearranged(
    db: Session,
    item_id: int,
    *,
    exclude_installation_id: int | None = None,
) -> None:
    blocking_claim = db.scalar(select(Claim.id).where(Claim.order_item_id == item_id).limit(1))
    if blocking_claim is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This serial row is already linked to a claim and cannot be rearranged",
        )
    blocking_complaint = db.scalar(
        select(func.count()).select_from(Complaint).where(Complaint.order_item_id == item_id)
    )
    if blocking_complaint:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This serial row is already linked to a complaint and cannot be rearranged",
        )
    blocking_installation_stmt = select(InstallationRequest.id).where(
        InstallationRequest.order_item_id == item_id,
        InstallationRequest.status.notin_(("Rejected", "Completed")),
    )
    if exclude_installation_id is not None:
        blocking_installation_stmt = blocking_installation_stmt.where(
            InstallationRequest.id != exclude_installation_id
        )
    blocking_installation = db.scalar(blocking_installation_stmt.limit(1))
    if blocking_installation is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This serial row is already linked to another active installation request",
        )


def _replace_order_item_row(
    db: Session,
    source: OrderItem,
    *,
    locked_slots: list[tuple[str, str]],
    open_slots: list[tuple[str, str]],
    exclude_installation_id: int | None = None,
) -> OrderItem:
    _assert_order_item_can_be_rearranged(
        db,
        source.id,
        exclude_installation_id=exclude_installation_id,
    )
    locked_serial_no, locked_serial_no_2 = _serial_values_from_slots(locked_slots)
    locked_item = _clone_order_item_row(
        source,
        serial_no=locked_serial_no,
        serial_no_2=locked_serial_no_2,
        installation_status="Submitted",
    )
    db.add(locked_item)
    db.flush()

    if open_slots:
        open_serial_no, open_serial_no_2 = _serial_values_from_slots(open_slots)
        open_item = _clone_order_item_row(
            source,
            serial_no=open_serial_no,
            serial_no_2=open_serial_no_2,
            installation_status="Not Requested",
        )
        db.add(open_item)

    db.query(SerialHistoryEvent).filter(
        SerialHistoryEvent.order_item_id == source.id
    ).update(
        {SerialHistoryEvent.order_item_id: None},
        synchronize_session=False,
    )
    db.delete(source)
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Verified serial row is still referenced elsewhere and could not be locked. Please refresh the order and try again.",
        )
    return locked_item


def lock_order_item_for_verified_serial(
    db: Session,
    *,
    order_id: int,
    serial_no: str,
    serial_no_2: str | None,
    actor: User,
    inst: InstallationRequest,
) -> OrderItem:
    """Lock verified serial(s) on the order at slot level, matching vendor submit behaviour."""
    serial = serial_no.strip()
    serial2 = (serial_no_2 or "").strip() or None
    if not serial:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required")

    verified_values = {_normalize_serial(serial)}
    if serial2:
        verified_values.add(_normalize_serial(serial2))

    item = find_order_item_by_serial_on_order(db, order_id, serial, serial2)
    if item is None:
        item = find_order_item_by_serial_on_order(db, order_id, serial, None)
    if item is None:
        locked_item = associate_serial_with_order(
            db,
            order_id=order_id,
            serial_no=serial,
            serial_no_2=serial2,
            actor=actor,
            inst=inst,
        )
        log_installation_action(
            db,
            inst,
            action="Serial Locked On Order",
            user=actor,
            remarks=f"Verified serial {serial} locked on order item #{locked_item.id}",
            metadata={
                "order_item_id": locked_item.id,
                "serial_no": serial,
                "serial_no_2": serial2,
            },
        )
        return locked_item

    if (item.installation_status or "Not Requested") != "Not Requested":
        return item

    slots_on_item = _serial_slots_on_item(item)
    matched_slots = [
        (slot, value) for slot, value in slots_on_item if _normalize_serial(value) in verified_values
    ]
    unmatched_slots = [
        (slot, value) for slot, value in slots_on_item if _normalize_serial(value) not in verified_values
    ]
    if not matched_slots:
        locked_item = associate_serial_with_order(
            db,
            order_id=order_id,
            serial_no=serial,
            serial_no_2=serial2,
            actor=actor,
            inst=inst,
        )
        log_installation_action(
            db,
            inst,
            action="Serial Locked On Order",
            user=actor,
            remarks=f"Verified serial {serial} locked on order item #{locked_item.id}",
            metadata={
                "order_item_id": locked_item.id,
                "serial_no": serial,
                "serial_no_2": serial2,
            },
        )
        return locked_item

    if not unmatched_slots:
        item.installation_status = "Submitted"
        log_installation_action(
            db,
            inst,
            action="Serial Locked On Order",
            user=actor,
            remarks=f"Verified serial {serial} locked on order item #{item.id}",
            metadata={
                "order_item_id": item.id,
                "serial_no": serial,
                "serial_no_2": serial2,
            },
        )
        return item

    locked_item = _replace_order_item_row(
        db,
        item,
        locked_slots=matched_slots,
        open_slots=unmatched_slots,
        exclude_installation_id=inst.id,
    )
    source_item_id = item.id
    log_installation_action(
        db,
        inst,
        action="Serial Locked On Order",
        user=actor,
        remarks=f"Verified serial {serial} locked on order item #{locked_item.id}",
        metadata={
            "order_item_id": locked_item.id,
            "serial_no": serial,
            "serial_no_2": serial2,
            "split_from_order_item_id": source_item_id,
        },
    )
    return locked_item


def apply_verified_serial_to_installation(
    db: Session,
    inst: InstallationRequest,
    item: OrderItem | None,
    *,
    actor: User,
    override_serial_no: str | None = None,
    override_serial_no_2: str | None = None,
) -> None:
    serial_no = (override_serial_no or inst.engineer_entered_serial_no or (item.serial_no if item else None) or "").strip()
    serial_no_2 = (override_serial_no_2 or inst.engineer_entered_serial_no_2 or (item.serial_no_2 if item else None) or "").strip() or None
    if override_serial_no and item is not None and item.order_id != inst.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial override must belong to the linked order")
    if override_serial_no:
        log_installation_action(
            db,
            inst,
            action="Serial Override",
            user=actor,
            remarks=f"Admin corrected serial to {serial_no}",
            metadata={"serial_no": serial_no, "serial_no_2": serial_no_2},
        )
    if not inst.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must be verified before serial verification")
    locked_item = lock_order_item_for_verified_serial(
        db,
        order_id=inst.order_id,
        serial_no=serial_no,
        serial_no_2=serial_no_2,
        actor=actor,
        inst=inst,
    )
    inst.order_item_id = locked_item.id
    inst.serial_no = serial_no
    inst.serial_no_2 = serial_no_2
    if locked_item.item_code and not inst.product_name:
        inst.product_name = locked_item.item_code


def resolve_order_item_for_serial(
    db: Session,
    *,
    order_id: int,
    serial_no: str,
    serial_no_2: str | None,
    actor: User,
    inst: InstallationRequest,
) -> OrderItem:
    return lock_order_item_for_verified_serial(
        db,
        order_id=order_id,
        serial_no=serial_no,
        serial_no_2=serial_no_2,
        actor=actor,
        inst=inst,
    )


def _copy_installation_shell(
    source: InstallationRequest,
    *,
    parent_installation_id: int | None = None,
) -> InstallationRequest:
    return InstallationRequest(
        complaint_id=source.complaint_id,
        customer_name=source.customer_name,
        contact_number=source.contact_number,
        customer_email=source.customer_email,
        address=source.address,
        source=source.source,
        order_id=source.order_id,
        created_by=source.created_by,
        assigned_engineer=source.assigned_engineer,
        document_access_token=source.document_access_token,
        ask_for_documents=source.ask_for_documents,
        document_request_sent_at=source.document_request_sent_at,
        order_verified_at=source.order_verified_at,
        order_verified_by=source.order_verified_by,
        engineer_site_remarks=source.engineer_site_remarks,
        engineer_serials_submitted_at=source.engineer_serials_submitted_at,
        parent_installation_id=parent_installation_id,
        request_date=source.request_date,
        status="Assigned",
    )


def _apply_verified_serial_line_to_request(
    db: Session,
    inst: InstallationRequest,
    serial_row: InstallationEngineerSerial,
    *,
    actor: User,
    billing_type: str,
    overall_remark: str | None,
) -> InstallationRequest:
    if not inst.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must be verified before serial verification")
    apply_verified_serial_to_installation(
        db,
        inst,
        None,
        actor=actor,
        override_serial_no=serial_row.serial_no,
        override_serial_no_2=serial_row.serial_no_2,
    )
    inst.admin_billing_type = billing_type
    inst.admin_approval_remark = overall_remark
    inst.admin_approved_at = now_utc()
    inst.admin_approved_by = actor.id
    inst.serial_verified_at = now_utc()
    inst.serial_verified_by = actor.id
    inst.engineer_entered_serial_no = serial_row.serial_no
    inst.engineer_entered_serial_no_2 = serial_row.serial_no_2
    inst.status = "Assigned"
    serial_row.split_installation_request_id = inst.id
    return inst


def split_installations_from_approved_serials(
    db: Session,
    inst: InstallationRequest,
    approved_rows: list[InstallationEngineerSerial],
    *,
    actor: User,
    billing_type: str,
    overall_remark: str | None,
) -> list[InstallationRequest]:
    if not approved_rows:
        return []
    approved_rows = sorted(approved_rows, key=lambda row: (row.line_no, row.id))
    results: list[InstallationRequest] = []

    primary = approved_rows[0]
    _apply_verified_serial_line_to_request(
        db,
        inst,
        primary,
        actor=actor,
        billing_type=billing_type,
        overall_remark=overall_remark,
    )
    results.append(inst)

    for serial_row in approved_rows[1:]:
        child = _copy_installation_shell(inst, parent_installation_id=inst.id)
        db.add(child)
        db.flush()
        _apply_verified_serial_line_to_request(
            db,
            child,
            serial_row,
            actor=actor,
            billing_type=billing_type,
            overall_remark=overall_remark,
        )
        log_installation_action(
            db,
            child,
            action="Split From Parent Installation",
            user=actor,
            old_status=None,
            new_status=child.status,
            remarks=f"Created from installation #{inst.id} for serial {serial_row.serial_no}",
            metadata={
                "parent_installation_id": inst.id,
                "serial_no": serial_row.serial_no,
                "serial_no_2": serial_row.serial_no_2,
                "order_item_id": child.order_item_id,
            },
        )
        results.append(child)

    return results


def sync_callcenter_order_item_on_completion(db: Session, inst: InstallationRequest) -> None:
    if not is_callcenter_source(inst) or inst.status != "Completed":
        return
    sync_order_item_for_service_eligibility(db, inst)


def sync_order_item_for_service_eligibility(db: Session, inst: InstallationRequest) -> None:
    """Mark the linked order line installation-complete for service workflows."""
    from app.services.service_serial import SERVICE_ELIGIBLE_INSTALLATION_REQUEST_STATUSES

    if (inst.status or "") not in SERVICE_ELIGIBLE_INSTALLATION_REQUEST_STATUSES:
        return
    item: OrderItem | None = None
    if inst.order_item_id:
        item = db.get(OrderItem, inst.order_item_id)
    elif inst.order_id and inst.serial_no:
        item = find_order_item_by_serial_on_order(db, inst.order_id, inst.serial_no, inst.serial_no_2)
        if item is not None and not inst.order_item_id:
            inst.order_item_id = item.id
    if item is not None:
        item.installation_status = "Completed"


def document_upload_url(inst: InstallationRequest) -> str | None:
    if not inst.document_access_token:
        return None
    return build_public_upload_url(inst.document_access_token)


def payment_qr_view_url(inst: InstallationRequest) -> str | None:
    if inst.payment_qr_code_path:
        return to_public_upload_path(inst.payment_qr_code_path)
    if inst.payment_qr_code_blob:
        return f"/api/installations/{inst.id}/payment-qr"
    return None


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def clear_installation_payment_request(inst: InstallationRequest) -> None:
    inst.payment_amount_requested = None
    inst.payment_type_requested = None
    inst.payment_qr_code_path = None
    inst.payment_qr_code_blob = None
    inst.payment_qr_code_filename = None
    inst.payment_qr_code_content_type = None
    inst.payment_qr_code_size_bytes = None
    inst.payment_proof_file_path = None
    inst.payment_requested_at = None


def clear_installation_completion_submission(inst: InstallationRequest) -> None:
    inst.installation_date = None
    inst.work_report_file_path = None


def replace_completion_proof_serial_2(
    db: Session,
    inst: InstallationRequest,
    file_path: str,
    user: User,
) -> None:
    for row in db.scalars(
        select(InstallationDocument).where(
            InstallationDocument.installation_request_id == inst.id,
            InstallationDocument.document_type == COMPLETION_PROOF_SERIAL_2_TYPE,
        )
    ).all():
        db.delete(row)
    db.add(
        InstallationDocument(
            installation_request_id=inst.id,
            document_type=COMPLETION_PROOF_SERIAL_2_TYPE,
            file_path=file_path,
            uploaded_by_type="engineer",
            uploaded_by_user_id=user.id,
            status="Uploaded",
            uploaded_at=now_utc(),
        )
    )


def latest_completion_proof_serial_2_path(db: Session, installation_id: int) -> str | None:
    row = db.scalar(
        select(InstallationDocument)
        .where(
            InstallationDocument.installation_request_id == installation_id,
            InstallationDocument.document_type == COMPLETION_PROOF_SERIAL_2_TYPE,
        )
        .order_by(InstallationDocument.uploaded_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    return to_public_upload_path(row.file_path)


def resolve_order_item_serial_count(db: Session, order_item: OrderItem | None) -> int:
    if order_item is None:
        return 1
    if order_item.item_id:
        master = db.get(ItemMaster, order_item.item_id)
        if master is not None and master.deleted_at is None:
            return max(1, int(master.serial_count or 1))
    normalized_code = (order_item.item_code or "").strip()
    if normalized_code:
        master = db.scalar(
            select(ItemMaster).where(
                ItemMaster.item_code == normalized_code,
                ItemMaster.deleted_at.is_(None),
            )
        )
        if master is not None:
            return max(1, int(master.serial_count or 1))
    return 1


def _pick_installation_serial_value(
    inst: InstallationRequest,
    order_item: OrderItem | None,
    slot: int,
) -> str | None:
    if slot == 1:
        value = (
            (inst.serial_no or "").strip()
            or (inst.engineer_entered_serial_no or "").strip()
            or ((order_item.serial_no or "").strip() if order_item else "")
        )
        return value or None
    value = (
        (inst.serial_no_2 or "").strip()
        or (inst.engineer_entered_serial_no_2 or "").strip()
        or ((order_item.serial_no_2 or "").strip() if order_item else "")
    )
    return value or None


def installation_required_serial_proof_slots(db: Session, inst: InstallationRequest) -> list[dict]:
    order_item = db.get(OrderItem, inst.order_item_id) if inst.order_item_id else None
    serial_count = resolve_order_item_serial_count(db, order_item)
    required = max(1, serial_count)
    if _pick_installation_serial_value(inst, order_item, 2):
        required = max(required, 2)
    return [
        {"slot": slot, "serial_no": _pick_installation_serial_value(inst, order_item, slot)}
        for slot in range(1, required + 1)
    ]


def build_installation_completion_proofs(db: Session, inst: InstallationRequest) -> list[dict]:
    path1 = to_public_upload_path(inst.work_report_file_path)
    path2 = latest_completion_proof_serial_2_path(db, inst.id)
    proofs = []
    for entry in installation_required_serial_proof_slots(db, inst):
        slot = entry["slot"]
        file_path = path1 if slot == 1 else path2 if slot == 2 else None
        proofs.append(
            {
                "slot": slot,
                "serial_no": entry["serial_no"],
                "file_path": file_path,
            }
        )
    return proofs


def installation_requires_second_serial_proof(db: Session, inst: InstallationRequest) -> bool:
    return len(installation_required_serial_proof_slots(db, inst)) >= 2


def installation_completion_proofs_complete(db: Session, inst: InstallationRequest) -> bool:
    proofs = build_installation_completion_proofs(db, inst)
    return bool(proofs) and all((proof.get("file_path") or "").strip() for proof in proofs)


def return_installation_to_engineer_for_rework(
    inst: InstallationRequest,
    *,
    reject_stage: str = "completion",
) -> str:
    """Send a structured workflow installation back to the assigned engineer."""
    if reject_stage == "payment":
        clear_installation_payment_request(inst)
        return "Installation Completed"
    clear_installation_completion_submission(inst)
    clear_installation_payment_request(inst)
    return "Returned"


def _clear_installation_workflow_fields(inst: InstallationRequest) -> None:
    inst.assigned_engineer = None
    inst.order_id = None
    inst.order_item_id = None
    inst.order_verified_at = None
    inst.order_verified_by = None
    inst.serial_no = None
    inst.serial_no_2 = None
    inst.serial_verified_at = None
    inst.serial_verified_by = None
    inst.engineer_entered_serial_no = None
    inst.engineer_entered_serial_no_2 = None
    inst.engineer_site_remarks = None
    inst.engineer_serials_submitted_at = None
    inst.admin_billing_type = None
    inst.admin_approval_remark = None
    inst.admin_approved_at = None
    inst.admin_approved_by = None
    inst.installation_date = None
    inst.work_report = None
    inst.work_report_file_path = None
    inst.payment_amount_requested = None
    inst.payment_type_requested = None
    inst.payment_qr_code_path = None
    inst.payment_qr_code_blob = None
    inst.payment_qr_code_filename = None
    inst.payment_qr_code_content_type = None
    inst.payment_qr_code_size_bytes = None
    inst.payment_proof_file_path = None
    inst.payment_requested_at = None
    inst.payment_amount_paid = None
    inst.payment_type_paid = None
    inst.payment_recorded_at = None
    inst.payment_recorded_by = None
    inst.payment_transaction_id = None
    inst.parent_installation_id = None
    inst.status = "Document Requested" if inst.document_request_sent_at else "Pending"


def _delete_child_installations(db: Session, inst: InstallationRequest) -> None:
    children = db.scalars(
        select(InstallationRequest).where(InstallationRequest.parent_installation_id == inst.id)
    ).all()
    for child in children:
        _delete_engineer_serial_rows(db, child.id)
        db.delete(child)


def _delete_engineer_serial_rows(db: Session, installation_id: int) -> None:
    rows = db.scalars(
        select(InstallationEngineerSerial).where(
            InstallationEngineerSerial.installation_request_id == installation_id
        )
    ).all()
    for row in rows:
        db.delete(row)


def _clear_payment_fields(inst: InstallationRequest) -> None:
    clear_installation_payment_request(inst)
    inst.payment_amount_paid = None
    inst.payment_type_paid = None
    inst.payment_recorded_at = None
    inst.payment_recorded_by = None
    inst.payment_transaction_id = None


def _clear_completion_fields(inst: InstallationRequest) -> None:
    clear_installation_completion_submission(inst)
    inst.work_report = None


def _unlock_callcenter_order_item(db: Session, inst: InstallationRequest) -> None:
    if not is_callcenter_source(inst) or not inst.order_item_id:
        return
    item = db.get(OrderItem, inst.order_item_id)
    if item is not None and (item.installation_status or "Not Requested") == "Submitted":
        item.installation_status = "Not Requested"
    inst.order_item_id = None


def _clear_serial_verification_fields(db: Session, inst: InstallationRequest) -> None:
    inst.serial_verified_at = None
    inst.serial_verified_by = None
    inst.admin_billing_type = None
    inst.admin_approval_remark = None
    inst.admin_approved_at = None
    inst.admin_approved_by = None
    if not is_vendor_initiated_workflow(inst):
        _unlock_callcenter_order_item(db, inst)
        inst.serial_no = None
        inst.serial_no_2 = None
        inst.engineer_entered_serial_no = None
        inst.engineer_entered_serial_no_2 = None


def _clear_engineer_serial_entry(db: Session, inst: InstallationRequest) -> None:
    _delete_engineer_serial_rows(db, inst.id)
    inst.engineer_serials_submitted_at = None
    inst.engineer_site_remarks = None
    if not is_vendor_initiated_workflow(inst):
        inst.engineer_entered_serial_no = None
        inst.engineer_entered_serial_no_2 = None


def _clear_assignment(inst: InstallationRequest) -> None:
    inst.assigned_engineer = None


def _clear_order_link(inst: InstallationRequest) -> None:
    inst.order_verified_at = None
    inst.order_verified_by = None
    inst.order_id = None
    inst.order_item_id = None


def _status_before_order_verified(inst: InstallationRequest) -> str:
    if inst.document_request_sent_at:
        return "Document Requested"
    return "Pending"


def _has_engineer_serial_rows(db: Session, inst: InstallationRequest) -> bool:
    return db.scalar(
        select(func.count())
        .select_from(InstallationEngineerSerial)
        .where(InstallationEngineerSerial.installation_request_id == inst.id)
    ) > 0


def _reset_vendor_to_submitted(db: Session, inst: InstallationRequest) -> None:
    """Roll a vendor order installation back to post-submission state (order link kept)."""
    _clear_assignment(inst)
    _clear_engineer_serial_entry(db, inst)
    _clear_serial_verification_fields(db, inst)
    _clear_completion_fields(inst)
    _clear_payment_fields(inst)
    if inst.order_item_id:
        item = db.get(OrderItem, inst.order_item_id)
        if item is not None:
            inst.serial_no = item.serial_no
            inst.serial_no_2 = item.serial_no_2
            if item.order_id:
                inst.order_id = item.order_id
    inst.order_verified_at = None
    inst.order_verified_by = None
    inst.admin_billing_type = None
    inst.status = "Submitted"


def apply_installation_workflow_step(
    db: Session,
    inst: InstallationRequest,
    target_step: int,
    user: User,
    remarks: str | None = None,
) -> InstallationRequest:
    """Roll an installation workflow back to the start of ``target_step`` (1–10)."""
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admin can reset installation workflow")
    if not (is_callcenter_source(inst) or is_vendor_initiated_workflow(inst)):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Workflow step reset is only available for call-center or vendor order installations",
        )
    if target_step < 1 or target_step > 10:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Workflow step must be between 1 and 10")

    vendor_flow = is_vendor_initiated_workflow(inst)
    if vendor_flow and target_step in {2, 3}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Steps 2 and 3 do not apply to vendor order installations",
        )

    old_status = inst.status
    _delete_child_installations(db, inst)

    if target_step <= 1:
        _delete_engineer_serial_rows(db, inst.id)
        if vendor_flow:
            _reset_vendor_to_submitted(db, inst)
        else:
            _clear_installation_workflow_fields(inst)
    else:
        if target_step <= 2 and not vendor_flow:
            _clear_order_link(inst)
            _clear_assignment(inst)
            _clear_engineer_serial_entry(db, inst)
            _clear_serial_verification_fields(db, inst)
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = _status_before_order_verified(inst)
        elif target_step <= 3 and not vendor_flow:
            _clear_order_link(inst)
            _clear_assignment(inst)
            _clear_engineer_serial_entry(db, inst)
            _clear_serial_verification_fields(db, inst)
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = _status_before_order_verified(inst)
        elif target_step <= 4 and vendor_flow:
            _reset_vendor_to_submitted(db, inst)
        elif target_step <= 4 and not vendor_flow:
            _clear_assignment(inst)
            _clear_engineer_serial_entry(db, inst)
            _clear_serial_verification_fields(db, inst)
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = "Order Verified" if inst.order_verified_at else _status_before_order_verified(inst)
        elif target_step <= 5:
            _clear_engineer_serial_entry(db, inst)
            _clear_serial_verification_fields(db, inst)
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = "Assigned" if inst.assigned_engineer else ("Submitted" if vendor_flow else "Order Verified")
        elif target_step <= 6:
            _clear_serial_verification_fields(db, inst)
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = (
                "Serial Pending Verification"
                if _has_engineer_serial_rows(db, inst)
                else ("Assigned" if inst.assigned_engineer else "Submitted")
            )
        elif target_step <= 7:
            _clear_completion_fields(inst)
            _clear_payment_fields(inst)
            inst.status = "In Progress" if inst.assigned_engineer else "Assigned"
        elif target_step <= 8:
            _clear_payment_fields(inst)
            inst.status = "Completion Pending Approval"
        elif target_step <= 9:
            _clear_payment_fields(inst)
            inst.status = "Installation Completed"
        else:
            inst.status = "Payment Pending"

    log_installation_action(
        db,
        inst,
        action="Workflow Step Reset",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=remarks or f"Admin rolled workflow back to step {target_step}",
        metadata={"target_step": target_step},
    )
    return inst


def reset_callcenter_workflow(db: Session, inst: InstallationRequest, user: User) -> InstallationRequest:
    return apply_installation_workflow_step(db, inst, 1, user, remarks="Admin reset the entire installation workflow")
