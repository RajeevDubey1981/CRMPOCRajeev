"""Per-unit serial verification and observation workflow helpers."""

from __future__ import annotations

from app.services.role_access import role_key as canonical_role_key

from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.field_photo import FieldPhoto
from app.models.item_master import ItemMaster
from app.models.order import OrderItem
from app.models.service import (
    ServiceApproval,
    ServiceCompletion,
    ServiceObservation,
    ServicePaymentRequest,
    ServiceRequest,
    ServiceRequestUnit,
)
from app.models.user import User

UNIT_STATUS_ASSIGNED = "Assigned"
UNIT_STATUS_ENGINEER_VISIT = "Engineer Visit"
UNIT_STATUS_SERIAL_PENDING = "Serial Verification Pending"
UNIT_STATUS_SERIAL_VERIFIED = "Serial Verified"
UNIT_STATUS_PENDING_TEAM_REVIEW = "Pending Service Team Review"
UNIT_STATUS_PENDING_APPROVAL = "Pending Service Approval"
UNIT_STATUS_APPROVED = "Approved for Service"
UNIT_STATUS_REJECTED = "Rejected"
UNIT_STATUS_COMPLETED = "Service Completed"
UNIT_STATUS_COMPLETION_PENDING = "Completion Pending Approval"
UNIT_STATUS_WAITING_PART = "Waiting for Part"
UNIT_STATUS_CUSTOMER_UNAVAILABLE = "Customer Not Available"
UNIT_STATUS_PAYMENT_REQUESTED = "Payment Requested"
UNIT_STATUS_PAYMENT_COMPLETED = "Payment Completed"
UNIT_STATUS_CLOSED = "Closed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def unit_primary_serial(unit: ServiceRequestUnit) -> str | None:
    serial = (unit.serial_no or "").strip()
    return serial or None


def unit_serial_values(unit: ServiceRequestUnit) -> list[str]:
    values: list[str] = []
    for raw in (unit.serial_no, unit.serial_no_2):
        serial = (raw or "").strip()
        if serial:
            values.append(serial)
    return values


def serial_matches_unit(unit: ServiceRequestUnit, serial_no: str) -> bool:
    normalized = serial_no.strip().lower()
    return any(value.lower() == normalized for value in unit_serial_values(unit))


def list_work_units(
    db: Session,
    service_id: int,
    *,
    engineer_id: int | None = None,
) -> list[ServiceRequestUnit]:
    stmt = (
        select(ServiceRequestUnit)
        .where(ServiceRequestUnit.service_request_id == service_id)
        .order_by(ServiceRequestUnit.id)
    )
    if engineer_id is not None:
        stmt = stmt.where(ServiceRequestUnit.assigned_engineer_id == engineer_id)
    return list(db.scalars(stmt).all())


def observations_for_service(db: Session, service_id: int) -> dict[int, ServiceObservation]:
    rows = db.scalars(
        select(ServiceObservation)
        .where(ServiceObservation.service_request_id == service_id)
        .order_by(ServiceObservation.submitted_at)
    ).all()
    mapped: dict[int, ServiceObservation] = {}
    for row in rows:
        if row.service_request_unit_id is not None:
            mapped[row.service_request_unit_id] = row
    return mapped


def approvals_for_service(db: Session, service_id: int) -> dict[int, ServiceApproval]:
    rows = db.scalars(
        select(ServiceApproval)
        .where(ServiceApproval.service_request_id == service_id)
        .order_by(ServiceApproval.approved_at)
    ).all()
    mapped: dict[int, ServiceApproval] = {}
    for row in rows:
        if row.service_request_unit_id is not None:
            mapped[row.service_request_unit_id] = row
    return mapped


def completions_for_service(db: Session, service_id: int) -> dict[int, ServiceCompletion]:
    rows = db.scalars(
        select(ServiceCompletion)
        .where(ServiceCompletion.service_request_id == service_id)
        .order_by(ServiceCompletion.completed_at)
    ).all()
    mapped: dict[int, ServiceCompletion] = {}
    for row in rows:
        if row.service_request_unit_id is not None:
            mapped[row.service_request_unit_id] = row
    return mapped


