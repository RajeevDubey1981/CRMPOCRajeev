"""Serial number helpers for service requests scoped to a customer's orders."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.installation import InstallationRequest
from app.models.order import Order, OrderItem
from app.models.service import ServiceRequest

SERVICE_ELIGIBLE_INSTALLATION_STATUS = "Completed"
SERVICE_ELIGIBLE_INSTALLATION_REQUEST_STATUSES = frozenset({
    "Installation Completed",
    "Payment Pending",
    "Completed",
    "Settlement Pending",
    "Settlement Approved",
})


def _normalize_mobile(value: str | None) -> str:
    return re.sub(r"\D", "", (value or "").strip())


def order_matches_service_customer(order: Order, service: ServiceRequest) -> bool:
    service_mobile = _normalize_mobile(service.customer_mobile)
    order_mobile = _normalize_mobile(order.customer_contact)
    if service_mobile and order_mobile and service_mobile == order_mobile:
        return True

    service_email = (service.customer_email or "").strip().lower()
    order_email = (order.customer_email or "").strip().lower()
    if service_email and order_email and service_email == order_email:
        return True

    service_name = (service.customer_name or "").strip().lower()
    order_name = (order.customer_name or "").strip().lower()
    if service_name and order_name and service_name == order_name:
        return True

    return False


def find_order_item_by_serial(db: Session, serial_no: str) -> OrderItem | None:
    normalized = (serial_no or "").strip()
    if not normalized:
        return None
    return db.scalar(
        select(OrderItem).where(
            or_(
                func.lower(func.coalesce(OrderItem.serial_no, "")) == normalized.lower(),
                func.lower(func.coalesce(OrderItem.serial_no_2, "")) == normalized.lower(),
            )
        )
    )


def order_item_matches_serial(order_item: OrderItem, serial_no: str) -> bool:
    normalized = (serial_no or "").strip().lower()
    if not normalized:
        return False
    values = [
        (order_item.serial_no or "").strip().lower(),
        (order_item.serial_no_2 or "").strip().lower(),
    ]
    return normalized in values


def find_customer_order_item_by_serial(
    db: Session,
    service: ServiceRequest,
    serial_no: str,
) -> OrderItem | None:
    item = find_order_item_by_serial(db, serial_no)
    if item is None:
        return None
    order = db.get(Order, item.order_id)
    if order is None or order.deleted_at is not None:
        return None
    if not order_matches_service_customer(order, service):
        return None
    return item


def _installation_request_ready_for_service(inst: InstallationRequest | None) -> bool:
    return inst is not None and (inst.status or "") in SERVICE_ELIGIBLE_INSTALLATION_REQUEST_STATUSES


def order_item_is_installed_for_service(db: Session, order_item: OrderItem) -> bool:
    """True when installation work is done enough to raise service (matches order UI installation states)."""
    if (order_item.installation_status or "").strip() == SERVICE_ELIGIBLE_INSTALLATION_STATUS:
        return True
    inst = db.scalar(
        select(InstallationRequest)
        .where(InstallationRequest.order_item_id == order_item.id)
        .order_by(InstallationRequest.updated_at.desc())
        .limit(1)
    )
    if _installation_request_ready_for_service(inst):
        return True
    serial_filters = []
    serial_one = (order_item.serial_no or "").strip()
    serial_two = (order_item.serial_no_2 or "").strip()
    if serial_one:
        serial_filters.append(func.lower(InstallationRequest.serial_no) == serial_one.lower())
    if serial_two:
        serial_filters.append(func.lower(InstallationRequest.serial_no_2) == serial_two.lower())
    if not serial_filters:
        return False
    inst = db.scalar(
        select(InstallationRequest)
        .where(
            InstallationRequest.order_id == order_item.order_id,
            or_(*serial_filters),
        )
        .order_by(InstallationRequest.updated_at.desc())
        .limit(1)
    )
    return _installation_request_ready_for_service(inst)


def find_customer_installed_order_item(
    db: Session,
    service: ServiceRequest,
    serial_no: str,
) -> OrderItem | None:
    """Serial on any order belonging to this service customer, with installation completed."""
    item = find_customer_order_item_by_serial(db, service, serial_no)
    if item is None:
        return None
    if not order_item_is_installed_for_service(db, item):
        return None
    return item


def filter_installed_items_by_serial(
    installed_items: list[OrderItem],
    serial_no: str,
) -> list[OrderItem]:
    matched = [row for row in installed_items if order_item_matches_serial(row, serial_no)]
    return matched


def find_order_item_by_serial_on_order(
    db: Session,
    order_id: int,
    serial_no: str,
    serial_no_2: str | None = None,
) -> OrderItem | None:
    serial = (serial_no or "").strip()
    serial2 = (serial_no_2 or "").strip() or None
    if not serial:
        return None
    terms = [
        func.lower(func.coalesce(OrderItem.serial_no, "")) == serial.lower(),
        func.lower(func.coalesce(OrderItem.serial_no_2, "")) == serial.lower(),
    ]
    if serial2:
        terms.append(func.lower(func.coalesce(OrderItem.serial_no_2, "")) == serial2.lower())
        terms.append(func.lower(func.coalesce(OrderItem.serial_no, "")) == serial2.lower())
        terms.append(func.lower(func.coalesce(OrderItem.serial_no_2, "")) == serial.lower())
    return db.scalar(
        select(OrderItem).where(
            OrderItem.order_id == order_id,
            or_(*terms),
        )
    )


def serial_exists_in_order_records(db: Session, serial_no: str) -> bool:
    return find_order_item_by_serial(db, serial_no) is not None


def associate_serial_with_service_order(
    db: Session,
    *,
    order_id: int,
    serial_no: str,
    serial_no_2: str | None = None,
    template_item: OrderItem | None = None,
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
            return item

    if not items and template_item is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order has no line items to attach a serial number")

    template = template_item or items[0]
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
        installation_status=template.installation_status or "Submitted",
    )
    db.add(new_item)
    db.flush()
    return new_item
