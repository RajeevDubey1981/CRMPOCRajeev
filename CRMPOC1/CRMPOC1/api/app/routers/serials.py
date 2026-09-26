from datetime import date
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.claim import Claim
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.serial_history import SerialHistoryEvent
from app.models.user import User
from app.schemas.serial import SerialHistoryEventOut, SerialHistoryHeader, SerialHistoryResponse, SerialLookup
from app.services.serial_history import backfill_serial_history_for_serial

router = APIRouter(prefix="/api/serials", tags=["serials"])
logger = logging.getLogger(__name__)


from app.services.role_access import is_operations_admin


def _require_history_access(user: User):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool users can access serial history.")


def _add_years(base_date: date | None, years: int | None) -> date | None:
    if base_date is None or years is None:
        return None
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle leap-day rollover consistently for non-leap target years.
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def _parse_legacy_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _whole_years_between(base_date: date | None, end_date: date | None) -> int | None:
    if base_date is None or end_date is None:
        return None
    return end_date.year - base_date.year


def _legacy_warranty_dates_from_events(rows: list[SerialHistoryEvent]) -> dict[str, date | None]:
    dates: dict[str, date | None] = {
        "pcb": None,
        "component": None,
        "machine": None,
    }
    for row in rows:
        if row.event_type != "migration" or row.event_subtype != "legacy_serial_recovery":
            continue
        if not row.metadata_json:
            continue
        try:
            metadata = json.loads(row.metadata_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(metadata, dict):
            continue
        dates["pcb"] = _parse_legacy_date(metadata.get("pcb_warrantyupto")) or dates["pcb"]
        dates["component"] = _parse_legacy_date(metadata.get("comp_warrantyupto")) or dates["component"]
        dates["machine"] = _parse_legacy_date(metadata.get("machin_warrantyupto")) or dates["machine"]
    return dates


class SerialSuggestion:
    def __init__(self, serial_no: str, item_name: str, customer_name: str, order_no: str):
        self.serial_no = serial_no
        self.item_name = item_name
        self.customer_name = customer_name
        self.order_no = order_no


@router.get("/search", response_model=list[dict])
def search(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Search for serials matching the query string."""
    search_pattern = f"%{query}%"
    items = db.query(OrderItem).where(
        func.lower(OrderItem.serial_no).like(func.lower(search_pattern))
    ).limit(10).all()

    suggestions = []
    for item in items:
        item_master = db.get(ItemMaster, item.item_id) if item.item_id else None
        order = db.get(Order, item.order_id)

        suggestions.append({
            "serial_no": item.serial_no,
            "serial_no_2": item.serial_no_2,
            "item_name": item_master.item_name if item_master else "Unknown Product",
            "item_code": item_master.item_code if item_master else None,
            "customer_name": order.customer_name if order else "Unknown Customer",
            "order_no": order.order_no if order else None,
            "installation_status": item.installation_status,
        })

    return suggestions


@router.get("/history/search", response_model=list[dict])
def search_history_serials(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_history_access(user)
    search_pattern = f"%{query.strip()}%"
    items = db.scalars(
        select(OrderItem)
        .where(
            or_(
                func.lower(func.coalesce(OrderItem.serial_no, "")).like(func.lower(search_pattern)),
                func.lower(func.coalesce(OrderItem.serial_no_2, "")).like(func.lower(search_pattern)),
            )
        )
        .limit(10)
    ).all()
    out = []
    for item in items:
        item_master = db.get(ItemMaster, item.item_id) if item.item_id else None
        order = db.get(Order, item.order_id)
        display_serial = item.serial_no or item.serial_no_2
        out.append({
            "serial_no": display_serial,
            "serial_no_2": item.serial_no_2,
            "item_name": item_master.item_name if item_master else None,
            "item_code": item_master.item_code if item_master else None,
            "order_no": order.order_no if order else None,
            "customer_name": order.customer_name if order else None,
            "installation_status": item.installation_status,
        })
    return out


@router.get("/lookup", response_model=SerialLookup)
def lookup(
    serial_no: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.scalar(select(OrderItem).where(func.lower(OrderItem.serial_no) == func.lower(serial_no)))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found")

    item_master = db.get(ItemMaster, item.item_id) if item.item_id else None
    order = db.get(Order, item.order_id)
    warranty_base = None
    if order is not None:
        warranty_base = order.actual_delivery_date or order.expected_delivery_date or order.order_date

    return SerialLookup(
        order_item_id=item.id,
        serial_no=item.serial_no,
        serial_no_2=item.serial_no_2,
        item_name=item_master.item_name if item_master else None,
        item_code=item_master.item_code if item_master else None,
        order_no=order.order_no if order else None,
        customer_name=order.customer_name if order else None,
        customer_contact=order.customer_contact if order else None,
        pcb_warranty_date=_add_years(warranty_base, item.pcb_warranty_years),
        component_warranty_date=_add_years(warranty_base, item.component_warranty_years),
        machine_warranty_date=_add_years(warranty_base, item.machine_warranty_years),
        installation_status=item.installation_status,
        free_service_count=item.free_service_count,
        service_consume_count=item.service_consume_count,
    )


def _find_order_item(db: Session, serial_no: str) -> OrderItem | None:
    return db.scalar(
        select(OrderItem).where(
            or_(
                func.lower(OrderItem.serial_no) == func.lower(serial_no),
                func.lower(OrderItem.serial_no_2) == func.lower(serial_no),
            )
        )
    )


@router.get("/{serial_no}/history", response_model=SerialHistoryResponse)
def get_serial_history(
    serial_no: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_history_access(user)
    item = _find_order_item(db, serial_no)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found")

    try:
        backfill_serial_history_for_serial(db, serial_no)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to backfill serial history for serial %s", serial_no)

    item_master = db.get(ItemMaster, item.item_id) if item.item_id else None
    order = db.get(Order, item.order_id)
    warranty_base = None
    if order is not None:
        warranty_base = order.actual_delivery_date or order.expected_delivery_date or order.order_date
    vendor_name = None
    if order and order.vendor_id:
        from app.models.vendor import Vendor
        vendor = db.get(Vendor, order.vendor_id)
        vendor_name = vendor.name_of_firm if vendor else None

    primary_serial = item.serial_no if item.serial_no and item.serial_no.lower() == serial_no.lower() else serial_no
    rows = db.scalars(
        select(SerialHistoryEvent)
        .where(func.lower(SerialHistoryEvent.serial_no) == func.lower(primary_serial))
        .order_by(SerialHistoryEvent.event_at.asc(), SerialHistoryEvent.id.asc())
    ).all()

    events = []
    for row in rows:
        metadata = None
        if row.metadata_json:
            try:
                metadata = json.loads(row.metadata_json)
            except json.JSONDecodeError:
                metadata = {"raw": row.metadata_json}
        events.append(
            SerialHistoryEventOut(
                id=row.id,
                event_at=row.event_at.isoformat(),
                event_type=row.event_type,
                event_subtype=row.event_subtype,
                performed_by=row.performed_by_name,
                title=row.title,
                description=row.description,
                remarks=row.remarks,
                metadata=metadata,
            )
        )

    legacy_warranty_dates = _legacy_warranty_dates_from_events(rows)
    pcb_warranty_date = _add_years(warranty_base, item.pcb_warranty_years) or legacy_warranty_dates["pcb"]
    component_warranty_date = (
        _add_years(warranty_base, item.component_warranty_years)
        or legacy_warranty_dates["component"]
    )
    machine_warranty_date = (
        _add_years(warranty_base, item.machine_warranty_years)
        or legacy_warranty_dates["machine"]
    )
    pcb_warranty_years = item.pcb_warranty_years
    if pcb_warranty_years is None:
        pcb_warranty_years = _whole_years_between(warranty_base, legacy_warranty_dates["pcb"])
    component_warranty_years = item.component_warranty_years
    if component_warranty_years is None:
        component_warranty_years = _whole_years_between(warranty_base, legacy_warranty_dates["component"])
    machine_warranty_years = item.machine_warranty_years
    if machine_warranty_years is None:
        machine_warranty_years = _whole_years_between(warranty_base, legacy_warranty_dates["machine"])

    header = SerialHistoryHeader(
        order_item_id=item.id,
        serial_no=item.serial_no or serial_no,
        serial_no_2=item.serial_no_2,
        item_name=item_master.item_name if item_master else None,
        item_code=item_master.item_code if item_master else None,
        order_no=order.order_no if order else None,
        customer_name=order.customer_name if order else None,
        customer_contact=order.customer_contact if order else None,
        vendor_name=vendor_name,
        installation_status=item.installation_status,
        free_service_count=item.free_service_count,
        service_consume_count=item.service_consume_count,
        pcb_warranty_years=pcb_warranty_years,
        component_warranty_years=component_warranty_years,
        machine_warranty_years=machine_warranty_years,
        pcb_warranty_date=pcb_warranty_date,
        component_warranty_date=component_warranty_date,
        machine_warranty_date=machine_warranty_date,
    )
    return SerialHistoryResponse(header=header, events=events)