def payment_requests_for_service(db: Session, service_id: int) -> dict[int, ServicePaymentRequest]:
    rows = db.scalars(
        select(ServicePaymentRequest)
        .where(ServicePaymentRequest.service_request_id == service_id)
        .order_by(ServicePaymentRequest.created_at)
    ).all()
    mapped: dict[int, ServicePaymentRequest] = {}
    for row in rows:
        if row.service_request_unit_id is not None:
            mapped[row.service_request_unit_id] = row
    return mapped


def sync_aggregate_service_status(db: Session, service: ServiceRequest) -> None:
    """Derive parent service request status from per-unit statuses."""
    units = list_work_units(db, service.id)
    if not units:
        return

    statuses = [unit.unit_status or UNIT_STATUS_ASSIGNED for unit in units]

    if all(status in (UNIT_STATUS_PAYMENT_COMPLETED, UNIT_STATUS_CLOSED) for status in statuses):
        service.status = "Payment Completed" if all(status == UNIT_STATUS_PAYMENT_COMPLETED for status in statuses) else "Closed"
        if all(status == UNIT_STATUS_CLOSED for status in statuses):
            service.closed_at = _now()
    elif any(status == UNIT_STATUS_COMPLETION_PENDING for status in statuses):
        service.status = UNIT_STATUS_COMPLETION_PENDING
    elif all(
        status in (UNIT_STATUS_COMPLETED, UNIT_STATUS_PAYMENT_REQUESTED, UNIT_STATUS_PAYMENT_COMPLETED)
        for status in statuses
    ):
        if any(status == UNIT_STATUS_PAYMENT_REQUESTED for status in statuses):
            service.status = "Payment Requested"
        else:
            service.status = "Service Completed"
    elif any(
        status in (
            UNIT_STATUS_APPROVED,
            UNIT_STATUS_COMPLETED,
            UNIT_STATUS_PAYMENT_REQUESTED,
            UNIT_STATUS_PAYMENT_COMPLETED,
        )
        for status in statuses
    ):
        service.status = "Service In Progress"
    elif any(status in (UNIT_STATUS_WAITING_PART, UNIT_STATUS_CUSTOMER_UNAVAILABLE) for status in statuses):
        service.status = next(
            status for status in statuses
            if status in (UNIT_STATUS_WAITING_PART, UNIT_STATUS_CUSTOMER_UNAVAILABLE)
        )
    elif any(status in (UNIT_STATUS_PENDING_APPROVAL, UNIT_STATUS_PENDING_TEAM_REVIEW) for status in statuses):
        if all(status in (UNIT_STATUS_PENDING_APPROVAL, UNIT_STATUS_PENDING_TEAM_REVIEW, UNIT_STATUS_REJECTED) for status in statuses):
            service.status = "Pending Service Approval"
        else:
            service.status = "Service In Progress"
    elif any(status == UNIT_STATUS_SERIAL_PENDING for status in statuses):
        service.status = "Serial Verification Review"
    elif all(status == UNIT_STATUS_ENGINEER_VISIT for status in statuses):
        service.status = "Engineer Visit"
    elif all(status == UNIT_STATUS_SERIAL_VERIFIED for status in statuses):
        service.status = "Serial Verified"
    elif any(status == UNIT_STATUS_SERIAL_VERIFIED for status in statuses):
        service.status = "Engineer Visit"
    else:
        service.status = "Assigned"
    service.status_date = _now()


def align_units_to_service_status(db: Session, service: ServiceRequest, target_status: str) -> None:
    """Apply an admin-selected parent step to every unit so reloads stay consistent."""
    units = list_work_units(db, service.id)
    if target_status == "Assigned":
        for unit in units:
            unit.unit_status = UNIT_STATUS_ASSIGNED
            unit.serial_verified_at = None
    elif target_status == "Engineer Visit":
        for unit in units:
            unit.unit_status = UNIT_STATUS_ENGINEER_VISIT
            unit.serial_verified_at = None
    elif target_status == "Serial Verification Review":
        for unit in units:
            unit.unit_status = UNIT_STATUS_SERIAL_PENDING
            unit.serial_verified_at = None
    elif target_status == "Serial Verified":
        for unit in units:
            unit.unit_status = UNIT_STATUS_SERIAL_VERIFIED
            unit.serial_verified_at = unit.serial_verified_at or _now()


