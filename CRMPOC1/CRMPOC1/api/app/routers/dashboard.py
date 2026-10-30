from datetime import date, datetime, timedelta, timezone

from app.services.role_access import role_key as canonical_role_key
from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.order import Order
from app.models.service import ServicePaymentRequest, ServiceRequest, ServiceRequestUnit
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.dashboard import (
    ComplaintChart,
    ComplaintChartPoint,
    ComplaintsSummary,
    InstallationPaymentStageOut,
    InstallationSummary,
    OrdersSummary,
    PaymentQueueItem,
    ReadyToPayItem,
    ServiceSummary,
)
from app.services.engineer_service_scope import (
    engineer_visible_complaint_filter,
    engineer_visible_service_filter,
)
from app.services.complaint_access import apply_complaint_assignment_scope
from app.services.installation_stages import stage_counts
from app.services.payment_approval_workflow import installation_payment_approval_stages, stage_index
from app.services.role_access import is_operations_admin, is_system_admin
from app.services.service_access import is_service_desk_user
from app.services.permissions import can_act_on, sub_module_scope

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
    if canonical_role_key(user.role) == "engineer":
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
    is_engineer = canonical_role_key(user.role) == "engineer"
    if not is_engineer and not can_act_on(db, user, "installations", "can_view", None):
        return InstallationSummary(total_pending=0, gt7days=0, gt15days=0, gt30days=0, stages=stage_counts({}))
    now = datetime.now(timezone.utc)
    base = select(func.count(InstallationRequest.id)).where(
        InstallationRequest.status.in_(["Pending", "Assigned", "In Progress", "Settlement Pending"])
    )
    if canonical_role_key(user.role) == "engineer":
        base = base.where(InstallationRequest.assigned_engineer == user.id)
    total = db.scalar(base) or 0
    gt7 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=7))) or 0
    gt15 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=15))) or 0
    gt30 = db.scalar(base.where(InstallationRequest.request_date < now - timedelta(days=30))) or 0
    # every stage, for the same people who see the list: engineers their own, service users theirs, call-center requests only once an engineer has them
    scope = select(InstallationRequest.status, func.count(InstallationRequest.id)).group_by(InstallationRequest.status)
    if canonical_role_key(user.role) == "engineer":
        scope = scope.where(InstallationRequest.assigned_engineer == user.id)
    else:
        scope = scope.where(or_(func.lower(InstallationRequest.source) != "callcenter", InstallationRequest.assigned_engineer.is_not(None)))
        if is_service_desk_user(user):
            scope = scope.where(InstallationRequest.assigned_service_user_id == user.id)
    stages = stage_counts({s: n for s, n in db.execute(scope).all()})
    return InstallationSummary(total_pending=total, gt7days=gt7, gt15days=gt15, gt30days=gt30, stages=stages)


#: Every stage the installation payment chain can sit in, in chain order -- fixed list so a
#: stage with nothing pending still shows as a zero card instead of vanishing.
_INSTALLATION_PAYMENT_STAGE_ORDER = [
    ("service_role", "Service Role"),
    ("service_manager", "Service Manager"),
    ("sub_admin", "Sub Admin"),
    ("accounts", "Accounts"),
    ("audit", "Audit"),
    ("admin", "Admin"),
]


@router.get("/installation-payment-stages", response_model=list[InstallationPaymentStageOut])
def installation_payment_stages_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """One card per stage of the installation payment chain -- not just the viewer's own queue,
    so Accounts (or Audit) can see urgency building up everywhere, not only what's already
    reached them. Restricted to roles with a real stake in this chain."""
    role = canonical_role_key(user.role)
    if not (is_operations_admin(user) or role in {"accounts", "audit"}):
        return []
    rows = db.execute(
        select(
            InstallationRequest.payment_approval_stage,
            func.count(InstallationRequest.id),
            func.coalesce(func.sum(InstallationRequest.payment_amount_requested), 0),
        )
        .where(InstallationRequest.status == "Payment Pending")
        .group_by(InstallationRequest.payment_approval_stage)
    ).all()
    by_stage = {stage_key: (count, float(amount)) for stage_key, count, amount in rows}
    return [
        InstallationPaymentStageOut(
            stage_key=key,
            stage_label=label,
            count=by_stage.get(key, (0, 0.0))[0],
            amount=by_stage.get(key, (0, 0.0))[1],
            is_mine=key == role,
        )
        for key, label in _INSTALLATION_PAYMENT_STAGE_ORDER
    ]


