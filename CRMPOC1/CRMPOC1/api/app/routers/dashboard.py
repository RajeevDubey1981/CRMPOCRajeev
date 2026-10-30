import json
from datetime import date, datetime, timedelta, timezone

from app.services.role_access import role_key as canonical_role_key
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.account_ledger import AccountLedgerEntry
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.order import Order
from app.models.payment import PaymentTransaction
from app.models.payment_approval import PaymentApprovalLog
from app.models.service import ServicePaymentRequest, ServiceRequest, ServiceRequestUnit
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.dashboard import (
    BulkPayResult,
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
from app.services.file_service import save_upload
from app.services.installation_stages import stage_counts
from app.services.installation_workflow import log_installation_action
from app.services.workflow_notifications import notify_payment_credited
from app.services.payment_approval_workflow import installation_payment_approval_stages, payment_approval_stages, stage_index
from app.services.role_access import is_operations_admin, is_system_admin
from app.services.service_access import is_service_desk_user
from app.services.service_unit_workflow import sync_aggregate_service_status
from app.services.permissions import can_act_on, sub_module_scope

# Reused from their own routers rather than re-implemented, so a pooled payment finalizes an
# installation or a service exactly the same way a single one already does (bank-details check,
# UTR requirement, the per-row PaymentTransaction/order-completion bookkeeping included).
from app.routers.installations import _apply_payment_transition, _create_payment_transaction, _sync_order_completion_state
from app.routers.services import _log_status as _log_service_status

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


def _last_action_map(db: Session, module: str, entity_ids: list[int]) -> dict[int, str]:
    """The most recent approve/return decision per entity, in that module's payment_approval_logs
    rows -- "Forwarded by <name>" or "Returned by <name>". Empty for anything still at its very
    first stage, since raising a payment request isn't itself an approval decision."""
    if not entity_ids:
        return {}
    rows = db.execute(
        select(PaymentApprovalLog, User.name)
        .outerjoin(User, User.id == PaymentApprovalLog.approved_by_user_id)
        .where(PaymentApprovalLog.module == module, PaymentApprovalLog.entity_id.in_(entity_ids))
        .order_by(PaymentApprovalLog.entity_id, PaymentApprovalLog.created_at.desc())
    ).all()
    latest: dict[int, str] = {}
    for log, approver_name in rows:
        if log.entity_id in latest:
            continue  # already have this entity's most recent row (rows arrive newest-first per entity)
        who = approver_name or log.approver_role or "someone"
        latest[log.entity_id] = f"Returned by {who}" if log.decision == "Rejected" else f"Forwarded by {who}"
    return latest


@router.get("/my-payment-queue", response_model=list[PaymentQueueItem])
def my_payment_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Everything sitting at the viewer's own stage of the installation and service payment
    chains, with a clear next-stop label (Service Manager's own next stop on an installation
    branches on amount, so this is computed per row rather than hard-coded), who last forwarded or
    returned it (if anyone has yet), and the same approve/return actions the record's own detail
    page already has -- installations act inline here; services open to their own detail page,
    since a service can carry several serials each with their own payment request needing that
    page's per-serial context. System Admin sees every non-final stage at once, for oversight --
    they can act on any of it anyway (the admin bypass both modules' approval endpoints give it)."""
    role = canonical_role_key(user.role)
    own_stage = _PAYMENT_QUEUE_OWN_STAGE.get(role)
    if own_stage is None and not is_system_admin(user):
        return []

    now = datetime.now(timezone.utc)
    items: list[PaymentQueueItem] = []

    inst_stmt = select(InstallationRequest, User.name).outerjoin(User, User.id == InstallationRequest.assigned_engineer).where(
        InstallationRequest.status == "Payment Pending",
    )
    if own_stage is not None:
        inst_stmt = inst_stmt.where(InstallationRequest.payment_approval_stage == own_stage)
    else:
        inst_stmt = inst_stmt.where(InstallationRequest.payment_approval_stage != "admin")
    if is_service_desk_user(user):
        # A bare "service" user can only act once the Service Manager has routed this
        # installation to them specifically -- same narrowing _load_visible() enforces on the
        # actual approve/return call, so this list never shows something they'd then fail to act on.
        inst_stmt = inst_stmt.where(InstallationRequest.assigned_service_user_id == user.id)

    inst_rows = db.execute(inst_stmt).all()
    inst_last_action = _last_action_map(db, "installations", [inst.id for inst, _ in inst_rows])
    for inst, engineer_name in inst_rows:
        amount = float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None
        stages = installation_payment_approval_stages(amount)
        idx = stage_index(inst.payment_approval_stage, stages)
        next_label = stages[idx + 1].label if idx + 1 < len(stages) else None
        requested_at = inst.payment_requested_at
        days = _days_waiting(requested_at, now)
        items.append(PaymentQueueItem(
            module="installation",
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
            last_action=inst_last_action.get(inst.id),
            href=f"/installations/{inst.id}",
            actionable=True,
        ))

    # Service Requests only ever reach service_role/service_manager (no Sub Admin/Accounts/Audit
    # stage exists for them), so this is a no-op for those three roles' own stage.
    if own_stage in (None, "service_role", "service_manager"):
        svc_stmt = (
            select(ServicePaymentRequest, ServiceRequest.request_no, User.name)
            .join(ServiceRequest, ServiceRequest.id == ServicePaymentRequest.service_request_id)
            .outerjoin(User, User.id == ServicePaymentRequest.requested_by_user_id)
            .where(ServicePaymentRequest.approval_status == "Pending")
        )
        if own_stage is not None:
            svc_stmt = svc_stmt.where(ServicePaymentRequest.approval_stage == own_stage)
        else:
            svc_stmt = svc_stmt.where(ServicePaymentRequest.approval_stage != "admin")
        svc_rows = db.execute(svc_stmt).all()
        svc_last_action = _last_action_map(db, "services", [p.service_request_id for p, _, _ in svc_rows])
        unit_counts: dict[int, int] = {}
        if svc_rows:
            for sr_id, n in db.execute(
                select(ServiceRequestUnit.service_request_id, func.count())
                .where(ServiceRequestUnit.service_request_id.in_({p.service_request_id for p, _, _ in svc_rows}))
                .group_by(ServiceRequestUnit.service_request_id)
            ).all():
                unit_counts[sr_id] = n
        flat_stages = payment_approval_stages()
        for payment, request_no, engineer_name in svc_rows:
            idx = stage_index(payment.approval_stage, flat_stages)
            next_label = flat_stages[idx + 1].label if idx + 1 < len(flat_stages) else None
            requested_at = payment.created_at
            days = _days_waiting(requested_at, now)
            items.append(PaymentQueueItem(
                module="service",
                entity_id=payment.service_request_id,
                label=request_no or f"#{payment.service_request_id}",
                engineer_name=engineer_name,
                amount=float(payment.total_requested_amount or 0),
                payment_type=payment.payment_type,
                requested_at=requested_at,
                days_waiting=days,
                urgency=_payment_urgency(days),
                stage_key=payment.approval_stage or "",
                stage_label=flat_stages[idx].label if idx < len(flat_stages) else (payment.approval_stage_label or ""),
                next_stage_label=next_label,
                last_action=svc_last_action.get(payment.service_request_id),
                href=f"/services/{payment.service_request_id}",
                actionable=unit_counts.get(payment.service_request_id, 0) <= 1,
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
                payee_id=inst.assigned_engineer,
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
                payee_id=payment.requested_by_vendor_id if is_vendor else payment.requested_by_user_id,
                payment_request_id=payment.id,
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


@router.post("/ready-to-pay/bulk-pay", response_model=BulkPayResult)
async def bulk_pay_ready_to_pay(
    background_tasks: BackgroundTasks,
    refs: str = Form(...),  # JSON list of {"module": "installation"|"service", "entity_id": int, "payment_request_id": int|null}
    payment_type: str = Form(...),
    payment_reference: str = Form(...),
    payment_paid_on: str = Form(...),
    proof_document: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One bank transfer covering several Ready to Pay items for the same engineer or vendor --
    the amount shown is the pool (what was actually transferred); each item is still recorded paid
    for its own original amount, all sharing the one reference, date and (optional) proof. Every
    item must already be sitting at the Admin stage (i.e. actually be a Ready to Pay row) -- this
    never lets a payment skip Accounts/Audit, it only lets Admin settle several already-cleared
    ones in one go."""
    if not is_system_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin can release a pooled payment")

    try:
        parsed_refs = json.loads(refs)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid selection")
    if not isinstance(parsed_refs, list) or not parsed_refs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing selected")
    if payment_type not in ("Cash", "UPI"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")
    normalized_reference = payment_reference.strip()
    if not normalized_reference:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment reference / UTR is required")
    try:
        paid_on_date = date.fromisoformat(payment_paid_on)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Paid on date must be a valid date")

    installation_rows: list[InstallationRequest] = []
    service_items: list[tuple[ServicePaymentRequest, ServiceRequest]] = []
    payee_keys: set[tuple[str, int]] = set()

    for ref in parsed_refs:
        module = ref.get("module") if isinstance(ref, dict) else None
        entity_id = ref.get("entity_id") if isinstance(ref, dict) else None
        if module == "installation":
            inst = db.get(InstallationRequest, entity_id)
            if inst is None or inst.status != "Payment Pending" or inst.payment_approval_stage != "admin":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Installation #{entity_id} is not ready to pay")
            if not inst.assigned_engineer:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Installation #{entity_id} has no engineer to pay")
            installation_rows.append(inst)
            payee_keys.add(("engineer", inst.assigned_engineer))
        elif module == "service":
            payment_request_id = ref.get("payment_request_id")
            payment = db.get(ServicePaymentRequest, payment_request_id) if payment_request_id else None
            if payment is None or payment.service_request_id != entity_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Service payment for #{entity_id} not found")
            if payment.approval_status != "Pending" or payment.approval_stage != "admin":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Service #{entity_id} is not ready to pay")
            service = db.get(ServiceRequest, entity_id)
            if service is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Service #{entity_id} not found")
            is_vendor = payment.requested_by_type == "vendor"
            payee_id = payment.requested_by_vendor_id if is_vendor else payment.requested_by_user_id
            if not payee_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Service #{entity_id} has no engineer or vendor to pay")
            service_items.append((payment, service))
            payee_keys.add(("vendor" if is_vendor else "engineer", payee_id))
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid selection")

    if len(payee_keys) > 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "All selected payments must be for the same engineer or vendor")
    payee_type, payee_id = next(iter(payee_keys))

    if payee_type == "engineer":
        engineer = db.get(User, payee_id)
        if engineer is None or not (engineer.bank_account_number or "").strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "This engineer has no bank account details on file. Add them (Users -> Edit) before paying.",
            )

    if payment_type == "UPI" and not (proof_document is not None and proof_document.filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload Payment Proof / Document is required when payment type is UPI")

    proof_path = None
    if proof_document is not None and proof_document.filename:
        proof_path = await save_upload(proof_document, module="payments")

    now = datetime.now(timezone.utc)
    paid_count = 0
    total_amount = 0.0

    for inst in installation_rows:
        amount = float(inst.payment_amount_requested or 0)
        old_status = inst.status
        inst.status = _apply_payment_transition(
            db,
            inst,
            requested_status="Completed",
            actor=user,
            installation_date=None,
            payment_amount=None,
            payment_type=payment_type,
            payment_reference=normalized_reference,
            payment_paid_on=payment_paid_on,
        )
        log_installation_action(
            db,
            inst,
            action="Payment Approved (pooled)",
            user=user,
            old_status=old_status,
            new_status=inst.status,
            remarks=f"Part of a pooled payment of {len(parsed_refs)} request(s), ref {normalized_reference}",
        )
        if proof_path:
            inst.payment_proof_file_path = proof_path
        _sync_order_completion_state(db, inst)
        paid_count += 1
        total_amount += amount

    if installation_rows:
        _create_payment_transaction(db, rows=installation_rows, actor=user, payment_type=payment_type)
        engineer = db.get(User, payee_id)  # payee_type is always "engineer" for installations
        if engineer is not None:
            for inst in installation_rows:
                notify_payment_credited(
                    background_tasks,
                    payee_email=engineer.email,
                    payee_name=engineer.name,
                    module="installation",
                    label=f"#{inst.id}",
                    amount=float(inst.payment_amount_paid or inst.payment_amount_requested or 0),
                    payment_type=payment_type,
                    payment_reference=normalized_reference,
                    payment_paid_on=paid_on_date,
                )

    service_transaction_amount = 0.0
    for payment, service in service_items:
        amount = float(payment.total_requested_amount or 0)
        old_status = service.status
        payment.status = "Processed"
        payment.approval_status = "Approved"
        payment.approval_stage = "admin"
        payment.approval_stage_label = "Completed"
        payment.next_approver_role = None
        payment.approved_amount = amount
        payment.payment_type = payment_type
        payment.payment_reference = normalized_reference
        payment.payment_paid_on = paid_on_date
        payment.processed_at = now
        payment.processed_by_user_id = user.id
        payment.updated_at = now
        if proof_path:
            payment.payment_proof_file_path = proof_path
        if payment.service_request_unit_id:
            unit = db.get(ServiceRequestUnit, payment.service_request_unit_id)
            if unit is not None:
                unit.unit_status = "Payment Completed"
            sync_aggregate_service_status(db, service)
        else:
            service.status = "Payment Completed"
            service.status_date = now
        _log_service_status(
            db,
            service,
            action="Payment Approved (pooled)",
            user=user,
            old_status=old_status,
            new_status=service.status,
            remarks=f"Part of a pooled payment of {len(parsed_refs)} request(s), ref {normalized_reference}",
            metadata={"payment_request_id": payment.id},
        )
        paid_count += 1
        total_amount += amount
        service_transaction_amount += amount

    if service_items:
        transaction = PaymentTransaction(
            payment_type=payment_type,
            total_amount=service_transaction_amount,
            request_count=len(service_items),
            recorded_by_user_id=user.id,
            engineer_user_id=payee_id if payee_type == "engineer" else None,
        )
        db.add(transaction)
        db.flush()
        for payment, _service in service_items:
            payment.payment_transaction_id = transaction.id
        today = now.date()
        for entry_type in ("credit", "debit"):
            db.add(AccountLedgerEntry(
                party_type=payee_type,
                party_id=payee_id,
                entry_type=entry_type,
                amount=service_transaction_amount,
                description=f"Pooled service payout ({len(service_items)} request(s))",
                source_type="job_payout",
                source_id=transaction.id,
                entry_date=today,
                created_by_user_id=None,
            ))

        if payee_type == "engineer":
            payee = db.get(User, payee_id)
            payee_email, payee_name = (payee.email, payee.name) if payee else (None, None)
        else:
            payee = db.get(Vendor, payee_id)
            payee_email, payee_name = (payee.email, payee.name_of_firm) if payee else (None, None)
        if payee_email:
            for payment, service in service_items:
                notify_payment_credited(
                    background_tasks,
                    payee_email=payee_email,
                    payee_name=payee_name,
                    module="service",
                    label=service.request_no or f"#{service.id}",
                    amount=float(payment.approved_amount or 0),
                    payment_type=payment_type,
                    payment_reference=normalized_reference,
                    payment_paid_on=paid_on_date,
                )

    db.commit()
    return BulkPayResult(paid=paid_count, total_amount=total_amount)


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