def sync_service_request_from_units(
    db: Session,
    service: ServiceRequest,
    *,
    engineer_id: int | None = None,
) -> None:
    units = list_work_units(db, service.id, engineer_id=engineer_id)
    if not units:
        return

    verified_units = [unit for unit in units if unit.serial_verified_at is not None]
    if verified_units:
        primary = verified_units[0]
        service.serial_no = unit_primary_serial(primary) or service.serial_no
        service.warranty_status = primary.warranty_status or service.warranty_status
        service.service_type = primary.service_type or service.service_type
        order_item = db.get(OrderItem, primary.order_item_id) if primary.order_item_id else None
        if order_item is not None:
            service.order_item_id = order_item.id
            service.order_id = order_item.order_id

    sync_aggregate_service_status(db, service)


def unverified_units(
    db: Session,
    service_id: int,
    *,
    engineer_id: int | None = None,
) -> list[ServiceRequestUnit]:
    units = list_work_units(db, service_id, engineer_id=engineer_id)
    return [unit for unit in units if unit.serial_verified_at is None]


def units_without_observation(
    db: Session,
    service_id: int,
    *,
    engineer_id: int | None = None,
) -> list[ServiceRequestUnit]:
    units = list_work_units(db, service_id, engineer_id=engineer_id)
    observations = observations_for_service(db, service_id)
    return [unit for unit in units if unit.id not in observations]


MIN_FIELD_PHOTOS = 1  # an engineer must photograph the machine before a serial can be verified


_NO_SERIAL = {"0", "-", "--", "na", "n/a", "nil", "none", "null", "no"}


def clean_serial(value: str | None) -> str | None:
    """A typed placeholder (0, -, NA ...) is not a serial number: treat it as nothing entered."""
    text = (value or "").strip()
    return None if not text or text.lower() in _NO_SERIAL else text


def product_serial_count(db: Session, order_item: OrderItem | None, fallback: int = 1) -> int:
    """How many serials this product carries by default: one for a refrigerator or window AC, two for a split AC
    (indoor and outdoor). It is the product's own setting in the item master, not whatever the screen happened to ask."""
    master = db.get(ItemMaster, order_item.item_id) if order_item is not None and order_item.item_id else None
    return int(master.serial_count) if master is not None and master.serial_count else fallback


def apply_serial_rule(db: Session, order_item: OrderItem | None, serial_no_2: str | None, fallback: int = 1) -> str | None:
    """The second serial for a unit of this product: none for a one-serial product, required for a two-serial one."""
    second = clean_serial(serial_no_2)
    count = product_serial_count(db, order_item, fallback)
    if count < 2:
        return None
    if not second and order_item is not None:
        second = clean_serial(order_item.serial_no_2)
    if not second:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This product has {count} serial numbers. Enter both serials.")
    return second


def verify_unit_serial(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    derive_context: Callable,
    find_order_item_by_serial: Callable,
    *,
    serial_no: str | None = None,
    serial_no_2: str | None = None,
) -> ServiceRequestUnit:
    if unit.service_request_id != service.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unit does not belong to this service request")
    if unit.serial_verified_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial is already verified for this unit")
    if unit.unit_status == UNIT_STATUS_SERIAL_PENDING and canonical_role_key(user.role) != "engineer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial verification is awaiting admin review")

    resolved_serial = (serial_no or "").strip() or unit_primary_serial(unit)
    resolved_serial_2 = clean_serial(serial_no_2)
    if not resolved_serial:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required for this unit")

    role_key = canonical_role_key(user.role)
    if role_key == "engineer":
        photo_count = db.scalar(select(func.count(FieldPhoto.id)).where(FieldPhoto.service_request_unit_id == unit.id)) or 0
        if photo_count < MIN_FIELD_PHOTOS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Take at least {MIN_FIELD_PHOTOS} photo of the machine first (serial {resolved_serial}). Tap Photos on that serial.",
            )

    lookup_item = find_order_item_by_serial(db, resolved_serial)
    submits_for_review = role_key in {"engineer", "vendor"}

    if lookup_item is None:
        if submits_for_review:
            unit.serial_no = resolved_serial
            unit.serial_no_2 = resolved_serial_2
            unit.unit_status = UNIT_STATUS_SERIAL_PENDING
            engineer_id = user.id if role_key == "engineer" else unit.assigned_engineer_id
            sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
            return unit
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found in order records")

    context = derive_context(db, lookup_item)
    existing_for_serial = db.scalar(
        select(ServiceRequestUnit).where(
            ServiceRequestUnit.service_request_id == service.id,
            ServiceRequestUnit.order_item_id == lookup_item.id,
            ServiceRequestUnit.id != unit.id,
        )
    )
    if existing_for_serial is not None:
        if existing_for_serial.assigned_engineer_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This serial is already assigned on this service request",
            )
        db.delete(existing_for_serial)
        db.flush()

    unit.serial_no = resolved_serial
    unit.serial_no_2 = apply_serial_rule(db, lookup_item, resolved_serial_2)
    unit.order_item_id = lookup_item.id
    unit.warranty_status = context["warranty_status"]
    unit.service_type = context["service_type"]
    if submits_for_review:
        unit.unit_status = UNIT_STATUS_SERIAL_PENDING
    else:
        unit.serial_verified_at = _now()
        unit.unit_status = UNIT_STATUS_SERIAL_VERIFIED

    engineer_id = user.id if role_key == "engineer" else unit.assigned_engineer_id
    sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
    return unit


