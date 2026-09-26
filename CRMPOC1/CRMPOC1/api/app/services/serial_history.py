import json
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.complaint import Complaint, ComplaintStatusLog
from app.models.installation import InstallationRequest
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.serial_history import SerialHistoryEvent
from app.models.service import ServiceCompletion, ServiceObservation, ServiceRequest
from app.models.user import User
from app.models.vendor import Vendor

EVENT_TYPES = {
    "ORDER": "ORDER",
    "INSTALLATION": "INSTALLATION",
    "COMPLAINT": "COMPLAINT",
    "SERVICE": "SERVICE",
    "CLAIM": "CLAIM",
    "PART_REPLACEMENT": "PART_REPLACEMENT",
    "SYSTEM": "SYSTEM",
}


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _performed_by_name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    return user.name if user else None


def _json_text(payload: dict | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, default=_iso, sort_keys=True)


def create_serial_history_event(
    db: Session,
    *,
    serial_no: str,
    event_type: str,
    event_at: datetime,
    title: str,
    description: str,
    order_item_id: int | None = None,
    serial_no_2: str | None = None,
    event_subtype: str | None = None,
    performed_by_user_id: int | None = None,
    performed_by_name: str | None = None,
    source_table: str | None = None,
    source_id: int | None = None,
    remarks: str | None = None,
    metadata: dict | None = None,
) -> SerialHistoryEvent | None:
    if not isinstance(event_at, datetime):
        # Skip malformed/zero-date source rows instead of failing the whole history load.
        return None
    existing = None
    if source_table and source_id is not None:
        # The session uses autoflush=False, so a duplicate key added earlier in this same
        # call is not yet visible to a DB query — check pending/loaded objects first to
        # avoid a duplicate-key IntegrityError on commit.
        existing = next(
            (
                obj for obj in db.new
                if isinstance(obj, SerialHistoryEvent)
                and obj.source_table == source_table
                and obj.source_id == source_id
                and obj.event_type == event_type
                and obj.serial_no == serial_no
            ),
            None,
        )
        if existing is None:
            existing = db.scalar(
                select(SerialHistoryEvent).where(
                    SerialHistoryEvent.source_table == source_table,
                    SerialHistoryEvent.source_id == source_id,
                    SerialHistoryEvent.event_type == event_type,
                    SerialHistoryEvent.serial_no == serial_no,
                )
            )
    if existing is not None:
        existing.event_at = event_at
        existing.title = title
        existing.description = description
        existing.remarks = remarks
        existing.metadata_json = _json_text(metadata)
        existing.event_subtype = event_subtype
        existing.performed_by_user_id = performed_by_user_id
        existing.performed_by_name = performed_by_name or existing.performed_by_name
        existing.serial_no_2 = serial_no_2
        existing.order_item_id = order_item_id
        return existing

    event = SerialHistoryEvent(
        order_item_id=order_item_id,
        serial_no=serial_no,
        serial_no_2=serial_no_2,
        event_type=event_type,
        event_subtype=event_subtype,
        event_at=event_at,
        performed_by_user_id=performed_by_user_id,
        performed_by_name=performed_by_name,
        source_table=source_table,
        source_id=source_id,
        title=title,
        description=description,
        remarks=remarks,
        metadata_json=_json_text(metadata),
    )
    db.add(event)
    return event


def _order_context(db: Session, item: OrderItem):
    order = db.get(Order, item.order_id)
    item_master = db.get(ItemMaster, item.item_id) if item.item_id else None
    vendor = db.get(Vendor, order.vendor_id) if order and order.vendor_id else None
    return order, item_master, vendor


def _item_serials(item: OrderItem, serial_no: str) -> tuple[str, str | None]:
    if item.serial_no and item.serial_no.lower() == serial_no.lower():
        return item.serial_no, item.serial_no_2
    if item.serial_no_2 and item.serial_no_2.lower() == serial_no.lower():
        return item.serial_no_2, item.serial_no
    return item.serial_no or serial_no, item.serial_no_2


