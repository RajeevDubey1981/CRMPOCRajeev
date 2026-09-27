from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.installation import InstallationRequest
from app.models.complaint import Complaint
from app.models.order import Order, OrderItem
from app.models.payment import PaymentTransaction
from app.models.service import ServicePaymentRequest, ServiceRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.installation import (
    BulkAssignRequest,
    BulkCancelRequest,
    InstallationEngineerAssignmentOption,
    InstallationCreate,
    InstallationBulkUpdateRequest,
    InstallationListItem,
    InstallationListResponse,
    InstallationOut,
    InstallationPaymentHistoryGroupItem,
    InstallationPaymentHistoryResponse,
    InstallationPaymentHistoryRequestItem,
    InstallationStatusUpdate,
    AdminInstallationPaymentUpdate,
)
from app.services.engineer_assignment import get_engineer_assignment_options
from app.services.file_service import read_upload_bytes, save_upload, to_public_upload_path
from app.services.role_access import is_operations_admin, is_system_admin
from app.services.installation_workflow import (
    callcenter_can_assign_engineer,
    document_upload_url,
    is_callcenter_source,
    is_vendor_assigned_engineer_workflow,
    log_installation_action,
    prepare_vendor_installation_for_engineer_workflow,
    resolve_order_context,
    return_installation_to_engineer_for_rework,
    supports_engineer_installation_workflow,
    sync_callcenter_order_item_on_completion,
)
from app.services.permissions import can_act_on
from app.services.serial_history import EVENT_TYPES, create_serial_history_event
from app.services.workflow_notifications import (
    notify_customer_installation_update,
    notify_engineer_installation_assigned,
)

router = APIRouter(prefix="/api/installations", tags=["installations"])

STATUSES = [
    "Pending", "Document Requested", "Admin Review Document", "Order Verified",
    "Submitted", "Assigned", "In Progress", "Serial Pending Verification",
    "Completion Pending Approval", "Installation Completed", "Payment Pending", "Completed", "Settlement Pending", "Settlement Approved",
    "Returned", "Rejected",
]

PAYMENT_TYPES = {"Cash", "UPI"}
PENDING_ASSIGNMENT_STATUSES = ("Assigned", "In Progress", "Payment Pending", "Settlement Pending")
SUCCESS_ASSIGNMENT_STATUSES = ("Completed", "Settlement Approved")
UNSUCCESS_ASSIGNMENT_STATUSES = ("Returned", "Rejected")


def _split_total_amount(total_amount: str, count: int) -> list[Decimal]:
    if count < 1:
        return []
    total_cents = int((Decimal(total_amount) * Decimal("100")).quantize(Decimal("1")))
    base_cents = total_cents // count
    remainder = total_cents % count
    return [
        Decimal(base_cents + (1 if idx < remainder else 0)) / Decimal("100")
        for idx in range(count)
    ]


def _payment_qr_view_url(inst: InstallationRequest) -> str | None:
    if inst.payment_qr_code_blob:
        return f"/api/installations/{inst.id}/payment-qr"
    return to_public_upload_path(inst.payment_qr_code_path)


def _validate_installation_request_allowed(db: Session, order_item_id: int | None) -> OrderItem:
    if order_item_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Installation request must be linked to an order item",
        )
    item = db.get(OrderItem, order_item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
    order = db.get(Order, item.order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.status != "Delivered":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Installation request can be raised only after the order is Delivered",
        )
    if not (order.oem_bill_no or "").strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Installation request can be raised only after OEM Bill No is submitted",
        )
    return item


def _resolve_order_vendor(db: Session, inst: InstallationRequest) -> tuple[str | None, str | None]:
    """Resolve (order_no, vendor_name) for an InstallationRequest."""
    order_no, order_id = resolve_order_context(db, inst)
    if not order_id:
        return None, None
    order = db.get(Order, order_id)
    if order is None:
        return order_no, None
    vendor_name = None
    if order.vendor_id:
        v = db.get(Vendor, order.vendor_id)
        vendor_name = v.name_of_firm if v else None
    return order.order_no or order_no, vendor_name


def _complaint_map_for_order_items(db: Session, order_item_ids: set[int]) -> dict[int, tuple[int, str]]:
    if not order_item_ids:
        return {}
    rows = db.execute(
        select(Complaint.order_item_id, Complaint.id, Complaint.comp_no)
        .where(
            Complaint.order_item_id.in_(order_item_ids),
            Complaint.deleted_at.is_(None),
        )
        .order_by(desc(Complaint.created_at))
    ).all()
    mapped: dict[int, tuple[int, str]] = {}
    for row in rows:
        if row.order_item_id and row.order_item_id not in mapped:
            mapped[row.order_item_id] = (row.id, row.comp_no)
    return mapped


