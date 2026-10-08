"""Unit-level service request assignment helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.service import (
    ServiceRequest,
    ServiceRequestItem,
    ServiceRequestUnit,
    ServiceUnitAssignment,
)
from app.models.user import User
from app.services.order_item_context import derive_service_type_for_item, serial_fields_for_item, service_billing_label
from app.services.service_documents import order_workflow_unlocked
from app.services.service_serial import (
    filter_installed_items_by_serial,
    find_customer_installed_order_item,
    find_customer_order_item_by_serial,
    order_item_is_installed_for_service,
    order_item_matches_serial,
    serial_exists_in_order_records,
)
from app.services.engineer_service_scope import sync_service_engineer_assignment
from app.services.service_unit_workflow import (
    approvals_for_service,
    completions_for_service,
    observations_for_service,
    payment_requests_for_service,
)

def _json_load_parts(observation) -> list[str]:
    if observation is None or not observation.parts_required_json:
        return []
    try:
        value = json.loads(observation.parts_required_json)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _is_installed_order_item(db: Session, order_item: OrderItem) -> bool:
    return order_item_is_installed_for_service(db, order_item)


def _now() -> datetime:
    return datetime.now(timezone.utc)


BILLING_LOCKED_UNIT_STATUSES = frozenset({"Payment Completed", "Closed"})


def apply_unit_billing_choice(
    db: Session,
    unit: ServiceRequestUnit,
    billing_type: str,
    *,
    order_item: OrderItem | None = None,
) -> None:
    billing = (billing_type or "").strip()
    if billing not in {"Free", "Paid"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "billing_type must be Free or Paid")
    if order_item is None and unit.order_item_id:
        order_item = db.get(OrderItem, unit.order_item_id)
    if billing == "Paid":
        unit.service_type = "Paid Service"
    else:
        unit.service_type = (
            derive_service_type_for_item(db, order_item) if order_item else "Free Service"
        )
    if order_item is not None:
        fields = serial_fields_for_item(db, order_item)
        if fields.get("warranty_status"):
            unit.warranty_status = fields.get("warranty_status")


def apply_service_billing_choice(
    db: Session,
    service: ServiceRequest,
    billing_type: str,
    *,
    order_item: OrderItem | None = None,
) -> None:
    billing = (billing_type or "").strip()
    if billing not in {"Free", "Paid"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "billing_type must be Free or Paid")
    if order_item is None and service.order_item_id:
        order_item = db.get(OrderItem, service.order_item_id)
    if billing == "Paid":
        service.service_type = "Paid Service"
    elif order_item is not None:
        service.service_type = derive_service_type_for_item(db, order_item)
    else:
        service.service_type = "Free Service"
    if order_item is not None:
        fields = serial_fields_for_item(db, order_item)
        service.warranty_status = fields.get("warranty_status")


def _resolve_item_master(db: Session, item_code: str | None, item_id: int | None) -> ItemMaster | None:
    if item_id:
        master = db.get(ItemMaster, item_id)
        if master is not None and master.deleted_at is None:
            return master
    code = (item_code or "").strip()
    if not code:
        return None
    return db.scalar(
        select(ItemMaster).where(ItemMaster.item_code == code, ItemMaster.deleted_at.is_(None))
    )


def _serial_labels(serial_count: int) -> list[str]:
    if serial_count <= 0:
        return []
    if serial_count == 1:
        return ["Serial Number"]
    return [f"Serial Number {idx}" for idx in range(1, serial_count + 1)]


def engineer_has_unit_assignment(db: Session, service_id: int, engineer_id: int) -> bool:
    unit_id = db.scalar(
        select(ServiceRequestUnit.id)
        .where(
            ServiceRequestUnit.service_request_id == service_id,
            ServiceRequestUnit.assigned_engineer_id == engineer_id,
        )
        .limit(1)
    )
    return unit_id is not None


def verify_order_for_service(
    db: Session,
    service: ServiceRequest,
    *,
    order_id: int | None,
    order_no: str | None,
    serial_no: str | None = None,
) -> Order:
    if not order_workflow_unlocked(db, service):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Approve customer documents before verifying the order.",
        )
    order: Order | None = None
    if order_id is not None:
        order = db.get(Order, order_id)
    elif order_no:
        normalized = order_no.strip()
        order = db.scalar(
            select(Order).where(
                func.lower(Order.order_no) == normalized.lower(),
                Order.deleted_at.is_(None),
            )
        )
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    service.order_id = order.id
    service.customer_name = order.customer_name or service.customer_name
    service.customer_mobile = order.customer_contact or service.customer_mobile
    service.customer_email = order.customer_email or service.customer_email
    service.customer_address = order.customer_address or service.customer_address
    service.customer_identified_at = _now()
    if service.status == "New":
        service.status = "Service Team Review"
        service.status_date = _now()

    order_items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)
    ).all()
    installed_items = [row for row in order_items if _is_installed_order_item(db, row)]
    if not installed_items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No installed units found on this order. Service is only allowed after installation is completed.",
        )

    effective_serial = (serial_no or service.serial_no or "").strip()
    serial_item: OrderItem | None = None
    if effective_serial:
        serial_item = find_customer_order_item_by_serial(db, service, effective_serial)
        if serial_item is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Serial number was not found on any order for this customer.",
            )
        if serial_item.order_id != order.id:
            linked_order = db.get(Order, serial_item.order_id)
            linked_order_no = linked_order.order_no if linked_order else serial_item.order_id
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Serial number belongs to order {linked_order_no}, not the selected order.",
            )
        serial_matches = filter_installed_items_by_serial(installed_items, effective_serial)
        if not serial_matches:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Serial number is on this order but installation is not completed yet.",
            )
        installed_items = serial_matches
        service.serial_no = effective_serial
        service.order_item_id = serial_item.id

    grouped: dict[str, list[OrderItem]] = defaultdict(list)
    for row in installed_items:
        code = (row.item_code or "").strip() or "UNASSIGNED"
        grouped[code].append(row)

    existing_items = {
        row.item_code: row
        for row in db.scalars(
            select(ServiceRequestItem).where(ServiceRequestItem.service_request_id == service.id)
        ).all()
    }
    existing_units = {
        row.order_item_id: row
        for row in db.scalars(
            select(ServiceRequestUnit).where(ServiceRequestUnit.service_request_id == service.id)
        ).all()
    }

    for item_code, rows in grouped.items():
        if not rows:
            continue
        master = _resolve_item_master(db, item_code, rows[0].item_id)
        serial_count = master.serial_count if master else 1
        item_name = master.item_name if master else (rows[0].item_code or item_code)
        sr_item = existing_items.get(item_code)
        if sr_item is None:
            sr_item = ServiceRequestItem(
                service_request_id=service.id,
                order_id=order.id,
                item_code=item_code,
                item_id=master.id if master else rows[0].item_id,
                item_name=item_name,
                ordered_quantity=len(rows),
                serial_count=serial_count,
            )
            db.add(sr_item)
            db.flush()
            existing_items[item_code] = sr_item
        else:
            sr_item.ordered_quantity = len(rows)
            sr_item.item_id = master.id if master else rows[0].item_id
            sr_item.item_name = item_name
            sr_item.serial_count = serial_count

        for order_item in rows:
            unit = existing_units.get(order_item.id)
            if unit is None:
                unit = ServiceRequestUnit(
                    service_request_id=service.id,
                    service_request_item_id=sr_item.id,
                    order_item_id=order_item.id,
                    serial_no=order_item.serial_no,
                    serial_no_2=order_item.serial_no_2,
                )
                db.add(unit)
                existing_units[order_item.id] = unit
            else:
                unit.serial_no = order_item.serial_no
                unit.serial_no_2 = order_item.serial_no_2
                unit.service_request_item_id = sr_item.id

    # Drop unassigned units that are not installation-complete (e.g. after re-verify).
    for unit in list(existing_units.values()):
        order_item = db.get(OrderItem, unit.order_item_id)
        if order_item is None or not _is_installed_order_item(db, order_item):
            if unit.assigned_engineer_id is None:
                db.delete(unit)
            continue
        if effective_serial and not order_item_matches_serial(order_item, effective_serial):
            if unit.assigned_engineer_id is None:
                db.delete(unit)

    return order


def build_order_item_summaries(db: Session, service_id: int) -> list[dict]:
    items = db.scalars(
        select(ServiceRequestItem)
        .where(ServiceRequestItem.service_request_id == service_id)
        .order_by(ServiceRequestItem.item_code)
    ).all()
    order_ids = {item.order_id for item in items if item.order_id}
    order_items_by_order_code: dict[tuple[int, str], list[OrderItem]] = defaultdict(list)
    if order_ids:
        for row in db.scalars(select(OrderItem).where(OrderItem.order_id.in_(order_ids))):
            code = (row.item_code or "").strip() or "UNASSIGNED"
            order_items_by_order_code[(row.order_id, code)].append(row)

    unit_rows = db.scalars(
        select(ServiceRequestUnit).where(ServiceRequestUnit.service_request_id == service_id)
    ).all()
    order_item_ids = {unit.order_item_id for unit in unit_rows}
    order_item_map = {}
    if order_item_ids:
        for row in db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))):
            order_item_map[row.id] = row

    units_by_item_id: dict[int, list[ServiceRequestUnit]] = defaultdict(list)
    for unit in unit_rows:
        units_by_item_id[unit.service_request_item_id].append(unit)

    summaries: list[dict] = []
    for item in items:
        units = units_by_item_id.get(item.id, [])
        eligible_units = []
        for unit in units:
            order_item = order_item_map.get(unit.order_item_id)
            if order_item is not None and _is_installed_order_item(db, order_item):
                eligible_units.append(unit)

        item_code = (item.item_code or "").strip() or "UNASSIGNED"
        order_items_for_code = order_items_by_order_code.get((item.order_id, item_code), [])
        total_ordered = len(order_items_for_code)
        installed_on_order = sum(1 for row in order_items_for_code if _is_installed_order_item(db, row))
        pending_installation = total_ordered - installed_on_order

        serials_available = sum(
            1 for unit in eligible_units
            if (unit.serial_no or "").strip() or (unit.serial_no_2 or "").strip()
        )
        assigned_count = sum(1 for unit in eligible_units if unit.assigned_engineer_id is not None)
        summaries.append({
            "id": item.id,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "ordered_quantity": total_ordered,
            "installed_quantity": installed_on_order,
            "pending_installation_quantity": pending_installation,
            "serial_count": item.serial_count,
            "serial_labels": _serial_labels(item.serial_count),
            "units_count": len(eligible_units),
            "serials_available_count": serials_available,
            "assigned_count": assigned_count,
            "unassigned_count": len(eligible_units) - assigned_count,
        })
    return summaries


def build_unit_rows(
    db: Session,
    service_id: int,
    *,
    item_code: str | None = None,
    engineer_id: int | None = None,
) -> list[dict]:
    stmt = (
        select(ServiceRequestUnit, ServiceRequestItem)
        .join(ServiceRequestItem, ServiceRequestUnit.service_request_item_id == ServiceRequestItem.id)
        .where(ServiceRequestUnit.service_request_id == service_id)
        .order_by(ServiceRequestItem.item_code, ServiceRequestUnit.id)
    )
    if item_code:
        stmt = stmt.where(ServiceRequestItem.item_code == item_code)
    if engineer_id is not None:
        stmt = stmt.where(ServiceRequestUnit.assigned_engineer_id == engineer_id)

    rows: list[dict] = []
    observation_map = observations_for_service(db, service_id)
    approval_map = approvals_for_service(db, service_id)
    completion_map = completions_for_service(db, service_id)
    payment_map = payment_requests_for_service(db, service_id)
    joined_rows = list(db.execute(stmt).all())
    order_item_ids = {unit.order_item_id for unit, _ in joined_rows}
    order_item_map = {}
    if order_item_ids:
        for row in db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))):
            order_item_map[row.id] = row
    engineer_ids = {unit.assigned_engineer_id for unit, _ in joined_rows if unit.assigned_engineer_id}
    engineer_map = {}
    if engineer_ids:
        for row in db.scalars(select(User).where(User.id.in_(engineer_ids))):
            engineer_map[row.id] = row
    for unit, item in joined_rows:
        order_item = order_item_map.get(unit.order_item_id)
        if order_item is None or not _is_installed_order_item(db, order_item):
            continue
        engineer = engineer_map.get(unit.assigned_engineer_id) if unit.assigned_engineer_id else None
        serial_values: list[str | None] = []
        if item.serial_count >= 1:
            serial_values.append(unit.serial_no)
        if item.serial_count >= 2:
            serial_values.append(unit.serial_no_2)
        observation = observation_map.get(unit.id)
        approval = approval_map.get(unit.id)
        completion = completion_map.get(unit.id)
        payment = payment_map.get(unit.id)
        fields = serial_fields_for_item(db, order_item)
        warranty_status = unit.warranty_status or fields.get("warranty_status")
        service_type = unit.service_type
        serial_not_in_order = (
            unit.unit_status == "Serial Verification Pending"
            and bool((unit.serial_no or "").strip())
            and not serial_exists_in_order_records(db, unit.serial_no or "")
        )
        rows.append({
            "id": unit.id,
            "service_request_item_id": item.id,
            "order_item_id": unit.order_item_id,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "serial_count": item.serial_count,
            "serial_labels": _serial_labels(item.serial_count),
            "serial_values": serial_values,
            "serial_no": unit.serial_no,
            "serial_no_2": unit.serial_no_2,
            "assigned_engineer_id": unit.assigned_engineer_id,
            "assigned_engineer_name": engineer.name if engineer else None,
            "assigned_at": unit.assigned_at,
            "serial_verified_at": unit.serial_verified_at,
            "warranty_status": warranty_status,
            "part_warranty_status": fields.get("part_warranty_status"),
            "free_service_count": fields.get("free_service_count"),
            "paid_service_count": fields.get("paid_service_count"),
            "admin_billing_type": service_billing_label(service_type),
            "service_type": service_type,
            "observation_id": observation.id if observation else None,
            "problem_found": observation.problem_found if observation else None,
            "observation_text": observation.observation if observation else None,
            "recommended_action": observation.recommended_action if observation else None,
            "parts_required": _json_load_parts(observation),
            "estimated_service_charge": float(observation.estimated_service_charge) if observation and observation.estimated_service_charge is not None else None,
            "estimated_parts_charge": float(observation.estimated_parts_charge) if observation and observation.estimated_parts_charge is not None else None,
            "observation_remarks": observation.remarks if observation else None,
            "observation_submitted_at": observation.submitted_at if observation else None,
            "unit_status": unit.unit_status,
            "serial_not_in_order": serial_not_in_order,
            "return_remarks": unit.remarks,
            "approval_id": approval.id if approval else None,
            "approval_decision": approval.decision if approval else None,
            "completion_id": completion.id if completion else None,
            "work_performed": completion.work_performed if completion else None,
            "final_amount": float(completion.final_amount) if completion and completion.final_amount is not None else None,
            "completion_proof_path": completion.customer_acknowledgement_path if completion else None,
            "completed_at": completion.completed_at if completion else None,
            "engineer_completion_code": completion.engineer_completion_code if completion else None,
            "payment_request_id": payment.id if payment else None,
            "payment_status": payment.status if payment else None,
            "payment_type": payment.payment_type if payment else None,
            "total_requested_amount": float(payment.total_requested_amount) if payment and payment.total_requested_amount is not None else None,
            "approved_amount": float(payment.approved_amount) if payment and payment.approved_amount is not None else None,
            "payment_qr_code_path": payment.payment_qr_code_path if payment else None,
            "payment_proof_file_path": payment.payment_proof_file_path if payment else None,
            "payment_approval_status": payment.approval_status if payment else None,
            "payment_approval_stage": payment.approval_stage if payment else None,
            "payment_approval_stage_label": payment.approval_stage_label if payment else None,
            "payment_approval_step": payment.approval_step if payment else None,
            "payment_approval_total_steps": payment.approval_total_steps if payment else None,
            "payment_next_approver_role": payment.next_approver_role if payment else None,
        })
    return rows


def _ensure_service_item_and_unit(
    db: Session,
    service: ServiceRequest,
    order: Order,
    order_item: OrderItem,
) -> ServiceRequestUnit:
    item_code = (order_item.item_code or "").strip() or "UNASSIGNED"
    master = _resolve_item_master(db, item_code, order_item.item_id)
    serial_count = master.serial_count if master else 1
    item_name = master.item_name if master else item_code

    sr_item = db.scalar(
        select(ServiceRequestItem).where(
            ServiceRequestItem.service_request_id == service.id,
            ServiceRequestItem.item_code == item_code,
        )
    )
    if sr_item is None:
        sr_item = ServiceRequestItem(
            service_request_id=service.id,
            order_id=order.id,
            item_code=item_code,
            item_id=master.id if master else order_item.item_id,
            item_name=item_name,
            ordered_quantity=1,
            serial_count=serial_count,
        )
        db.add(sr_item)
        db.flush()
    else:
        sr_item.item_id = master.id if master else order_item.item_id
        sr_item.item_name = item_name
        sr_item.serial_count = serial_count

    unit = db.scalar(
        select(ServiceRequestUnit).where(
            ServiceRequestUnit.service_request_id == service.id,
            ServiceRequestUnit.order_item_id == order_item.id,
        )
    )
    if unit is None:
        unit = ServiceRequestUnit(
            service_request_id=service.id,
            service_request_item_id=sr_item.id,
            order_item_id=order_item.id,
            serial_no=order_item.serial_no,
            serial_no_2=order_item.serial_no_2,
        )
        db.add(unit)
        db.flush()
    else:
        unit.serial_no = order_item.serial_no
        unit.serial_no_2 = order_item.serial_no_2
        unit.service_request_item_id = sr_item.id
    return unit


def add_service_unit_by_serial(
    db: Session,
    service: ServiceRequest,
    *,
    serial_no: str,
    engineer_id: int,
    assigned_by_user_id: int,
    billing_type: str | None = "Free",
    remarks: str | None = None,
) -> ServiceRequestUnit:
    """Attach an installation-complete order serial to this service request and assign it to an engineer.

    The serial may be on any order for the same customer as this service request (not only the linked order).
    """
    normalized = (serial_no or "").strip()
    if not normalized:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required")

    if not (
        (service.customer_mobile or "").strip()
        or (service.customer_email or "").strip()
        or (service.customer_name or "").strip()
        or service.order_id is not None
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Identify the customer or verify an order on this service request before adding serials.",
        )

    order_item = find_customer_installed_order_item(db, service, normalized)
    if order_item is None:
        if find_customer_order_item_by_serial(db, service, normalized) is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Serial number was not found on any order for this customer.",
            )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Installation must be completed for this serial before it can be added to a service request.",
        )

    item_order = db.get(Order, order_item.order_id)
    if item_order is None or item_order.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order for this serial is not available")

    if service.order_id is None:
        service.order_id = item_order.id
        service.customer_name = item_order.customer_name or service.customer_name
        service.customer_mobile = item_order.customer_contact or service.customer_mobile
        service.customer_email = item_order.customer_email or service.customer_email
        service.customer_address = item_order.customer_address or service.customer_address

    if engineer_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "An engineer must be selected to assign this serial.",
        )

    unit = _ensure_service_item_and_unit(db, service, item_order, order_item)

    if unit.assigned_engineer_id is not None and unit.assigned_engineer_id != engineer_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This serial is already assigned to another engineer on this service request.",
        )

    if unit.assigned_engineer_id is None:
        assign_units_to_engineer(
            db,
            service,
            [unit.id],
            engineer_id,
            assigned_by_user_id,
            remarks,
            billing_type,
        )
        db.refresh(unit)

    if unit.assigned_engineer_id is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Serial was linked but engineer assignment did not save. Try again or ask service team to assign the unit.",
        )
    return unit


def assign_units_to_engineer(
    db: Session,
    service: ServiceRequest,
    unit_ids: list[int],
    engineer_id: int,
    assigned_by_user_id: int,
    remarks: str | None = None,
    billing_type: str | None = "Free",
) -> list[ServiceRequestUnit]:
    engineer = db.get(User, engineer_id)
    if engineer is None or engineer.deleted_at is not None or not engineer.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected engineer is not active")
    if (engineer.role or "").lower() != "engineer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected user is not an engineer")

    if not unit_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select at least one unit to assign")

    units = db.scalars(
        select(ServiceRequestUnit)
        .where(
            ServiceRequestUnit.service_request_id == service.id,
            ServiceRequestUnit.id.in_(unit_ids),
        )
    ).all()
    if len(units) != len(set(unit_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more selected units were not found on this service request")

    for unit in units:
        order_item = db.get(OrderItem, unit.order_item_id)
        if order_item is None or not _is_installed_order_item(db, order_item):
            serial_label = unit.serial_no or unit.serial_no_2 or f"unit #{unit.id}"
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Serial {serial_label} is not installation-complete. Service can only be assigned to installed units.",
            )

    already_assigned = [unit for unit in units if unit.assigned_engineer_id is not None]
    if already_assigned:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "One or more selected units are already assigned. Reassign only unassigned units.",
        )

    now = _now()
    billing = (billing_type or "Free").strip()
    if billing not in {"Free", "Paid"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "billing_type must be Free or Paid")

    for unit in units:
        order_item = db.get(OrderItem, unit.order_item_id)
        apply_unit_billing_choice(db, unit, billing, order_item=order_item)
        unit.assigned_engineer_id = engineer.id
        unit.assigned_at = now
        unit.assigned_by_user_id = assigned_by_user_id
        unit.unit_status = "Assigned"
        db.add(
            ServiceUnitAssignment(
                service_request_id=service.id,
                service_request_unit_id=unit.id,
                engineer_id=engineer.id,
                assigned_by_user_id=assigned_by_user_id,
                assigned_at=now,
                is_active=True,
                remarks=remarks,
            )
        )

    if service.status in {"New", "Service Team Review", "Rejected"}:
        service.status = "Assigned"
        service.status_date = now

    primary = units[0] if units else None
    if primary is not None:
        service.warranty_status = primary.warranty_status
        service.service_type = primary.service_type

    sync_service_engineer_assignment(db, service, engineer.id)

    return units


def build_engineer_unit_groups(db: Session, engineer_id: int) -> list[dict]:
    stmt = (
        select(ServiceRequestUnit, ServiceRequestItem, ServiceRequest)
        .join(ServiceRequestItem, ServiceRequestUnit.service_request_item_id == ServiceRequestItem.id)
        .join(ServiceRequest, ServiceRequestUnit.service_request_id == ServiceRequest.id)
        .where(
            ServiceRequestUnit.assigned_engineer_id == engineer_id,
            ServiceRequest.deleted_at.is_(None),
        )
        .order_by(ServiceRequest.request_no, ServiceRequestItem.item_code, ServiceRequestUnit.id)
    )
    groups: dict[tuple[int, str], dict] = {}
    for unit, item, service in db.execute(stmt).all():
        order_item = db.get(OrderItem, unit.order_item_id)
        if order_item is None or not _is_installed_order_item(db, order_item):
            continue
        order = db.get(Order, service.order_id) if service.order_id else None
        key = (service.id, item.item_code)
        if key not in groups:
            groups[key] = {
                "service_request_id": service.id,
                "request_no": service.request_no,
                "order_no": order.order_no if order else None,
                "customer_name": service.customer_name,
                "customer_address": service.customer_address,
                "problem_description": service.problem_description,
                "status": service.status,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "serial_count": item.serial_count,
                "serial_labels": _serial_labels(item.serial_count),
                "assigned_quantity": 0,
                "units": [],
            }
        serial_values: list[str | None] = []
        if item.serial_count >= 1:
            serial_values.append(unit.serial_no)
        if item.serial_count >= 2:
            serial_values.append(unit.serial_no_2)
        groups[key]["units"].append({
            "id": unit.id,
            "order_item_id": unit.order_item_id,
            "serial_values": serial_values,
            "serial_no": unit.serial_no,
            "serial_no_2": unit.serial_no_2,
            "assigned_at": unit.assigned_at,
        })
        groups[key]["assigned_quantity"] += 1
    return list(groups.values())
