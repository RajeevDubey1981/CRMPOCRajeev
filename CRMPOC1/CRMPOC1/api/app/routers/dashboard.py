from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.order import Order
from app.models.service import ServiceRequest, ServiceRequestUnit
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.dashboard import (
    ComplaintChart,
    ComplaintChartPoint,
    ComplaintsSummary,
    InstallationSummary,
    OrdersSummary,
    ServiceSummary,
)
from app.services.engineer_service_scope import (
    engineer_visible_complaint_filter,
    engineer_visible_service_filter,
)
from app.services.complaint_access import apply_complaint_assignment_scope
from app.services.permissions import sub_module_scope

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _scoped_complaints_stmt(db: Session, user: User) -> tuple[Select | None, bool]:
    """Return a base SELECT over visible, non-deleted complaints for this user.

    Returns (stmt, has_access). When has_access is False the dashboard returns
    zeros without running a query.
    """
    scope = sub_module_scope(db, user, "complaints", "can_view")
    if scope is not None and not scope:
        return None, False
    stmt = select(Complaint).where(Complaint.deleted_at.is_(None))
    if scope is not None:
        stmt = stmt.where(Complaint.query_type.in_(scope))
    if (user.role or "").lower() == "engineer":
        stmt = stmt.where(engineer_visible_complaint_filter(user.id))
    return apply_complaint_assignment_scope(stmt, user), True


def _count(db: Session, base: Select, status_value: str) -> int:
    return db.scalar(
        select(func.count()).select_from(
            base.where(Complaint.status == status_value).subquery()
        )
    ) or 0


@router.get("/complaints-summary", response_model=ComplaintsSummary)
def complaints_summary(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base, ok = _scoped_complaints_stmt(db, user)
    if not ok:
        return ComplaintsSummary(pending=0, resolved=0, under_process=0, rejected=0, in_process=0)
    if date_from:
        base = base.where(Complaint.comp_date >= date_from)
    if date_to:
        base = base.where(Complaint.comp_date <= date_to)
    return ComplaintsSummary(
        pending=_count(db, base, "Pending"),
        resolved=_count(db, base, "Resolved"),
        under_process=_count(db, base, "Under Process"),
        rejected=_count(db, base, "Rejected"),
        in_process=_count(db, base, "In Process"),
    )


@router.get("/installation-summary", response_model=InstallationSummary)
def installation_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    base = select(func.count(InstallationRequest.id)).where(
        InstallationRequest.status.in_(["Pending", "Assigned", "In Progress", "Settlement Pending"])
    )
    if user.role == "engineer":
        base = base.where(InstallationRequest.assigned_engineer == user.id)
    total = db.scalar(base) or 0
    gt7 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=7))) or 0
    gt15 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=15))) or 0
    gt30 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=30))) or 0
    return InstallationSummary(total_pending=total, gt7days=gt7, gt15days=gt15, gt30days=gt30)


@router.get("/orders-summary", response_model=OrdersSummary)
def orders_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = select(Order).where(Order.deleted_at.is_(None))

    if user.role == "vendor":
        vendor = db.scalar(select(Vendor).where(Vendor.email == user.email))
        if vendor is None:
            return OrdersSummary(total=0, pending=0, in_transit=0, delivered=0)
        base = base.where(Order.vendor_id == vendor.id)

    def cnt(status_val: str) -> int:
        return db.scalar(
            select(func.count()).select_from(
                base.where(Order.status == status_val).subquery()
            )
        ) or 0

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    return OrdersSummary(
        total=total,
        pending=cnt("Pending"),
        in_transit=cnt("In Transit"),
        delivered=cnt("Delivered"),
    )


@router.get("/services-summary", response_model=ServiceSummary)
def services_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))
    role = (user.role or "").lower()
    if role == "engineer":
        base = base.where(engineer_visible_service_filter(user.id))
    elif role == "vendor":
        vendor = db.scalar(select(Vendor).where(Vendor.email == user.email))
        if vendor is None:
            return ServiceSummary(new_requests=0, unassigned=0, assigned=0, pending_observation=0, pending_approval=0, approved=0, in_progress=0, payment_pending=0, completed=0, closed=0)
        base = base.where(ServiceRequest.assigned_vendor_id == vendor.id)

    def cnt(status_value: str) -> int:
        return db.scalar(select(func.count()).select_from(base.where(ServiceRequest.status == status_value).subquery())) or 0

    if role in {"engineer", "vendor"}:
        unassigned = 0
    else:
        unassigned = db.scalar(
            select(func.count()).select_from(
                select(ServiceRequest).where(
                    ServiceRequest.deleted_at.is_(None),
                    ServiceRequest.assigned_engineer_id.is_(None),
                    ServiceRequest.assigned_vendor_id.is_(None),
                ).subquery()
            )
        ) or 0

    return ServiceSummary(
        new_requests=cnt("New"),
        unassigned=unassigned,
        assigned=cnt("Assigned"),
        pending_observation=cnt("Engineer Visit"),
        pending_approval=cnt("Pending Service Approval"),
        approved=cnt("Approved for Service"),
        in_progress=cnt("Service In Progress"),
        payment_pending=cnt("Payment Requested"),
        completed=cnt("Service Completed"),
        closed=cnt("Closed"),
    )


@router.get("/complaint-chart", response_model=ComplaintChart)
def complaint_chart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base, ok = _scoped_complaints_stmt(db, user)
    now = datetime.now(timezone.utc)
    points: list[ComplaintChartPoint] = []
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        label = month_start.strftime("%Y-%m")
        if not ok:
            points.append(ComplaintChartPoint(
                month=label, pending=0, resolved=0, under_process=0, rejected=0, in_process=0,
            ))
            continue

        scoped = base.where(
            Complaint.created_at >= month_start,
            Complaint.created_at < next_month,
        )

        def cnt(status_value: str) -> int:
            return db.scalar(
                select(func.count()).select_from(
                    scoped.where(Complaint.status == status_value).subquery()
                )
            ) or 0

        points.append(ComplaintChartPoint(
            month=label,
            pending=cnt("Pending"),
            resolved=cnt("Resolved"),
            under_process=cnt("Under Process"),
            rejected=cnt("Rejected"),
            in_process=cnt("In Process"),
        ))
    return ComplaintChart(points=points)