def _list_row(
    db: Session,
    inst: InstallationRequest,
    order_map: dict[int, Order],
    order_item_map: dict[int, OrderItem],
    vendor_map: dict[int, str],
    complaint_map: dict[int, tuple[int, str]] | None = None,
    orders_by_id: dict[int, Order] | None = None,
) -> InstallationListItem:
    engineer_name = None
    if inst.assigned_engineer:
        u = db.get(User, inst.assigned_engineer)
        engineer_name = u.name if u else None
    approved_by_name = None
    if inst.settlement_approved_by:
        u = db.get(User, inst.settlement_approved_by)
        approved_by_name = u.name if u else None
    payment_recorded_by_name = None
    if inst.payment_recorded_by:
        u = db.get(User, inst.payment_recorded_by)
        payment_recorded_by_name = u.name if u else None
    order_item = order_item_map.get(inst.order_item_id)
    order = order_map.get(inst.order_item_id)
    if order is None and inst.order_id:
        order = (orders_by_id or {}).get(inst.order_id)
    order_no = order.order_no if order else None
    vendor_name = vendor_map.get(order.vendor_id) if order and order.vendor_id else None
    complaint_id = None
    complaint_no = None
    if inst.order_item_id and complaint_map:
        complaint_id, complaint_no = complaint_map.get(inst.order_item_id, (None, None))
    return InstallationListItem(
        id=inst.id,
        source=inst.source or "vendor",
        order_item_id=inst.order_item_id,
        item_code=order_item.item_code if order_item else None,
        customer_name=inst.customer_name,
        contact_number=inst.contact_number,
        product_name=inst.product_name,
        order_no=order_no,
        vendor_name=vendor_name,
        serial_no=inst.serial_no,
        serial_no_2=inst.serial_no_2,
        status=inst.status,
        request_date=inst.request_date,
        installation_date=inst.installation_date,
        assigned_engineer=inst.assigned_engineer,
        assigned_engineer_name=engineer_name,
        settlement_approved_by_name=approved_by_name,
        payment_amount_requested=float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None,
        payment_type_requested=inst.payment_type_requested,
        payment_qr_code_path=_payment_qr_view_url(inst),
        payment_qr_code_filename=inst.payment_qr_code_filename,
        payment_proof_file_path=to_public_upload_path(inst.payment_proof_file_path),
        complaint_id=complaint_id,
        complaint_no=complaint_no,
    )


def _hydrate(db: Session, inst: InstallationRequest) -> dict:
    engineer_name = None
    if inst.assigned_engineer:
        u = db.get(User, inst.assigned_engineer)
        engineer_name = u.name if u else None
    approved_by_name = None
    if inst.settlement_approved_by:
        u = db.get(User, inst.settlement_approved_by)
        approved_by_name = u.name if u else None
    payment_recorded_by_name = None
    if inst.payment_recorded_by:
        u = db.get(User, inst.payment_recorded_by)
        payment_recorded_by_name = u.name if u else None
    order_no, vendor_name = _resolve_order_vendor(db, inst)
    complaint_id = inst.complaint_id
    complaint_no = None
    if complaint_id:
        complaint = db.get(Complaint, complaint_id)
        if complaint is not None:
            complaint_no = complaint.comp_no
    elif inst.order_item_id:
        complaint = db.scalar(
            select(Complaint)
            .where(Complaint.order_item_id == inst.order_item_id, Complaint.deleted_at.is_(None))
            .order_by(desc(Complaint.created_at))
        )
        if complaint is not None:
            complaint_id = complaint.id
            complaint_no = complaint.comp_no
    from app.services.installation_workflow import (
        build_installation_completion_proofs,
        resolve_order_item_serial_count,
    )

    order_item = db.get(OrderItem, inst.order_item_id) if inst.order_item_id else None
    item_code = order_item.item_code if order_item else None
    item_serial_count = resolve_order_item_serial_count(db, order_item)
    completion_proofs = build_installation_completion_proofs(db, inst)
    work_report_file_path_2 = next(
        (proof["file_path"] for proof in completion_proofs if proof["slot"] == 2),
        None,
    )
    return {
        **{k: getattr(inst, k) for k in (
            "id", "source", "customer_name", "contact_number", "customer_email", "address",
            "order_id", "order_item_id", "product_name",
            "serial_no", "serial_no_2",
            "request_date", "assigned_engineer", "status", "installation_date",
            "work_report", "work_report_file_path", "settlement_approved_by",
            "payment_type_requested", "payment_qr_code_path", "payment_qr_code_filename", "payment_proof_file_path", "payment_requested_at",
            "payment_type_paid", "payment_recorded_at", "payment_recorded_by",
            "document_request_sent_at", "order_verified_at",
            "engineer_entered_serial_no", "engineer_entered_serial_no_2", "serial_verified_at",
            "admin_billing_type", "admin_approval_remark", "admin_approved_at",
            "engineer_site_remarks", "engineer_serials_submitted_at",
            "parent_installation_id",
            "created_at", "updated_at",
        )},
        "payment_amount_requested": float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None,
        "payment_amount_paid": float(inst.payment_amount_paid) if inst.payment_amount_paid is not None else None,
        "work_report_file_path": to_public_upload_path(inst.work_report_file_path),
        "work_report_file_path_2": work_report_file_path_2,
        "item_serial_count": item_serial_count,
        "completion_proofs": completion_proofs,
        "payment_qr_code_path": _payment_qr_view_url(inst),
        "payment_qr_code_filename": inst.payment_qr_code_filename,
        "payment_proof_file_path": to_public_upload_path(inst.payment_proof_file_path),
        "order_no": order_no,
        "vendor_name": vendor_name,
        "assigned_engineer_name": engineer_name,
        "settlement_approved_by_name": approved_by_name,
        "payment_recorded_by_name": payment_recorded_by_name,
        "complaint_id": complaint_id,
        "complaint_no": complaint_no,
        "item_code": item_code,
        "document_upload_url": document_upload_url(inst),
    }


