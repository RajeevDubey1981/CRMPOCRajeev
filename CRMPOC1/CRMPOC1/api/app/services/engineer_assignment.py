from __future__ import annotations

from sqlalchemy import case, func, select, union_all
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.service import ServiceRequest, ServiceRequestUnit
from app.models.user import User
from app.schemas.installation import InstallationEngineerAssignmentOption
from app.services.geo import match_engineer, match_rank

INSTALLATION_PENDING_STATUSES = ("Assigned", "In Progress", "Payment Pending", "Settlement Pending")
INSTALLATION_SUCCESS_STATUSES = ("Completed", "Settlement Approved")
INSTALLATION_UNSUCCESS_STATUSES = ("Returned", "Rejected")

SERVICE_TERMINAL_STATUSES = ("Closed", "Cancelled", "Rejected")
COMPLAINT_TERMINAL_STATUSES = ("Resolved", "Rejected")


def get_engineer_assignment_options(
    db: Session,
    address: str | None = None,
    pincode: str | None = None,
    state: str | None = None,
    district: str | None = None,
) -> list[InstallationEngineerAssignmentOption]:
    """Engineers to pick from. With the customer's address, the nearest come first: same pin code, same area (first 3
    digits), same district, same state, then the rest; within a group the one with the fewest pending jobs first.
    The pin code, state and district typed for the customer count first; the address text is used for what is missing."""
    where = bool((address or "").strip() or pincode or state or district)
    engineers = db.scalars(
        select(User)
        .where(User.deleted_at.is_(None), User.is_active.is_(True), User.role == "engineer")
        .order_by(User.name)
    ).all()
    if not engineers:
        return []

    engineer_ids = [engineer.id for engineer in engineers]

    installation_pending_rows = db.execute(
        select(
            InstallationRequest.assigned_engineer,
            func.count(InstallationRequest.id),
        )
        .where(
            InstallationRequest.assigned_engineer.in_(engineer_ids),
            InstallationRequest.status.in_(INSTALLATION_PENDING_STATUSES),
        )
        .group_by(InstallationRequest.assigned_engineer)
    ).all()
    installation_pending_map = {
        engineer_id: int(count)
        for engineer_id, count in installation_pending_rows
        if engineer_id is not None
    }

    assignment_rows = union_all(
        select(
            ServiceRequest.assigned_engineer_id.label("engineer_id"),
            ServiceRequest.id.label("service_request_id"),
        ).where(
            ServiceRequest.assigned_engineer_id.in_(engineer_ids),
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.status.notin_(SERVICE_TERMINAL_STATUSES),
        ),
        select(
            ServiceRequestUnit.assigned_engineer_id.label("engineer_id"),
            ServiceRequestUnit.service_request_id.label("service_request_id"),
        )
        .join(ServiceRequest, ServiceRequest.id == ServiceRequestUnit.service_request_id)
        .where(
            ServiceRequestUnit.assigned_engineer_id.in_(engineer_ids),
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.status.notin_(SERVICE_TERMINAL_STATUSES),
        ),
    ).subquery("assignment_rows")

    service_assignment_rows = db.execute(
        select(
            assignment_rows.c.engineer_id,
            func.count(func.distinct(assignment_rows.c.service_request_id)),
        )
        .group_by(assignment_rows.c.engineer_id)
    ).all()
    service_pending_map = {
        engineer_id: int(count)
        for engineer_id, count in service_assignment_rows
        if engineer_id is not None
    }

    complaint_pending_rows = db.execute(
        select(
            Complaint.assigned_engineer,
            func.count(Complaint.id),
        )
        .where(
            Complaint.assigned_engineer.in_(engineer_ids),
            Complaint.status.notin_(COMPLAINT_TERMINAL_STATUSES),
        )
        .group_by(Complaint.assigned_engineer)
    ).all()
    complaint_pending_map = {
        engineer_id: int(count)
        for engineer_id, count in complaint_pending_rows
        if engineer_id is not None
    }

    performance_rows = db.execute(
        select(
            InstallationRequest.assigned_engineer,
            func.sum(
                case(
                    (InstallationRequest.status.in_(INSTALLATION_SUCCESS_STATUSES), 1),
                    else_=0,
                )
            ).label("completed_count"),
            func.sum(
                case(
                    (InstallationRequest.status.in_(INSTALLATION_UNSUCCESS_STATUSES), 1),
                    else_=0,
                )
            ).label("unsuccessful_count"),
        )
        .where(InstallationRequest.assigned_engineer.in_(engineer_ids))
        .group_by(InstallationRequest.assigned_engineer)
    ).all()

    performance_map: dict[int, tuple[int, int]] = {}
    for engineer_id, completed_count, unsuccessful_count in performance_rows:
        if engineer_id is not None:
            performance_map[engineer_id] = (int(completed_count or 0), int(unsuccessful_count or 0))

    options: list[InstallationEngineerAssignmentOption] = []
    for engineer in engineers:
        completed_count, unsuccessful_count = performance_map.get(engineer.id, (0, 0))
        rated_jobs = completed_count + unsuccessful_count
        rating = 0.0 if rated_jobs == 0 else round((completed_count / rated_jobs) * 5, 1)
        pending_requests = (
            installation_pending_map.get(engineer.id, 0)
            + service_pending_map.get(engineer.id, 0)
            + complaint_pending_map.get(engineer.id, 0)
        )
        options.append(
            InstallationEngineerAssignmentOption(
                id=engineer.id,
                name=engineer.name,
                email=engineer.email,
                pending_requests=pending_requests,
                rating=rating,
                completed_requests=completed_count,
                pincode=engineer.pincode,
                state=engineer.state,
                district=engineer.district,
                match=match_engineer(address, engineer.pincode, engineer.state, engineer.district, pincode, state, district) if where else "",
            )
        )
    if where:
        options.sort(key=lambda o: (match_rank(o.match), o.pending_requests, o.name.lower()))
    return options