#: Service Requests keep the flat Service Role -> [Service Manager] -> Admin chain (no Sub
#: Admin/Accounts/Audit) -- a separate, shorter order from the installation one above.
_SERVICE_PAYMENT_STAGE_ORDER = [
    ("service_role", "Service Role"),
    ("service_manager", "Service Manager"),
    ("admin", "Admin"),
]


@router.get("/service-payment-stages", response_model=list[InstallationPaymentStageOut])
def service_payment_stages_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Same idea as installation-payment-stages, for Service Requests' own (shorter) payment
    chain -- lets Accounts/Audit/Admin see that pipeline's urgency too, not just installations'."""
    role = canonical_role_key(user.role)
    if not (is_operations_admin(user) or role in {"accounts", "audit"}):
        return []
    rows = db.execute(
        select(
            ServicePaymentRequest.approval_stage,
            func.count(ServicePaymentRequest.id),
            func.coalesce(func.sum(ServicePaymentRequest.total_requested_amount), 0),
        )
        .where(ServicePaymentRequest.approval_status == "Pending")
        .group_by(ServicePaymentRequest.approval_stage)
    ).all()
    by_stage = {stage_key: (count, float(amount)) for stage_key, count, amount in rows}
    return [
        InstallationPaymentStageOut(
            stage_key=key,
            stage_label=label,
            count=by_stage.get(key, (0, 0.0))[0],
            amount=by_stage.get(key, (0, 0.0))[1],
            is_mine=key == role,
        )
        for key, label in _SERVICE_PAYMENT_STAGE_ORDER
    ]


def _payment_urgency(days: int) -> str:
    if days >= 7:
        return "urgent"
    if days >= 3:
        return "soon"
    return "ontime"


def _days_waiting(requested_at: datetime | None, now: datetime) -> int:
    if requested_at is None:
        return 0
    # SQLite (local preview) hands back naive datetimes even for timezone=True columns;
    # MySQL (production) doesn't. Strip both sides so the subtraction works either way.
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=timezone.utc)
    return max(0, (now - requested_at).days)


#: Which role sits at which stage of the installation payment chain -- a role not in here never
#: has a stage of its own to act on, so my_payment_queue() returns nothing for it.
_PAYMENT_QUEUE_OWN_STAGE = {
    "service": "service_role",
    "indcool_service": "service_role",
    "service_manager": "service_manager",
    "sub_admin": "sub_admin",
    "accounts": "accounts",
    "audit": "audit",
}


@router.get("/my-payment-queue", response_model=list[PaymentQueueItem])
def my_payment_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Everything sitting at the viewer's own stage of the installation payment chain, with a
    clear next-stop label (Service Manager's own next stop branches on amount, so this is computed
    per row rather than hard-coded) and the same approve/return actions the record's own detail
    page already has. System Admin sees every non-final stage at once, for oversight -- they can
    act on any of it anyway (the admin bypass in installations.update_status)."""
    role = canonical_role_key(user.role)
    own_stage = _PAYMENT_QUEUE_OWN_STAGE.get(role)
    if own_stage is None and not is_system_admin(user):
        return []

    now = datetime.now(timezone.utc)
    stmt = select(InstallationRequest, User.name).outerjoin(User, User.id == InstallationRequest.assigned_engineer).where(
        InstallationRequest.status == "Payment Pending",
    )
    if own_stage is not None:
        stmt = stmt.where(InstallationRequest.payment_approval_stage == own_stage)
    else:
        stmt = stmt.where(InstallationRequest.payment_approval_stage != "admin")
    if is_service_desk_user(user):
        # A bare "service" user can only act once the Service Manager has routed this
        # installation to them specifically -- same narrowing _load_visible() enforces on the
        # actual approve/return call, so this list never shows something they'd then fail to act on.
        stmt = stmt.where(InstallationRequest.assigned_service_user_id == user.id)

    items: list[PaymentQueueItem] = []
    for inst, engineer_name in db.execute(stmt).all():
        amount = float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None
        stages = installation_payment_approval_stages(amount)
        idx = stage_index(inst.payment_approval_stage, stages)
        next_label = stages[idx + 1].label if idx + 1 < len(stages) else None
        requested_at = inst.payment_requested_at
        days = _days_waiting(requested_at, now)
        items.append(PaymentQueueItem(
            entity_id=inst.id,
            label=f"#{inst.id}",
            customer_name=inst.customer_name,
            engineer_name=engineer_name,
            amount=amount or 0.0,
            payment_type=inst.payment_type_requested,
            requested_at=requested_at,
            days_waiting=days,
            urgency=_payment_urgency(days),
            stage_key=inst.payment_approval_stage or "",
            stage_label=stages[idx].label if idx < len(stages) else (inst.payment_approval_stage_label or ""),
            next_stage_label=next_label,
            href=f"/installations/{inst.id}",
        ))
    items.sort(key=lambda i: -i.days_waiting)
    return items