def _apply_payment_transition(
    inst: InstallationRequest,
    *,
    requested_status: str,
    actor: User,
    installation_date: str | None,
    payment_amount: str | None = None,
    payment_type: str | None = None,
    payment_qr_code_path: str | None = None,
    payment_qr_code_blob: bytes | None = None,
    payment_qr_code_filename: str | None = None,
    payment_qr_code_content_type: str | None = None,
    payment_qr_code_size_bytes: int | None = None,
) -> str:
    normalized_payment_type = (payment_type or "").strip() or None
    if normalized_payment_type is not None and normalized_payment_type not in PAYMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")

    if requested_status == "Completed" and actor.role == "engineer":
        if not installation_date:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation date is required when status is Completed")
        if payment_amount in (None, ""):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Amount is required when status is Completed")
        try:
            requested_amount = float(payment_amount)
        except (TypeError, ValueError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Amount must be a valid number")
        if requested_amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Amount cannot be negative")
        if normalized_payment_type is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Type is required when status is Completed")
        if normalized_payment_type == "UPI" and not payment_qr_code_blob and not inst.payment_qr_code_blob and not inst.payment_qr_code_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required when payment type is UPI")

        inst.payment_amount_requested = requested_amount
        inst.payment_type_requested = normalized_payment_type
        if payment_qr_code_blob:
            inst.payment_qr_code_blob = payment_qr_code_blob
            inst.payment_qr_code_filename = payment_qr_code_filename
            inst.payment_qr_code_content_type = payment_qr_code_content_type
            inst.payment_qr_code_size_bytes = payment_qr_code_size_bytes
            inst.payment_qr_code_path = None
        inst.payment_requested_at = datetime.now(timezone.utc)
        return "Payment Pending"

    if requested_status == "Completed" and is_operations_admin(actor) and inst.status == "Payment Pending":
        if payment_amount in (None, "") and inst.payment_amount_requested is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Amount is required to complete payment")
        effective_amount = float(payment_amount) if payment_amount not in (None, "") else float(inst.payment_amount_requested)
        effective_type = normalized_payment_type or inst.payment_type_requested
        if effective_type is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment Type is required to complete payment")
        if effective_type == "UPI" and not payment_qr_code_blob and not inst.payment_qr_code_blob and not inst.payment_qr_code_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required when payment type is UPI")

        inst.payment_amount_requested = effective_amount
        inst.payment_amount_paid = effective_amount
        inst.payment_type_requested = effective_type
        inst.payment_type_paid = effective_type
        if payment_qr_code_blob:
            inst.payment_qr_code_blob = payment_qr_code_blob
            inst.payment_qr_code_filename = payment_qr_code_filename
            inst.payment_qr_code_content_type = payment_qr_code_content_type
            inst.payment_qr_code_size_bytes = payment_qr_code_size_bytes
            inst.payment_qr_code_path = None
        inst.payment_recorded_at = datetime.now(timezone.utc)
        inst.payment_recorded_by = actor.id
        return "Completed"

    return requested_status


def _create_payment_transaction(
    db: Session,
    *,
    rows: list[InstallationRequest],
    actor: User,
    payment_type: str,
) -> PaymentTransaction:
    total_amount = sum(float(row.payment_amount_paid or row.payment_amount_requested or 0) for row in rows)
    engineer_ids = {row.assigned_engineer for row in rows if row.assigned_engineer}
    transaction = PaymentTransaction(
        payment_type=payment_type,
        total_amount=total_amount,
        request_count=len(rows),
        recorded_by_user_id=actor.id,
        engineer_user_id=next(iter(engineer_ids)) if len(engineer_ids) == 1 else None,
    )
    db.add(transaction)
    db.flush()
    for row in rows:
        row.payment_transaction_id = transaction.id
    return transaction


def _sync_order_completion_state(db: Session, inst: InstallationRequest) -> None:
    sync_callcenter_order_item_on_completion(db, inst)
    if not inst.order_item_id or inst.status != "Completed":
        return
    item = db.get(OrderItem, inst.order_item_id)
    if item is None:
        return
    item.installation_status = "Completed"
    order = db.get(Order, item.order_id)
    if order is None:
        return
    remaining = db.scalar(
        select(func.count())
        .select_from(OrderItem)
        .where(
            OrderItem.order_id == order.id,
            OrderItem.installation_status != "Completed",
        )
    ) or 0
    if remaining == 0:
        order.status = "Completed"


@router.get("", response_model=InstallationListResponse)
def list_installations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    order_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "installations", "can_view", None):
        return InstallationListResponse(items=[], total=0, page=page, per_page=per_page)

    stmt = select(InstallationRequest)

    # Call-center requests stay on the complaint workflow until an engineer is assigned.
    if user.role != "engineer":
        stmt = stmt.where(
            or_(
                func.lower(InstallationRequest.source) != "callcenter",
                InstallationRequest.assigned_engineer.is_not(None),
            )
        )

    # Engineers only ever see installation requests assigned to them.
    if user.role == "engineer":
        stmt = stmt.where(InstallationRequest.assigned_engineer == user.id)

    if order_id is not None:
        item_ids_subq = select(OrderItem.id).where(OrderItem.order_id == order_id)
        stmt = stmt.where(
            (InstallationRequest.order_id == order_id)
            | InstallationRequest.order_item_id.in_(item_ids_subq)
        )
    if status_filter and status_filter in STATUSES:
        stmt = stmt.where(InstallationRequest.status == status_filter)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            InstallationRequest.customer_name.ilike(like) |
            InstallationRequest.contact_number.ilike(like) |
            InstallationRequest.product_name.ilike(like)
        )
    if date_from:
        stmt = stmt.where(InstallationRequest.request_date >= date_from)
    if date_to:
        stmt = stmt.where(InstallationRequest.request_date <= date_to)

    stmt = stmt.order_by(desc(InstallationRequest.request_date))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    # Batch-resolve order/vendor lookups for the page (avoid N+1)
    order_item_ids = {r.order_item_id for r in rows if r.order_item_id}
    direct_order_ids = {r.order_id for r in rows if r.order_id}
    order_map: dict[int, Order] = {}
    order_item_map: dict[int, OrderItem] = {}
    orders_by_id: dict[int, Order] = {}
    if order_item_ids:
        items = db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))).all()
        order_item_map = {item.id: item for item in items}
        order_ids = {i.order_id for i in items}
        orders_by_id = {
            o.id: o for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
        } if order_ids else {}
        for i in items:
            order_map[i.id] = orders_by_id.get(i.order_id)
    if direct_order_ids:
        for order in db.scalars(select(Order).where(Order.id.in_(direct_order_ids))).all():
            orders_by_id[order.id] = order

    vendor_ids = {o.vendor_id for o in list(order_map.values()) + list(orders_by_id.values()) if o and o.vendor_id}
    vendor_map: dict[int, str] = {}
    if vendor_ids:
        for v in db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids))).all():
            vendor_map[v.id] = v.name_of_firm

    complaint_map = _complaint_map_for_order_items(db, order_item_ids)

    return InstallationListResponse(
        items=[_list_row(db, inst, order_map, order_item_map, vendor_map, complaint_map, orders_by_id) for inst in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/payment-history", response_model=InstallationPaymentHistoryResponse)
def payment_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: str | None = None,
    engineer: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_system_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view payment history")

    if search:
        like = f"%{search.strip()}%"
        installation_txn_ids = set(db.scalars(
            select(InstallationRequest.payment_transaction_id)
            .where(
                InstallationRequest.payment_transaction_id.is_not(None),
                InstallationRequest.customer_name.ilike(like) |
                InstallationRequest.product_name.ilike(like) |
                InstallationRequest.serial_no.ilike(like),
            )
        ).all())
        service_txn_ids = set(db.scalars(
            select(ServicePaymentRequest.payment_transaction_id)
            .join(ServiceRequest, ServiceRequest.id == ServicePaymentRequest.service_request_id)
            .where(
                ServicePaymentRequest.payment_transaction_id.is_not(None),
                ServiceRequest.customer_name.ilike(like) |
                ServiceRequest.model_details.ilike(like) |
                ServiceRequest.serial_no.ilike(like) |
                ServiceRequest.request_no.ilike(like),
            )
        ).all())
        txn_ids = installation_txn_ids | service_txn_ids
        stmt = select(PaymentTransaction).where(PaymentTransaction.id.in_(txn_ids or {-1}))
    else:
        stmt = select(PaymentTransaction)
    if engineer and engineer.strip():
        engineer_like = f"%{engineer.strip()}%"
        stmt = (
            stmt
            .join(User, PaymentTransaction.engineer_user_id == User.id)
            .where(User.name.ilike(engineer_like) | User.email.ilike(engineer_like))
        )
    stmt = stmt.order_by(desc(PaymentTransaction.recorded_at))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    transaction_ids = [row.id for row in rows]
    linked_installations = db.scalars(
        select(InstallationRequest).where(InstallationRequest.payment_transaction_id.in_(transaction_ids))
    ).all() if transaction_ids else []
    linked_services = db.scalars(
        select(ServicePaymentRequest).where(ServicePaymentRequest.payment_transaction_id.in_(transaction_ids))
    ).all() if transaction_ids else []

    order_item_ids = {r.order_item_id for r in linked_installations if r.order_item_id}
    order_item_map: dict[int, OrderItem] = {}
    order_map: dict[int, Order] = {}
    if order_item_ids:
        items = db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))).all()
        order_item_map = {item.id: item for item in items}
        order_ids = {i.order_id for i in items}
        orders_by_id = {
            o.id: o for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
        } if order_ids else {}
        for item in items:
            order_map[item.id] = orders_by_id.get(item.order_id)

    linked_by_transaction: dict[int, list[InstallationRequest]] = {}
    for installation in linked_installations:
        linked_by_transaction.setdefault(installation.payment_transaction_id, []).append(installation)
    linked_services_by_transaction: dict[int, list[ServicePaymentRequest]] = {}
    service_ids = {row.service_request_id for row in linked_services}
    services_by_id = {row.id: row for row in db.scalars(select(ServiceRequest).where(ServiceRequest.id.in_(service_ids))).all()} if service_ids else {}
    for payment_request in linked_services:
        linked_services_by_transaction.setdefault(payment_request.payment_transaction_id, []).append(payment_request)

    items: list[InstallationPaymentHistoryGroupItem] = []
    for txn in rows:
        recorded_by_name = None
        if txn.recorded_by_user_id:
            recorded_by = db.get(User, txn.recorded_by_user_id)
            recorded_by_name = recorded_by.name if recorded_by else None
        engineer_name = None
        if txn.engineer_user_id:
            engineer = db.get(User, txn.engineer_user_id)
            engineer_name = engineer.name if engineer else None
        request_items: list[InstallationPaymentHistoryRequestItem] = []
        for inst in linked_by_transaction.get(txn.id, []):
            order_item = order_item_map.get(inst.order_item_id)
            order = order_map.get(inst.order_item_id)
            request_items.append(InstallationPaymentHistoryRequestItem(
                id=inst.id,
                source_type="installation",
                order_no=order.order_no if order else None,
                item_code=order_item.item_code if order_item else None,
                customer_name=inst.customer_name,
                installation_date=inst.installation_date,
                requested_amount=float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None,
                paid_amount=float(inst.payment_amount_paid) if inst.payment_amount_paid is not None else None,
                status=inst.status,
            ))
        for payment_request in linked_services_by_transaction.get(txn.id, []):
            service = services_by_id.get(payment_request.service_request_id)
            if service is None:
                continue
            request_items.append(InstallationPaymentHistoryRequestItem(
                id=service.id,
                source_type="service",
                order_no=service.request_no,
                item_code=service.model_details,
                customer_name=service.customer_name,
                installation_date=payment_request.processed_at,
                requested_amount=float(payment_request.total_requested_amount) if payment_request.total_requested_amount is not None else None,
                paid_amount=float(payment_request.approved_amount) if payment_request.approved_amount is not None else None,
                status=service.status,
            ))
        items.append(InstallationPaymentHistoryGroupItem(
            id=txn.id,
            payment_type=txn.payment_type,
            total_amount=float(txn.total_amount),
            request_count=txn.request_count,
            recorded_at=txn.recorded_at,
            recorded_by_name=recorded_by_name,
            engineer_name=engineer_name,
            requests=request_items,
        ))

    return InstallationPaymentHistoryResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/engineer-assignment-options", response_model=list[InstallationEngineerAssignmentOption])