def backfill_serial_history_for_serial(db: Session, serial_no: str) -> bool:
    item = db.scalar(
        select(OrderItem).where(
            or_(
                func.lower(OrderItem.serial_no) == func.lower(serial_no),
                func.lower(OrderItem.serial_no_2) == func.lower(serial_no),
            )
        )
    )
    if item is None:
        return False

    primary_serial, secondary_serial = _item_serials(item, serial_no)
    db.execute(
        delete(SerialHistoryEvent).where(
            func.lower(SerialHistoryEvent.serial_no) == primary_serial.lower(),
            SerialHistoryEvent.event_type == EVENT_TYPES["SERVICE"],
            SerialHistoryEvent.source_table.in_(["service_requests", "service_status_logs"]),
        )
    )
    order, item_master, vendor = _order_context(db, item)
    if order is not None:
        create_serial_history_event(
            db,
            serial_no=primary_serial,
            serial_no_2=secondary_serial,
            order_item_id=item.id,
            event_type=EVENT_TYPES["ORDER"],
            event_subtype="ORDER_CREATED",
            event_at=order.created_at,
            performed_by_user_id=order.created_by,
            performed_by_name=_performed_by_name(db, order.created_by),
            source_table="orders",
            source_id=order.id,
            title="Order created",
            description=f"Order {order.order_no or order.id} created for {order.customer_name or 'customer'}.",
            metadata={
                "order_no": order.order_no,
                "customer_name": order.customer_name,
                "vendor_name": vendor.name_of_firm if vendor else None,
                "item_name": item_master.item_name if item_master else None,
                "status": order.status,
            },
        )
        if order.status in {"Shipped", "In Transit"}:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["ORDER"],
                event_subtype="ORDER_DISPATCHED",
                event_at=order.updated_at,
                performed_by_user_id=order.created_by,
                performed_by_name=_performed_by_name(db, order.created_by),
                source_table="orders",
                # Distinct source_id: without autoflush, the same key as ORDER_CREATED
                # (source_id=order.id) is not visible to the dedup lookup yet and causes
                # a duplicate-key IntegrityError on commit.
                source_id=order.id + 500000,
                title="Order dispatched",
                description=f"Order status moved to {order.status}.",
                metadata={"order_status": order.status, "lrn_no": order.lrn_no},
            )
        if order.expected_delivery_date:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["ORDER"],
                event_subtype="EXPECTED_DELIVERY",
                event_at=datetime.combine(order.expected_delivery_date, datetime.min.time(), tzinfo=timezone.utc),
                source_table="orders",
                source_id=order.id + 1000000,
                title="Expected delivery scheduled",
                description=f"Expected delivery date set to {order.expected_delivery_date.isoformat()}.",
                metadata={"expected_delivery_date": order.expected_delivery_date.isoformat()},
            )
        if order.actual_delivery_date:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["ORDER"],
                event_subtype="ACTUAL_DELIVERY",
                event_at=datetime.combine(order.actual_delivery_date, datetime.min.time(), tzinfo=timezone.utc),
                source_table="orders",
                source_id=order.id + 2000000,
                title="Order delivered",
                description=f"Product delivered on {order.actual_delivery_date.isoformat()}.",
                metadata={"actual_delivery_date": order.actual_delivery_date.isoformat()},
            )

    installations = db.scalars(
        select(InstallationRequest).where(
            or_(
                InstallationRequest.order_item_id == item.id,
                func.lower(func.coalesce(InstallationRequest.serial_no, "")) == primary_serial.lower(),
                func.lower(func.coalesce(InstallationRequest.serial_no_2, "")) == primary_serial.lower(),
            )
        )
    ).all()
    for inst in installations:
        create_serial_history_event(
            db,
            serial_no=primary_serial,
            serial_no_2=secondary_serial,
            order_item_id=item.id,
            event_type=EVENT_TYPES["INSTALLATION"],
            event_subtype="REQUEST_CREATED",
            event_at=inst.request_date,
            performed_by_user_id=inst.assigned_engineer,
            performed_by_name=_performed_by_name(db, inst.assigned_engineer),
            source_table="installation_requests",
            source_id=inst.id,
            title="Installation request created",
            description=f"Installation request {inst.id} created with status {inst.status}.",
            metadata={"status": inst.status, "product_name": inst.product_name},
        )
        if inst.installation_date:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["INSTALLATION"],
                event_subtype="COMPLETED",
                event_at=inst.installation_date,
                performed_by_user_id=inst.assigned_engineer,
                performed_by_name=_performed_by_name(db, inst.assigned_engineer),
                source_table="installation_requests",
                source_id=inst.id + 1000000,
                title="Installation completed",
                description=f"Installation completed with status {inst.status}.",
                remarks=inst.work_report,
                metadata={"status": inst.status, "work_report_file_path": inst.work_report_file_path},
            )
        elif inst.status in {"Assigned", "In Progress", "Settlement Pending", "Settlement Approved", "Rejected", "Submitted"}:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["INSTALLATION"],
                event_subtype=f"STATUS_{inst.status.upper().replace(' ', '_')}",
                event_at=inst.updated_at,
                performed_by_user_id=inst.assigned_engineer,
                performed_by_name=_performed_by_name(db, inst.assigned_engineer),
                source_table="installation_requests",
                source_id=inst.id + 2000000,
                title="Installation status updated",
                description=f"Installation request status is {inst.status}.",
                remarks=inst.work_report,
                metadata={"status": inst.status},
            )

    claims = db.scalars(
        select(Claim).where(
            or_(
                Claim.order_item_id == item.id,
                func.lower(func.coalesce(Claim.serial_number, "")) == primary_serial.lower(),
            )
        )
    ).all()
    for claim in claims:
        create_serial_history_event(
            db,
            serial_no=primary_serial,
            serial_no_2=secondary_serial,
            order_item_id=item.id,
            event_type=EVENT_TYPES["CLAIM"],
            event_subtype="SUBMITTED",
            event_at=claim.submitted_at,
            performed_by_user_id=claim.processed_by,
            performed_by_name=_performed_by_name(db, claim.processed_by),
            source_table="claims",
            source_id=claim.id,
            title="Warranty claim submitted",
            description=f"Claim {claim.claim_id} submitted with status {claim.status}.",
            remarks=claim.notes,
            metadata={"claim_id": claim.claim_id, "status": claim.status},
        )
        if claim.updated_at and claim.updated_at != claim.submitted_at:
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=EVENT_TYPES["CLAIM"],
                event_subtype="STATUS_UPDATED",
                event_at=claim.updated_at,
                performed_by_user_id=claim.processed_by,
                performed_by_name=_performed_by_name(db, claim.processed_by),
                source_table="claims",
                source_id=claim.id + 1000000,
                title="Warranty claim updated",
                description=f"Claim {claim.claim_id} updated to status {claim.status}.",
                remarks=claim.admin_remark or claim.notes,
                metadata={"claim_id": claim.claim_id, "status": claim.status},
            )

    complaints = db.scalars(
        select(Complaint).where(
            or_(
                Complaint.order_item_id == item.id,
                func.lower(func.coalesce(Complaint.serial_no, "")) == primary_serial.lower(),
            ),
            Complaint.deleted_at.is_(None),
        )
    ).all()
    for complaint in complaints:
        create_serial_history_event(
            db,
            serial_no=primary_serial,
            serial_no_2=secondary_serial,
            order_item_id=item.id,
            event_type=EVENT_TYPES["COMPLAINT"],
            event_subtype="CREATED",
            event_at=complaint.created_at,
            performed_by_user_id=complaint.created_by,
            performed_by_name=_performed_by_name(db, complaint.created_by),
            source_table="complaints",
            source_id=complaint.id,
            title="Complaint created",
            description=f"Complaint {complaint.comp_no} created with status {complaint.status}.",
            remarks=complaint.problem_description or complaint.remark,
            metadata={"comp_no": complaint.comp_no, "query_type": complaint.query_type, "status": complaint.status},
        )
        logs = db.scalars(
            select(ComplaintStatusLog)
            .where(ComplaintStatusLog.complaint_id == complaint.id)
            .order_by(ComplaintStatusLog.changed_at.asc())
        ).all()
        for log in logs:
            event_type = EVENT_TYPES["SERVICE"] if log.action_taken else EVENT_TYPES["COMPLAINT"]
            subtype = "ACTION_RECORDED" if log.action_taken else "STATUS_CHANGED"
            title = "Complaint action recorded" if log.action_taken else "Complaint status updated"
            description = (
                f"Action taken: {log.action_taken}."
                if log.action_taken
                else f"Complaint status changed from {log.old_status or 'Unknown'} to {log.new_status or 'Unknown'}."
            )
            create_serial_history_event(
                db,
                serial_no=primary_serial,
                serial_no_2=secondary_serial,
                order_item_id=item.id,
                event_type=event_type,
                event_subtype=subtype,
                event_at=log.changed_at,
                performed_by_user_id=log.changed_by,
                performed_by_name=_performed_by_name(db, log.changed_by),
                source_table="complaint_status_logs",
                source_id=log.id,
                title=title,
                description=description,
                remarks=log.remark,
                metadata={
                    "complaint_id": complaint.id,
                    "comp_no": complaint.comp_no,
                    "old_status": log.old_status,
                    "new_status": log.new_status,
                    "action_taken": log.action_taken,
                    "document_path": log.document_path,
                },
            )

    service_requests = db.scalars(
        select(ServiceRequest).where(
            or_(
                ServiceRequest.order_item_id == item.id,
                func.lower(func.coalesce(ServiceRequest.serial_no, "")) == primary_serial.lower(),
            ),
            ServiceRequest.deleted_at.is_(None),
        )
    ).all()
    for service in service_requests:
        latest_completion = db.scalar(
            select(ServiceCompletion)
            .where(ServiceCompletion.service_request_id == service.id)
            .order_by(ServiceCompletion.completed_at.desc())
        )
        if latest_completion is None:
            continue
        latest_observation = db.scalar(
            select(ServiceObservation)
            .where(ServiceObservation.service_request_id == service.id)
            .order_by(ServiceObservation.submitted_at.desc())
        )
        problem = (
            latest_observation.problem_found
            if latest_observation and latest_observation.problem_found
            else service.problem_description
        )
        action = latest_completion.work_performed or (latest_observation.recommended_action if latest_observation else None)
        parts = []
        try:
            parts = json.loads(latest_completion.parts_replaced_json or "[]")
        except json.JSONDecodeError:
            parts = []
        if not parts and latest_observation and latest_observation.parts_required_json:
            try:
                parts = json.loads(latest_observation.parts_required_json)
            except json.JSONDecodeError:
                parts = []
        summary_bits = []
        if problem:
            summary_bits.append(f"Problem: {problem}")
        if action:
            summary_bits.append(f"Final action: {action}")
        if parts:
            summary_bits.append(f"Parts replaced: {', '.join(parts)}")
        summary = ". ".join(summary_bits) or f"Service completed for request {service.request_no or service.id}"
        create_serial_history_event(
            db,
            serial_no=primary_serial,
            serial_no_2=secondary_serial,
            order_item_id=item.id,
            event_type=EVENT_TYPES["SERVICE"],
            event_subtype="SERVICE_SUMMARY",
            event_at=latest_completion.completed_at,
            performed_by_user_id=latest_completion.performed_by_user_id,
            performed_by_name=_performed_by_name(db, latest_completion.performed_by_user_id),
            source_table="service_requests",
            source_id=service.id,
            title="Service completed",
            description=summary,
            remarks=latest_completion.completion_remarks or (latest_observation.remarks if latest_observation else None),
            metadata={
                "request_no": service.request_no,
                "status": service.status,
                "service_type": service.service_type,
                "warranty_status": service.warranty_status,
                "query_type": service.query_type,
                "problem_found": problem,
                "final_action": action,
                "parts_replaced": parts,
                "proof_document": latest_completion.customer_acknowledgement_path,
            },
        )
    return True