def bulk_verify_units(
    db: Session,
    service: ServiceRequest,
    user: User,
    derive_context: Callable,
    find_order_item_by_serial: Callable,
    unit_ids: list[int] | None = None,
) -> list[ServiceRequestUnit]:
    engineer_id = user.id if canonical_role_key(user.role) == "engineer" else None
    candidates = unverified_units(db, service.id, engineer_id=engineer_id)
    if unit_ids:
        allowed = set(unit_ids)
        candidates = [unit for unit in candidates if unit.id in allowed]
    if not candidates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No units available to verify")

    verified: list[ServiceRequestUnit] = []
    for unit in candidates:
        verify_unit_serial(
            db,
            service,
            unit,
            user,
            derive_context,
            find_order_item_by_serial,
        )
        verified.append(unit)
    return verified


def submit_unit_observation(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    body,
    json_dump: Callable,
) -> ServiceObservation:
    if unit.service_request_id != service.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unit does not belong to this service request")
    if unit.serial_verified_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verify serial before submitting observation")

    existing = db.scalar(
        select(ServiceObservation).where(
            ServiceObservation.service_request_id == service.id,
            ServiceObservation.service_request_unit_id == unit.id,
        )
    )
    if existing is not None:
        role = canonical_role_key(user.role)
        is_editor_engineer = role == "engineer"
        # Service Team/Manager/Admin may also correct the recommendation while it's still in review --
        # the frontend already shows them this form, so the backend has to actually honor it.
        is_reviewer_editor = can_user_forward_at_all(user) or can_user_approve_at_all(user)
        status_allowed = unit.unit_status in {UNIT_STATUS_PENDING_TEAM_REVIEW, UNIT_STATUS_PENDING_APPROVAL, UNIT_STATUS_REJECTED}
        if not status_allowed or not (is_editor_engineer or is_reviewer_editor):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Observation already submitted for this serial")
        existing.problem_found = body.problem_found
        existing.observation = body.observation
        existing.recommended_action = body.recommended_action
        existing.parts_required_json = json_dump(body.parts_required)
        existing.misc_required_json = json_dump(body.misc_required)
        existing.estimated_service_charge = body.estimated_service_charge
        existing.estimated_parts_charge = body.estimated_parts_charge
        existing.remarks = body.remarks
        existing.submitted_at = _now()
        # Only the engineer re-editing restarts the review chain; a reviewer's own correction
        # while handling it doesn't send their own in-progress item back a stage.
        if is_editor_engineer:
            unit.unit_status = UNIT_STATUS_PENDING_TEAM_REVIEW
        return existing

    observation = ServiceObservation(
        service_request_id=service.id,
        service_request_unit_id=unit.id,
        submitted_by_user_id=user.id,
        serial_no=unit_primary_serial(unit),
        warranty_status=unit.warranty_status,
        service_type=unit.service_type,
        problem_found=body.problem_found,
        observation=body.observation,
        recommended_action=body.recommended_action,
        parts_required_json=json_dump(body.parts_required),
        misc_required_json=json_dump(body.misc_required),
        estimated_service_charge=body.estimated_service_charge,
        estimated_parts_charge=body.estimated_parts_charge,
        remarks=body.remarks,
        submitted_at=_now(),
    )
    db.add(observation)
    unit.unit_status = UNIT_STATUS_PENDING_TEAM_REVIEW

    engineer_id = user.id if canonical_role_key(user.role) == "engineer" else unit.assigned_engineer_id
    sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
    return observation