@router.get("/ready-to-pay", response_model=list[ReadyToPayItem])
def ready_to_pay(
    search: str | None = None,
    engineer: str | None = None,
    vendor: str | None = None,
    module: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Everything that's cleared Audit and is sitting at the Admin stage, across both Installations
    and Service Requests -- purely a finding/prioritizing view (age since the request was first
    raised flags urgency); actually paying still happens on that record's own detail page.
    System Admin only -- the "admin" stage itself is already gated to is_system_admin
    (user_can_approve_stage), and nobody else is the one actually releasing this money, Accounts
    and Sub Admin included."""
    if not is_system_admin(user):
        return []

    now = datetime.now(timezone.utc)
    items: list[ReadyToPayItem] = []

    if module in (None, "", "installation"):
        rows = db.execute(
            select(InstallationRequest, User.name)
            .outerjoin(User, User.id == InstallationRequest.assigned_engineer)
            .where(
                InstallationRequest.status == "Payment Pending",
                InstallationRequest.payment_approval_stage == "admin",
            )
        ).all()
        for inst, engineer_name in rows:
            requested_at = inst.payment_requested_at
            days = _days_waiting(requested_at, now)
            items.append(ReadyToPayItem(
                module="installation",
                entity_id=inst.id,
                label=f"#{inst.id}",
                payee_name=engineer_name,
                payee_type="Engineer" if engineer_name else None,
                requested_at=requested_at,
                amount=float(inst.payment_amount_requested or 0),
                days_waiting=days,
                urgency=_payment_urgency(days),
                href=f"/installations/{inst.id}",
            ))

    if module in (None, "", "service"):
        from app.models.vendor import Vendor as VendorModel

        rows = db.execute(
            select(ServicePaymentRequest, ServiceRequest.request_no, User.name, VendorModel.name_of_firm)
            .join(ServiceRequest, ServiceRequest.id == ServicePaymentRequest.service_request_id)
            .outerjoin(User, User.id == ServicePaymentRequest.requested_by_user_id)
            .outerjoin(VendorModel, VendorModel.id == ServicePaymentRequest.requested_by_vendor_id)
            .where(
                ServicePaymentRequest.approval_status == "Pending",
                ServicePaymentRequest.approval_stage == "admin",
            )
        ).all()
        for payment, request_no, engineer_name, vendor_name in rows:
            requested_at = payment.created_at
            days = _days_waiting(requested_at, now)
            is_vendor = payment.requested_by_type == "vendor"
            items.append(ReadyToPayItem(
                module="service",
                entity_id=payment.service_request_id,
                label=request_no or f"#{payment.service_request_id}",
                payee_name=vendor_name if is_vendor else engineer_name,
                payee_type="Vendor" if is_vendor else ("Engineer" if engineer_name else None),
                requested_at=requested_at,
                amount=float(payment.total_requested_amount or 0),
                days_waiting=days,
                urgency=_payment_urgency(days),
                href=f"/services/{payment.service_request_id}",
            ))

    if search:
        needle = search.strip().lower()
        items = [i for i in items if needle in i.label.lower() or (i.payee_name and needle in i.payee_name.lower())]
    if engineer:
        needle = engineer.strip().lower()
        items = [i for i in items if i.payee_type == "Engineer" and i.payee_name and needle in i.payee_name.lower()]
    if vendor:
        needle = vendor.strip().lower()
        items = [i for i in items if i.payee_type == "Vendor" and i.payee_name and needle in i.payee_name.lower()]

    items.sort(key=lambda i: -i.days_waiting)
    return items


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
    role = canonical_role_key(user.role)
    if role == "engineer":
        base = base.where(engineer_visible_service_filter(user.id))
    elif role == "vendor":
        vendor = db.scalar(select(Vendor).where(Vendor.email == user.email))
        if vendor is None:
            return ServiceSummary(new_requests=0, unassigned=0, assigned=0, pending_observation=0, pending_approval=0, completion_pending_approval=0, approved=0, in_progress=0, payment_pending=0, completed=0, closed=0)
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
        completion_pending_approval=cnt("Completion Pending Approval"),
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