def engineer_assignment_options(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Engineers cannot assign installation requests")
    if not (
        can_act_on(db, user, "installations", "can_view", None)
        or can_act_on(db, user, "services", "can_view", None)
        or can_act_on(db, user, "complaints", "can_view", None)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view engineer assignment options")
    return get_engineer_assignment_options(db)


@router.post("", response_model=InstallationOut, status_code=status.HTTP_201_CREATED)
def create_installation(
    body: InstallationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "installations", "can_create", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create installation requests")

    role = (user.role or "").lower()
    requested_source = (body.source or "").lower()
    callcenter_create = role == "callcenter" or requested_source == "callcenter"

    if callcenter_create:
        order = db.get(Order, body.order_id) if body.order_id else None
        if body.order_id and (order is None or order.deleted_at is not None):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
        inst = InstallationRequest(
            source="callcenter",
            created_by=user.id,
            customer_name=body.customer_name,
            contact_number=body.contact_number,
            customer_email=body.customer_email,
            address=body.address,
            order_id=body.order_id,
            product_name=body.product_name,
            request_date=body.request_date or datetime.now(timezone.utc),
            status="Pending",
        )
        if order is not None:
            inst.customer_name = order.customer_name or inst.customer_name
            inst.contact_number = order.customer_contact or inst.contact_number
            inst.customer_email = order.customer_email or inst.customer_email
            inst.address = order.customer_address or inst.address
        db.add(inst)
        db.flush()
        log_installation_action(
            db,
            inst,
            action="Call Center Request Created",
            user=user,
            new_status=inst.status,
            metadata={"order_id": inst.order_id},
        )
        db.commit()
        db.refresh(inst)
        return InstallationOut(**_hydrate(db, inst))

    _validate_installation_request_allowed(db, body.order_item_id)
    order_item = db.get(OrderItem, body.order_item_id) if body.order_item_id else None

    inst = InstallationRequest(
        source="vendor",
        customer_name=body.customer_name,
        contact_number=body.contact_number,
        customer_email=body.customer_email,
        address=body.address,
        order_id=order_item.order_id if order_item else None,
        order_item_id=body.order_item_id,
        product_name=body.product_name,
        request_date=body.request_date or datetime.now(timezone.utc),
        status="Pending",
        serial_no=order_item.serial_no if order_item else None,
        serial_no_2=order_item.serial_no_2 if order_item else None,
    )
    db.add(inst)
    db.flush()
    if inst.serial_no:
        create_serial_history_event(
            db,
            serial_no=inst.serial_no,
            serial_no_2=inst.serial_no_2,
            order_item_id=inst.order_item_id,
            event_type=EVENT_TYPES["INSTALLATION"],
            event_subtype="REQUEST_CREATED",
            event_at=inst.request_date,
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="installation_requests",
            source_id=inst.id,
            title="Installation request created",
            description=f"Installation request {inst.id} created with status {inst.status}.",
            metadata={"status": inst.status, "product_name": inst.product_name},
        )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate(db, inst))


@router.post("/bulk-assign")
def bulk_assign(
    body: BulkAssignRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Assign (or re-assign) engineers to one or more installation requests in a single call.

    Each pair may target a row by installation_id or order_item_id. Rows not currently in
    Submitted or Assigned status are skipped (not overwritten) rather than failing the batch.
    """
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot assign installation requests")
    if user.role == "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Engineers cannot assign installation requests")

    if not body.assignments:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No assignments provided")

    engineer_ids = {a.engineer_id for a in body.assignments}
    engineers = {
        u.id: u for u in db.scalars(
            select(User).where(User.id.in_(engineer_ids), User.role == "engineer")
        ).all()
    }
    invalid_engineer_ids = sorted(engineer_ids - engineers.keys())
    if invalid_engineer_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid engineer id(s): {invalid_engineer_ids}",
        )

    assigned: list[int] = []
    not_found: list[dict] = []
    skipped_wrong_status: list[dict] = []
    engineer_assignments: dict[int, list[int]] = {}
    engineer_order_nos: dict[int, set[str]] = {}

    for pair in body.assignments:
        if pair.installation_id is not None:
            inst = db.get(InstallationRequest, pair.installation_id)
        elif pair.order_item_id is not None:
            inst = db.scalar(
                select(InstallationRequest).where(InstallationRequest.order_item_id == pair.order_item_id)
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Each assignment must specify installation_id or order_item_id",
            )

        if inst is None:
            not_found.append({"installation_id": pair.installation_id, "order_item_id": pair.order_item_id})
            continue
        assignable_statuses = ("Submitted", "Assigned")
        if is_callcenter_source(inst):
            if not callcenter_can_assign_engineer(inst):
                skipped_wrong_status.append({"installation_id": inst.id, "status": inst.status})
                continue
        elif inst.status not in assignable_statuses:
            skipped_wrong_status.append({"installation_id": inst.id, "status": inst.status})
            continue

        inst.assigned_engineer = pair.engineer_id
        inst.status = "Assigned"
        prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user)
        assigned.append(inst.id)
        engineer_assignments.setdefault(pair.engineer_id, []).append(inst.id)
        if inst.complaint_id:
            complaint = db.get(Complaint, inst.complaint_id)
            if complaint is not None and complaint.assigned_engineer != pair.engineer_id:
                complaint.assigned_engineer = pair.engineer_id
        order_no, _ = resolve_order_context(db, inst)
        if order_no:
            engineer_order_nos.setdefault(pair.engineer_id, set()).add(order_no)
        elif inst.order_item_id:
            item = db.get(OrderItem, inst.order_item_id)
            if item is not None:
                order = db.get(Order, item.order_id)
                if order and order.order_no:
                    engineer_order_nos.setdefault(pair.engineer_id, set()).add(order.order_no)

    db.commit()

    for engineer_id, installation_ids in engineer_assignments.items():
        engineer = engineers.get(engineer_id)
        if engineer is not None:
            notify_engineer_installation_assigned(
                background_tasks,
                engineer=engineer,
                installation_ids=installation_ids,
                order_nos=sorted(engineer_order_nos.get(engineer_id, set())),
            )

    return {
        "assigned": assigned,
        "not_found": not_found,
        "skipped_wrong_status": skipped_wrong_status,
    }


def _cancel_one(db: Session, inst: InstallationRequest) -> None:
    """Revert a single InstallationRequest to its pre-submission state: delete the request
    and unlock its linked OrderItem back to "Not Requested" so the vendor can re-select it.
    Caller must have already validated inst.status is Submitted or Assigned.
    """
    if inst.order_item_id is not None:
        item = db.get(OrderItem, inst.order_item_id)
        if item is not None:
            item.installation_status = "Not Requested"
    db.delete(inst)


@router.post("/bulk-cancel", status_code=status.HTTP_200_OK)
def bulk_cancel(
    body: BulkCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel (revert) multiple installation requests in one call. Each must be in
    Submitted or Assigned status (before work starts); others are skipped, not failed.
    """
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel installation requests")
    if user.role == "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Engineers cannot cancel installation requests")

    if not body.installation_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No installation ids provided")

    cancelled: list[int] = []
    not_found: list[int] = []
    skipped_wrong_status: list[dict] = []

    for inst_id in body.installation_ids:
        inst = db.get(InstallationRequest, inst_id)
        if inst is None:
            not_found.append(inst_id)
            continue
        if inst.status not in ("Submitted", "Assigned"):
            skipped_wrong_status.append({"installation_id": inst.id, "status": inst.status})
            continue
        _cancel_one(db, inst)
        cancelled.append(inst_id)

    db.commit()

    return {
        "cancelled": cancelled,
        "not_found": not_found,
        "skipped_wrong_status": skipped_wrong_status,
    }


@router.post("/{installation_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_submission(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revert a vendor's submission back to its original open state: allowed while status
    is "Submitted" or "Assigned" (i.e. before work has actually started). Deletes the
    InstallationRequest and unlocks the linked OrderItem back to "Not Requested" so the
    vendor can re-select it. Not allowed once work is "In Progress" or later.
    """
    inst = db.get(InstallationRequest, installation_id)
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel installation requests")
    if user.role == "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Engineers cannot cancel installation requests")
    if inst.status not in ("Submitted", "Assigned"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Can only cancel requests still in Submitted or Assigned status (before work starts)",
        )

    _cancel_one(db, inst)
    db.commit()
    return {"message": "Submission cancelled", "installation_id": installation_id}


def _load_visible(db: Session, user: User, inst_id: int) -> InstallationRequest:
    inst = db.get(InstallationRequest, inst_id)
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    if not can_act_on(db, user, "installations", "can_view", None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    if user.role == "engineer" and inst.assigned_engineer != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Installation request not found")
    return inst


@router.get("/{installation_id}", response_model=InstallationOut)
def get_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _load_visible(db, user, installation_id)
    if prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user):
        db.commit()
        db.refresh(inst)
    return InstallationOut(**_hydrate(db, inst))


@router.get("/{installation_id}/payment-qr")
def get_installation_payment_qr(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _load_visible(db, user, installation_id)
    if not is_operations_admin(user) and user.role != "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view payment QR codes")
    if not inst.payment_qr_code_blob:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment QR code not found")
    return Response(
        content=inst.payment_qr_code_blob,
        media_type=inst.payment_qr_code_content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{inst.payment_qr_code_filename or "payment-qr"}"'
        },
    )


@router.put("/{installation_id}", response_model=InstallationOut)
def update_installation(
    installation_id: int,
    body: InstallationStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _load_visible(db, user, installation_id)
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit installation requests")

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(inst, field, value)
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate(db, inst))


@router.patch("/{installation_id}/payment-amount", response_model=InstallationOut)
def admin_update_installation_payment_amount(
    installation_id: int,
    body: AdminInstallationPaymentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admin can update payment amounts")
    inst = _load_visible(db, user, installation_id)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment fields provided")

    for payment_type_field in ("payment_type_requested", "payment_type_paid"):
        if payment_type_field in data:
            normalized = (data[payment_type_field] or "").strip()
            if normalized not in PAYMENT_TYPES:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")
            data[payment_type_field] = normalized

    for amount_field in ("payment_amount_requested", "payment_amount_paid"):
        if amount_field in data and data[amount_field] is not None and data[amount_field] < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount cannot be negative")

    for field, value in data.items():
        setattr(inst, field, value)
    if "payment_amount_paid" in data and data["payment_amount_paid"] is not None:
        inst.payment_recorded_at = datetime.now(timezone.utc)
        inst.payment_recorded_by = user.id
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate(db, inst))


@router.put("/{installation_id}/status", response_model=InstallationOut)
async def update_status(
    installation_id: int,
    background_tasks: BackgroundTasks,
    new_status: str = Form(...),
    assigned_engineer: int | None = Form(None),
    installation_date: str | None = Form(None),
    work_report: str | None = Form(None),
    document: UploadFile | None = File(None),
    settlement_approved_by: int | None = Form(None),
    payment_amount: str | None = Form(None),
    payment_type: str | None = Form(None),
    qr_code: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Engineer-only pseudo-status: sends the job back to admin/Incool for reassignment
    # (status -> "Submitted", engineer unassigned) rather than a real lifecycle state.
    if new_status == "Send Back to Admin":
        inst = _load_visible(db, user, installation_id)
        if user.role != "engineer":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only engineers can send a job back to admin")
        if inst.status != "Assigned":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Can only send back to admin while status is still Assigned (before work starts)",
            )
        inst.status = "Submitted"
        inst.assigned_engineer = None
        db.commit()
        db.refresh(inst)
        return InstallationOut(**_hydrate(db, inst))

    if new_status not in STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")

    inst = _load_visible(db, user, installation_id)
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this installation request")
    if user.role == "engineer" and is_vendor_assigned_engineer_workflow(inst):
        prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user)
    if user.role == "engineer" and assigned_engineer is not None and assigned_engineer != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Engineers cannot reassign installation requests")
    if (
        supports_engineer_installation_workflow(inst)
        and not inst.serial_verified_at
        and new_status in {"Installation Completed", "Completed", "Payment Pending", "Settlement Pending", "Settlement Approved"}
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Installation requires serial verification before completion",
        )
    if (
        supports_engineer_installation_workflow(inst)
        and inst.serial_verified_at
        and user.role == "engineer"
        and new_status == "Completed"
        and inst.status != "Payment Pending"
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Use complete installation and payment request actions for assigned installations",
        )

    old_status = inst.status
    if (
        is_operations_admin(user)
        and new_status in {"Returned", "Rejected"}
        and supports_engineer_installation_workflow(inst)
        and inst.assigned_engineer
    ):
        reject_stage = "payment" if inst.status == "Payment Pending" else "completion"
        if work_report:
            inst.admin_approval_remark = work_report.strip()
        inst.status = return_installation_to_engineer_for_rework(inst, reject_stage=reject_stage)
        log_installation_action(
            db,
            inst,
            action="Returned to Engineer" if new_status == "Returned" else "Completion Rejected",
            user=user,
            old_status=old_status,
            new_status=inst.status,
            remarks=work_report,
        )
        db.commit()
        db.refresh(inst)
        return InstallationOut(**_hydrate(db, inst))

    doc_path = None
    if document is not None and document.filename:
        doc_path = await save_upload(document, module="installations")
    if user.role == "engineer" and new_status == "Completed" and not doc_path and not inst.work_report_file_path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload Document is required when status is Completed")
    effective_payment_type = (payment_type or "").strip() or inst.payment_type_requested
    if (
        is_operations_admin(user)
        and new_status == "Completed"
        and inst.status == "Payment Pending"
        and effective_payment_type == "UPI"
        and not doc_path
        and not inst.payment_proof_file_path
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload Payment Proof / Document is required when payment type is UPI")
    qr_blob = None
    qr_filename = None
    qr_content_type = None
    qr_size_bytes = None
    if qr_code is not None and qr_code.filename:
        qr_blob, qr_filename, qr_content_type, qr_size_bytes = await read_upload_bytes(qr_code)

    inst.status = _apply_payment_transition(
        inst,
        requested_status=new_status,
        actor=user,
        installation_date=installation_date,
        payment_amount=payment_amount,
        payment_type=payment_type,
        payment_qr_code_path=None,
        payment_qr_code_blob=qr_blob,
        payment_qr_code_filename=qr_filename,
        payment_qr_code_content_type=qr_content_type,
        payment_qr_code_size_bytes=qr_size_bytes,
    )
    if assigned_engineer is not None:
        inst.assigned_engineer = assigned_engineer
        if inst.status in {"Submitted", "Assigned"}:
            inst.status = "Assigned"
        prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user)
    if installation_date:
        inst.installation_date = datetime.fromisoformat(installation_date)
    if work_report is not None:
        inst.work_report = work_report
    if doc_path:
        if (
            is_operations_admin(user)
            and inst.status == "Payment Pending"
            and new_status == "Completed"
            and effective_payment_type == "UPI"
        ):
            inst.payment_proof_file_path = doc_path
        else:
            inst.work_report_file_path = doc_path
    if settlement_approved_by is not None:
        inst.settlement_approved_by = settlement_approved_by
    if qr_blob:
        inst.payment_qr_code_blob = qr_blob
        inst.payment_qr_code_filename = qr_filename
        inst.payment_qr_code_content_type = qr_content_type
        inst.payment_qr_code_size_bytes = qr_size_bytes
        inst.payment_qr_code_path = None
    if (
        is_operations_admin(user)
        and inst.status == "Completed"
        and inst.payment_recorded_at
        and not inst.payment_transaction_id
        and old_status == "Payment Pending"
    ):
        _create_payment_transaction(
            db,
            rows=[inst],
            actor=user,
            payment_type=inst.payment_type_paid or inst.payment_type_requested or "Cash",
        )
    _sync_order_completion_state(db, inst)

    if inst.serial_no:
        create_serial_history_event(
            db,
            serial_no=inst.serial_no,
            serial_no_2=inst.serial_no_2,
            order_item_id=inst.order_item_id,
            event_type=EVENT_TYPES["INSTALLATION"],
            event_subtype=f"STATUS_{new_status.upper().replace(' ', '_')}",
            event_at=inst.installation_date or datetime.now(timezone.utc),
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="installation_requests",
            source_id=inst.id + 1000000,
            title="Installation status updated",
            description=f"Installation request {inst.id} updated to {new_status}.",
            remarks=work_report,
            metadata={"status": new_status, "document_path": doc_path},
        )

    db.commit()
    db.refresh(inst)
    linked_order = None
    if inst.order_item_id:
        item = db.get(OrderItem, inst.order_item_id)
        if item is not None:
            linked_order = db.get(Order, item.order_id)
    if linked_order is not None:
        notify_customer_installation_update(
            background_tasks,
            order=linked_order,
            installation=inst,
            old_status=old_status,
            new_status=inst.status,
        )
    if assigned_engineer is not None and inst.status == "Assigned":
        engineer = db.get(User, assigned_engineer)
        if engineer is not None:
            notify_engineer_installation_assigned(
                background_tasks,
                engineer=engineer,
                installation_ids=[inst.id],
                order_nos=[linked_order.order_no] if linked_order and linked_order.order_no else [],
            )
    return InstallationOut(**_hydrate(db, inst))


@router.post("/bulk-status-update", response_model=list[InstallationOut])
async def bulk_update_status(
    installation_ids: str = Form(...),
    new_status: str = Form(...),
    installation_date: str | None = Form(None),
    work_report: str | None = Form(None),
    payment_amount: str | None = Form(None),
    payment_type: str | None = Form(None),
    settlement_approved_by: int | None = Form(None),
    assigned_engineer: int | None = Form(None),
    document: UploadFile | None = File(None),
    qr_code: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if new_status not in STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
    if not can_act_on(db, user, "installations", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit installation requests")

    try:
        parsed_ids = [int(raw.strip()) for raw in installation_ids.split(",") if raw.strip()]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid installation id list")
    if not parsed_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No installation requests selected")

    rows = [_load_visible(db, user, installation_id) for installation_id in parsed_ids]
    item_codes = {
        ((db.get(OrderItem, row.order_item_id).item_code if row.order_item_id else None) or "").strip() or "UNASSIGNED"
        for row in rows
    }
    if len(item_codes) > 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bulk editing is allowed only within the same Item Code group")

    qr_blob = None
    qr_filename = None
    qr_content_type = None
    qr_size_bytes = None
    if qr_code is not None and qr_code.filename:
        qr_blob, qr_filename, qr_content_type, qr_size_bytes = await read_upload_bytes(qr_code)
    doc_path = None
    if document is not None and document.filename:
        doc_path = await save_upload(document, module="installations")
    if (
        user.role == "engineer"
        and new_status == "Completed"
        and not doc_path
        and any(not row.work_report_file_path for row in rows)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload Document is required when status is Completed")
    if is_operations_admin(user) and new_status == "Completed":
        missing_upi_proof = any(
            row.status == "Payment Pending"
            and ((payment_type or "").strip() or row.payment_type_requested) == "UPI"
            and not row.payment_proof_file_path
            for row in rows
        )
        if missing_upi_proof and not doc_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload Payment Proof / Document is required when payment type is UPI")

    bulk_admin_paid_amounts: dict[int, Decimal] = {}
    if (
        is_operations_admin(user)
        and new_status == "Completed"
        and payment_amount not in (None, "")
    ):
        payment_pending_rows = [row for row in rows if row.status == "Payment Pending"]
        split_amounts = _split_total_amount(payment_amount, len(payment_pending_rows))
        bulk_admin_paid_amounts = {
            row.id: split_amounts[idx]
            for idx, row in enumerate(payment_pending_rows)
        }

    updated: list[InstallationOut] = []
    for inst in rows:
        inst.status = _apply_payment_transition(
            inst,
            requested_status=new_status,
            actor=user,
            installation_date=installation_date,
            payment_amount=None if inst.id in bulk_admin_paid_amounts else payment_amount,
            payment_type=payment_type,
            payment_qr_code_path=None,
            payment_qr_code_blob=qr_blob,
            payment_qr_code_filename=qr_filename,
            payment_qr_code_content_type=qr_content_type,
            payment_qr_code_size_bytes=qr_size_bytes,
        )
        if inst.id in bulk_admin_paid_amounts:
            inst.payment_amount_paid = bulk_admin_paid_amounts[inst.id]
        if assigned_engineer is not None:
            inst.assigned_engineer = assigned_engineer
            if inst.status in {"Submitted", "Assigned"}:
                inst.status = "Assigned"
            prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user)
        if installation_date:
            inst.installation_date = datetime.fromisoformat(installation_date)
        if work_report is not None:
            inst.work_report = work_report
        if doc_path:
            if is_operations_admin(user) and (inst.status == "Payment Pending" or new_status == "Completed"):
                inst.payment_proof_file_path = doc_path
            else:
                inst.work_report_file_path = doc_path
        if settlement_approved_by is not None:
            inst.settlement_approved_by = settlement_approved_by
        if qr_blob:
            inst.payment_qr_code_blob = qr_blob
            inst.payment_qr_code_filename = qr_filename
            inst.payment_qr_code_content_type = qr_content_type
            inst.payment_qr_code_size_bytes = qr_size_bytes
            inst.payment_qr_code_path = None
        updated.append(InstallationOut(**_hydrate(db, inst)))

    if is_operations_admin(user) and new_status == "Completed":
        completed_rows = [inst for inst in rows if inst.status == "Completed" and inst.payment_recorded_at]
        if completed_rows:
            _create_payment_transaction(
                db,
                rows=completed_rows,
                actor=user,
                payment_type=completed_rows[0].payment_type_paid or completed_rows[0].payment_type_requested or "Cash",
            )

    for inst in rows:
        _sync_order_completion_state(db, inst)

    db.commit()
    for inst in rows:
        db.refresh(inst)
    return [InstallationOut(**_hydrate(db, inst)) for inst in rows]


@router.delete("/{installation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _load_visible(db, user, installation_id)
    if not can_act_on(db, user, "installations", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete this installation request")
    db.delete(inst)
    db.commit()