def bulk_submit_observations(
    db: Session,
    service: ServiceRequest,
    user: User,
    items: list,
    json_dump: Callable,
) -> list[ServiceObservation]:
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No observations provided")

    engineer_id = user.id if canonical_role_key(user.role) == "engineer" else None
    units = list_work_units(db, service.id, engineer_id=engineer_id)
    unit_map = {unit.id: unit for unit in units}
    existing = observations_for_service(db, service.id)
    created: list[ServiceObservation] = []

    for item in items:
        unit = unit_map.get(item.unit_id)
        if unit is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Unit {item.unit_id} is not assigned to you on this request",
            )
        if unit.serial_verified_at is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Verify serial before submitting observation for unit {item.unit_id}",
            )
        if unit.id in existing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Observation already submitted for unit {item.unit_id}",
            )
        observation = ServiceObservation(
            service_request_id=service.id,
            service_request_unit_id=unit.id,
            submitted_by_user_id=user.id,
            serial_no=unit_primary_serial(unit),
            warranty_status=unit.warranty_status,
            service_type=unit.service_type,
            problem_found=item.problem_found,
            observation=item.observation,
            recommended_action=item.recommended_action,
            parts_required_json=json_dump(item.parts_required),
            misc_required_json=json_dump(item.misc_required),
            estimated_service_charge=item.estimated_service_charge,
            estimated_parts_charge=item.estimated_parts_charge,
            remarks=item.remarks,
            submitted_at=_now(),
        )
        db.add(observation)
        unit.unit_status = UNIT_STATUS_PENDING_TEAM_REVIEW
        created.append(observation)

    db.flush()
    sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
    return created


def backfill_unit_verification_from_service(db: Session, service: ServiceRequest) -> None:
    """Map legacy single-serial verification onto matching unit rows."""
    if not service.serial_no or service.status not in {
        "Serial Verified",
        "Pending Service Approval",
        "Approved for Service",
        "Service In Progress",
        "Service Completed",
        "Payment Requested",
        "Payment Completed",
        "Closed",
    }:
        return
    for unit in list_work_units(db, service.id):
        if unit.serial_verified_at is not None:
            continue
        if serial_matches_unit(unit, service.serial_no):
            unit.serial_verified_at = service.status_date or _now()
            unit.warranty_status = service.warranty_status
            unit.service_type = service.service_type
            unit.unit_status = UNIT_STATUS_SERIAL_VERIFIED


# The chain: Engineer recommends -> Service Team reviews and forwards -> Service Manager approves
# (capped) -> Admin/Sub Admin/Incool decide above the cap, and can override any stage at any amount.
# Service-desk roles can forward but never approve/reject outright: that's Service Manager/Admin's call.
APPROVAL_CAP_AMOUNT = 2500
ADMIN_OVERRIDE_ROLES = frozenset({"admin", "incool", "sub_admin"})
SERVICE_MANAGER_ROLES = frozenset({"service_manager"})
SERVICE_DESK_ROLES = frozenset({"service", "indcool_service", "indcool"})
UNIT_APPROVAL_ROLES = ADMIN_OVERRIDE_ROLES | SERVICE_MANAGER_ROLES
UNIT_FORWARD_ROLES = ADMIN_OVERRIDE_ROLES | SERVICE_DESK_ROLES


def unit_requested_amount(observation: ServiceObservation | None) -> float:
    if observation is None:
        return 0.0
    service_amt = float(observation.estimated_service_charge or 0)
    parts_amt = float(observation.estimated_parts_charge or 0)
    return service_amt + parts_amt


def requires_admin_approval(amount: float) -> bool:
    return amount > APPROVAL_CAP_AMOUNT


def can_user_approve_at_all(user: User) -> bool:
    return canonical_role_key(user.role) in UNIT_APPROVAL_ROLES


def can_user_approve_amount(user: User, amount: float) -> bool:
    role = canonical_role_key(user.role)
    if role in ADMIN_OVERRIDE_ROLES:
        return True
    if role in SERVICE_MANAGER_ROLES:
        return not requires_admin_approval(amount)
    return False


def can_user_forward_at_all(user: User) -> bool:
    return canonical_role_key(user.role) in UNIT_FORWARD_ROLES


def forward_unit_to_manager(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    decision: str,
    remarks: str | None,
) -> None:
    """Service Team's review step between the engineer's recommendation and Service Manager's decision.
    "Forward" moves it on; "Send back" returns it to the engineer, same as a rejection at that stage."""
    if unit.unit_status != UNIT_STATUS_PENDING_TEAM_REVIEW:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This unit is not pending service team review")
    if not can_user_forward_at_all(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the Service Team or Admin can review this before it reaches the Service Manager")
    if decision == "Forward":
        unit.unit_status = UNIT_STATUS_PENDING_APPROVAL
    else:
        unit.unit_status = UNIT_STATUS_REJECTED


def approve_unit(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    decision: str,
    remarks: str | None,
    observation: ServiceObservation,
) -> ServiceApproval:
    if unit.unit_status != UNIT_STATUS_PENDING_APPROVAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This unit is not pending service approval")
    if not can_user_approve_at_all(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the Service Manager or Admin can decide this — your role can recommend, not approve")
    if decision == "Approve":
        amount = unit_requested_amount(observation)
        if not can_user_approve_amount(user, amount):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This needs Admin approval — the engineer's recommended work (₹{amount:,.0f}) is over the "
                f"₹{APPROVAL_CAP_AMOUNT:,.0f} Service Manager limit.",
            )
    approval = ServiceApproval(
        service_request_id=service.id,
        service_request_unit_id=unit.id,
        observation_id=observation.id,
        decision=decision,
        remarks=remarks,
        approved_by=user.id,
        approved_at=_now(),
    )
    db.add(approval)
    # A Service Manager rejection goes back to Service Team, not straight to a dead end — they decide
    # whether to forward it again (e.g. after a correction) or send it back to the engineer themselves.
    unit.unit_status = UNIT_STATUS_APPROVED if decision == "Approve" else UNIT_STATUS_PENDING_TEAM_REVIEW
    if decision == "Approve":
        service.approved_at = _now()
    sync_aggregate_service_status(db, service)
    return approval


def bulk_forward_units(
    db: Session,
    service: ServiceRequest,
    user: User,
    decision: str,
    remarks: str | None,
    unit_ids: list[int] | None = None,
) -> list[ServiceRequestUnit]:
    units = list_work_units(db, service.id)
    pending = [unit for unit in units if unit.unit_status == UNIT_STATUS_PENDING_TEAM_REVIEW]
    if unit_ids:
        allowed = set(unit_ids)
        pending = [unit for unit in pending if unit.id in allowed]
    if not pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No units pending service team review")
    for unit in pending:
        forward_unit_to_manager(db, service, unit, user, decision, remarks)
    sync_aggregate_service_status(db, service)
    return pending


def bulk_approve_units(
    db: Session,
    service: ServiceRequest,
    user: User,
    decision: str,
    remarks: str | None,
    unit_ids: list[int] | None = None,
) -> list[ServiceApproval]:
    observations = observations_for_service(db, service.id)
    units = list_work_units(db, service.id)
    pending = [unit for unit in units if unit.unit_status == UNIT_STATUS_PENDING_APPROVAL]
    if unit_ids:
        allowed = set(unit_ids)
        pending = [unit for unit in pending if unit.id in allowed]
    if not pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No units pending approval")
    created: list[ServiceApproval] = []
    for unit in pending:
        observation = observations.get(unit.id)
        if observation is None:
            continue
        created.append(approve_unit(db, service, unit, user, decision, remarks, observation))
    return created


def complete_unit(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    is_engineer: bool,
    is_vendor: bool,
    vendor_id: int | None,
    body,
    proof_path: str,
    json_dump: Callable,
    json_load: Callable,
) -> ServiceCompletion:
    if unit.unit_status not in {
        UNIT_STATUS_APPROVED,
        UNIT_STATUS_WAITING_PART,
        UNIT_STATUS_CUSTOMER_UNAVAILABLE,
    }:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unit must be approved before completion")
    existing = db.scalar(
        select(ServiceCompletion).where(
            ServiceCompletion.service_request_id == service.id,
            ServiceCompletion.service_request_unit_id == unit.id,
        )
    )
    if existing is not None:
        if unit.unit_status not in {UNIT_STATUS_WAITING_PART, UNIT_STATUS_CUSTOMER_UNAVAILABLE}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This unit is already marked completed")
        parts = body.parts_replaced if hasattr(body, "parts_replaced") and isinstance(body.parts_replaced, list) else []
        existing.work_performed = body.work_performed
        existing.parts_replaced_json = json_dump(parts)
        existing.service_notes = body.service_notes
        existing.service_date = body.service_date
        existing.old_part_serial_no = body.old_part_serial_no
        existing.new_part_serial_no = body.new_part_serial_no
        existing.customer_acknowledgement_path = proof_path or existing.customer_acknowledgement_path
        existing.final_amount = body.final_amount
        existing.completion_remarks = body.completion_remarks
        existing.engineer_completion_code = getattr(body, "engineer_completion_code", None)
        existing.completed_at = _now()
        requested_status = getattr(body, "completion_status", UNIT_STATUS_COMPLETED)
        unit.unit_status = UNIT_STATUS_COMPLETION_PENDING if requested_status == UNIT_STATUS_COMPLETED else requested_status
        sync_aggregate_service_status(db, service)
        return existing

    parts = body.parts_replaced if hasattr(body, "parts_replaced") and isinstance(body.parts_replaced, list) else []
    completion = ServiceCompletion(
        service_request_id=service.id,
        service_request_unit_id=unit.id,
        performed_by_type="engineer" if is_engineer else "vendor",
        performed_by_user_id=user.id if is_engineer else None,
        performed_by_vendor_id=vendor_id if is_vendor else None,
        work_performed=body.work_performed,
        parts_replaced_json=json_dump(parts),
        service_notes=body.service_notes,
        service_date=body.service_date,
        old_part_serial_no=body.old_part_serial_no,
        new_part_serial_no=body.new_part_serial_no,
        customer_acknowledgement_path=proof_path,
        final_amount=body.final_amount,
        completion_remarks=body.completion_remarks,
        engineer_completion_code=getattr(body, "engineer_completion_code", None),
        completed_at=_now(),
    )
    db.add(completion)
    requested_status = getattr(body, "completion_status", UNIT_STATUS_COMPLETED)
    unit.unit_status = UNIT_STATUS_COMPLETION_PENDING if requested_status == UNIT_STATUS_COMPLETED else requested_status

    order_item = db.get(OrderItem, unit.order_item_id)
    if order_item is not None and unit.service_type == "Free Service":
        order_item.service_consume_count = (order_item.service_consume_count or 0) + 1

    sync_aggregate_service_status(db, service)
    if body.completion_status == UNIT_STATUS_COMPLETED and not service.completed_at:
        service.completed_at = _now()
    return completion


def raise_payment_for_unit(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
    user: User,
    requested_by_type: str,
    vendor_id: int | None,
    payment_type: str,
    qr_path: str | None,
    customer_charge_amount: float | None,
    settlement_service_amount: float | None,
    settlement_parts_amount: float | None,
    total_requested_amount: float | None,
    remarks: str | None,
) -> ServicePaymentRequest:
    if unit.unit_status != UNIT_STATUS_COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Complete service for this unit before raising payment")
    existing = db.scalar(
        select(ServicePaymentRequest).where(
            ServicePaymentRequest.service_request_id == service.id,
            ServicePaymentRequest.service_request_unit_id == unit.id,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment already requested for this unit")

    payment_request = ServicePaymentRequest(
        service_request_id=service.id,
        service_request_unit_id=unit.id,
        requested_by_type=requested_by_type,
        requested_by_user_id=user.id if requested_by_type != "vendor" else None,
        requested_by_vendor_id=vendor_id if requested_by_type == "vendor" else None,
        service_type=unit.service_type or service.service_type,
        customer_charge_amount=customer_charge_amount,
        settlement_service_amount=settlement_service_amount,
        settlement_parts_amount=settlement_parts_amount,
        total_requested_amount=total_requested_amount,
        payment_type=payment_type,
        payment_qr_code_path=qr_path,
        remarks=remarks,
        status="Requested",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(payment_request)
    unit.unit_status = UNIT_STATUS_PAYMENT_REQUESTED
    sync_aggregate_service_status(db, service)
    return payment_request


def cancel_payment_for_unit(
    db: Session,
    service: ServiceRequest,
    unit: ServiceRequestUnit,
) -> ServicePaymentRequest:
    if unit.unit_status != UNIT_STATUS_PAYMENT_REQUESTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This serial does not have a pending payment request")
    payment = db.scalar(
        select(ServicePaymentRequest)
        .where(
            ServicePaymentRequest.service_request_id == service.id,
            ServicePaymentRequest.service_request_unit_id == unit.id,
        )
        .order_by(desc(ServicePaymentRequest.created_at))
    )
    if payment is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment request found for this serial")
    db.delete(payment)
    unit.unit_status = UNIT_STATUS_COMPLETED
    sync_aggregate_service_status(db, service)
    return payment


def all_units_payment_completed(db: Session, service_id: int) -> bool:
    units = list_work_units(db, service_id)
    if not units:
        return False
    return all((unit.unit_status or UNIT_STATUS_ASSIGNED) == UNIT_STATUS_PAYMENT_COMPLETED for unit in units)


def close_service_with_units(
    db: Session,
    service: ServiceRequest,
) -> list[ServiceRequestUnit]:
    units = list_work_units(db, service.id)
    if units:
        pending = [
            unit for unit in units
            if (unit.unit_status or UNIT_STATUS_ASSIGNED) != UNIT_STATUS_PAYMENT_COMPLETED
        ]
        if pending:
            serials = ", ".join(unit.serial_no or f"#{unit.id}" for unit in pending[:5])
            suffix = f" and {len(pending) - 5} more" if len(pending) > 5 else ""
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"All serials must reach Payment Completed before closing. Pending: {serials}{suffix}",
            )
        for unit in units:
            unit.unit_status = UNIT_STATUS_CLOSED
        return units

    if service.status != "Payment Completed":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Service can be closed only after payment is completed",
        )
    return []


def reopen_service_to_engineer(
    db: Session,
    service: ServiceRequest,
    *,
    unit_id: int | None = None,
) -> None:
    allowed_statuses = {UNIT_STATUS_PAYMENT_COMPLETED, UNIT_STATUS_PAYMENT_REQUESTED, UNIT_STATUS_COMPLETED}
    units = list_work_units(db, service.id)
    if units:
        targets = units
        if unit_id is not None:
            targets = [unit for unit in units if unit.id == unit_id]
            if not targets:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        for unit in targets:
            if (unit.unit_status or UNIT_STATUS_ASSIGNED) not in allowed_statuses:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Serial {unit.serial_no or unit.id} cannot be reopened from status {unit.unit_status}",
                )
            payment = db.scalar(
                select(ServicePaymentRequest)
                .where(
                    ServicePaymentRequest.service_request_id == service.id,
                    ServicePaymentRequest.service_request_unit_id == unit.id,
                )
                .order_by(desc(ServicePaymentRequest.created_at))
            )
            if payment is not None:
                db.delete(payment)
            unit.unit_status = UNIT_STATUS_APPROVED
        sync_aggregate_service_status(db, service)
        return

    if service.status not in {"Payment Completed", "Payment Requested", "Service Completed"}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Service can be reopened only after completion or payment stages",
        )
    latest_payment = db.scalar(
        select(ServicePaymentRequest)
        .where(ServicePaymentRequest.service_request_id == service.id)
        .order_by(desc(ServicePaymentRequest.created_at))
    )
    if latest_payment is not None:
        db.delete(latest_payment)
    service.status = "Approved for Service"
    service.status_date = _now()


def backfill_unit_statuses(db: Session, service: ServiceRequest) -> None:
    observations = observations_for_service(db, service.id)
    approvals = approvals_for_service(db, service.id)
    completions = completions_for_service(db, service.id)
    payments = payment_requests_for_service(db, service.id)

    for unit in list_work_units(db, service.id):
        if unit.unit_status == UNIT_STATUS_CLOSED:
            continue
        if unit.id in payments:
            payment = payments[unit.id]
            if payment.status in ("Completed", "Approved", "Processed") or payment.processed_at:
                unit.unit_status = UNIT_STATUS_PAYMENT_COMPLETED
            else:
                unit.unit_status = UNIT_STATUS_PAYMENT_REQUESTED
            continue
        if unit.unit_status and unit.unit_status != UNIT_STATUS_ASSIGNED:
            continue
        if unit.id in completions:
            unit.unit_status = UNIT_STATUS_COMPLETED
        elif unit.id in approvals:
            unit.unit_status = (
                UNIT_STATUS_APPROVED if approvals[unit.id].decision == "Approve" else UNIT_STATUS_REJECTED
            )
        elif unit.id in observations:
            unit.unit_status = UNIT_STATUS_PENDING_TEAM_REVIEW
        elif unit.serial_verified_at:
            unit.unit_status = UNIT_STATUS_SERIAL_VERIFIED
        else:
            unit.unit_status = UNIT_STATUS_ASSIGNED
