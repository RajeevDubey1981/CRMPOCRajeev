import json
import secrets
import time
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import desc, exists, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.complaint import Complaint, ComplaintStatusLog
from app.models.order import Order, OrderItem
from app.models.payment import PaymentTransaction
from app.models.service import (
    ServiceApproval,
    ServiceAssignment,
    ServiceCompletion,
    ServiceDocument,
    ServiceDocumentRule,
    ServiceObservation,
    ServicePaymentRequest,
    ServiceNotification,
    ServiceRequest,
    ServiceRequestItem,
    ServiceRequestUnit,
    ServiceStatusLog,
    ServiceUnitAssignment,
)
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.serial import SerialLookup
from app.schemas.service import (
    SERVICE_STATUSES,
    ServiceApprovalIn,
    ServiceApprovalOut,
    ServiceAddUnitBySerialIn,
    ServiceAssignUnitsIn,
    ServiceAssignmentIn,
    ServiceAssignmentOut,
    ServiceBulkApprovalIn,
    ServiceBulkObservationsIn,
    ServiceBulkSerialVerifyIn,
    ServiceCompletionIn,
    ServiceCompletionIn,
    ServiceCompletionOut,
    ServiceCreate,
    ServiceDocumentOut,
    ServiceDocumentLinkOut,
    ServiceDocumentReviewIn,
    ServiceHistoryEntry,
    ServiceIdentifyCustomer,
    ServiceListItem,
    ServiceListResponse,
    ServiceObservationIn,
    ServiceObservationCancelIn,
    ServiceObservationOut,
    ServiceOrderItemSummary,
    ServiceOut,
    ServicePaymentRequestIn,
    ServicePaymentRequestOut,
    ServicePaymentCompleteIn,
    AdminServicePaymentUpdate,
    ServicePublicDocumentContext,
    ServiceRequestUnitOut,
    ServiceUnitBillingIn,
    ServiceSerialVerifyIn,
    ServiceSerialReviewIn,
    ServiceSummary,
    ServiceUpdate,
    ServiceVerifyOrderIn,
    EngineerAssignedUnitGroup,
)
from app.services.engineer_service_scope import engineer_visible_service_filter
from app.services.email_service import (
    send_document_upload_link_email,
    send_service_request_acknowledgment_email,
    send_service_unit_assignment_email,
)
from app.services.workflow_notifications import (
    after_service_approval,
    after_service_status_change,
    notify_customer_happy_code,
    notify_engineer_service_assigned,
    notify_vendor_service_assigned,
)
from app.services.role_access import is_operations_admin, is_service_team
from app.services.file_service import save_upload, to_public_upload_path
from app.services.service_completion_code import clear_completion_code, issue_completion_code, validate_engineer_completion_code
from app.services.service_documents import (
    CUSTOMER_DOCUMENT_EXTENSIONS,
    CUSTOMER_DOCUMENT_MIME_TYPES,
    CUSTOMER_DOCUMENT_TYPES,
    build_public_upload_url,
    customer_document_types,
    customer_documents_approved,
    order_workflow_unlocked,
    on_enter_service_team_review,
    reset_service_workflow_from_status,
    service_workflow_is_revert,
    sync_document_workflow_status,
)
from app.services.serial_history import write_service_completion_serial_history
from app.services.service_serial import (
    associate_serial_with_service_order,
    find_customer_order_item_by_serial,
    find_order_item_by_serial as _find_order_item_by_serial_global,
    find_order_item_by_serial_on_order,
)
from app.services.service_units import (
    add_service_unit_by_serial,
    apply_service_billing_choice,
    apply_unit_billing_choice,
    assign_units_to_engineer,
    BILLING_LOCKED_UNIT_STATUSES,
    build_engineer_unit_groups,
    build_order_item_summaries,
    build_unit_rows,
    engineer_has_unit_assignment,
    verify_order_for_service,
)
from app.services.service_unit_workflow import (
    backfill_unit_statuses,
    backfill_unit_verification_from_service,
    bulk_approve_units,
    bulk_submit_observations,
    bulk_verify_units,
    approve_unit,
    align_units_to_service_status,
    complete_unit,
    list_work_units,
    observations_for_service,
    raise_payment_for_unit,
    close_service_with_units,
    reopen_service_to_engineer,
    cancel_payment_for_unit,
    serial_matches_unit,
    submit_unit_observation,
    sync_aggregate_service_status,
    sync_service_request_from_units,
    verify_unit_serial,
)

router = APIRouter(prefix="/api/services", tags=["services"])

SERVICE_STATUS_FLOW = {
    "New": {"Service Team Review", "Admin Review Document", "Cancelled"},
    "Service Team Review": {"Admin Review Document", "Assigned", "Cancelled", "Rejected"},
    "Admin Review Document": {"Service Team Review", "Cancelled", "Rejected"},
    "Assigned": {"Engineer Visit", "Cancelled", "Rejected"},
    "Engineer Visit": {"Serial Verification Review", "Serial Verified", "Cancelled"},
    "Serial Verification Review": {"Serial Verified", "Engineer Visit", "Cancelled"},
    "Serial Verified": {"Pending Service Approval", "Service In Progress"},
    "Pending Service Approval": {"Approved for Service", "Rejected"},
    "Approved for Service": {"Service In Progress", "Cancelled"},
    "Service In Progress": {"Service Completed", "Cancelled"},
    "Service Completed": {"Payment Requested", "Closed"},
    "Completion Pending Approval": {"Service Completed", "Approved for Service", "Cancelled"},
    "Payment Requested": {"Payment Completed", "Closed"},
    "Payment Completed": {"Closed"},
    "Closed": set(),
    "Rejected": {"Assigned", "Cancelled"},
    "Cancelled": set(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _role(user: User) -> str:
    return (user.role or "").lower()


def _is_service_team(user: User) -> bool:
    return is_service_team(user)


def _is_call_center(user: User) -> bool:
    return _role(user) in {"callcenter", "call center", "admin", "incool", "indcool service", "indcool_service"}
def _is_workflow_admin(user: User) -> bool:
    return _role(user) in {"admin", "incool", "indcool", "service", "indcool service", "indcool_service"}


def _is_engineer(user: User) -> bool:
    return _role(user) == "engineer"


def _is_vendor(user: User) -> bool:
    return _role(user) == "vendor"


def _resolve_linked_complaint_from_service(db: Session, service: ServiceRequest, user: User, remark: str | None = None) -> None:
    if not service.complaint_id or service.status not in {"Payment Completed", "Closed"}:
        return
    complaint = db.get(Complaint, service.complaint_id)
    if complaint is None or complaint.status == "Resolved":
        return

    old_status = complaint.status
    complaint.status = "Resolved"
    complaint.status_date = _now()
    complaint.remark = remark or f"Auto resolved after service request {service.request_no} reached {service.status}."
    db.add(ComplaintStatusLog(
        complaint_id=complaint.id,
        old_status=old_status,
        new_status="Resolved",
        changed_by=user.id,
        remark=complaint.remark,
        action_taken="Service Request Completed",
    ))


def _generate_request_no() -> str:
    return f"SRV_{int(time.time() * 1000)}"


def _generate_access_token() -> str:
    return secrets.token_urlsafe(24)


def _json_load(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _json_dump(value) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value)


def _user_name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    return user.name if user else None


def _vendor_name(db: Session, vendor_id: int | None) -> str | None:
    if not vendor_id:
        return None
    vendor = db.get(Vendor, vendor_id)
    return vendor.name_of_firm if vendor else None


def _active_vendor_for_user(db: Session, user: User) -> Vendor | None:
    if not _is_vendor(user):
        return None
    return db.scalar(select(Vendor).where(Vendor.email == user.email))


def _engineer_assigned_service_ids(db: Session, engineer_id: int):
    return select(ServiceRequestUnit.service_request_id).where(
        ServiceRequestUnit.assigned_engineer_id == engineer_id
    ).distinct()


def _service_visible_to_user(db: Session, service: ServiceRequest, user: User) -> bool:
    if _is_service_team(user) or _is_call_center(user):
        return True
    if _is_engineer(user):
        if service.assigned_engineer_id == user.id:
            return True
        if engineer_has_unit_assignment(db, service.id, user.id):
            return True
        if service.complaint_id:
            complaint = db.get(Complaint, service.complaint_id)
            return complaint is not None and complaint.assigned_engineer == user.id
        return False
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        return vendor is not None and service.assigned_vendor_id == vendor.id
    return False


def _engineer_can_work_on_service(db: Session, service: ServiceRequest, user: User) -> bool:
    if service.assigned_engineer_id == user.id:
        return True
    return engineer_has_unit_assignment(db, service.id, user.id)


def _load_visible_service(db: Session, service_id: int, user: User) -> ServiceRequest:
    service = db.get(ServiceRequest, service_id)
    if service is None or service.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    if not _service_visible_to_user(db, service, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    return service


def _count_service_documents(db: Session, service_id: int) -> int:
    return db.scalar(select(func.count()).select_from(ServiceDocument).where(ServiceDocument.service_request_id == service_id)) or 0


def _count_unread_notifications(db: Session, user: User) -> int:
    if not _is_service_team(user):
        return 0
    return db.scalar(
        select(func.count()).select_from(ServiceNotification).where(
            ServiceNotification.recipient_user_id == user.id,
            ServiceNotification.is_read == False,
        )
    ) or 0


def _find_order_item_by_serial(db: Session, serial_no: str) -> OrderItem | None:
    return _find_order_item_by_serial_global(db, serial_no)


def _apply_customer_serial_to_service(db: Session, service: ServiceRequest, serial_no: str) -> None:
    normalized = (serial_no or "").strip()
    if not normalized:
        return
    item = find_customer_order_item_by_serial(db, service, normalized)
    if item is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Serial number was not found on any order for this customer.",
        )
    order = db.get(Order, item.order_id)
    service.serial_no = normalized
    service.order_item_id = item.id
    if order is not None:
        service.order_id = order.id
    context = _derive_service_context(db, item)
    service.warranty_status = context["warranty_status"]
    service.service_type = context["service_type"]


def _add_years(base_date: date | None, years: int | None) -> date | None:
    if base_date is None or years is None:
        return None
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def _derive_service_context(db: Session, item: OrderItem | None):
    if item is None:
        return {"warranty_status": None, "service_type": None, "order": None}
    order = db.get(Order, item.order_id) if item.order_id else None
    warranty_base = None
    if order is not None:
        warranty_base = order.actual_delivery_date or order.expected_delivery_date or order.order_date
    machine_warranty_date = _add_years(warranty_base, item.machine_warranty_years)
    today = date.today()
    in_warranty = machine_warranty_date is not None and today <= machine_warranty_date
    warranty_status = "IN WARRANTY" if in_warranty else "OUT OF WARRANTY"
    if item.free_service_count and item.service_consume_count < item.free_service_count:
        service_type = "Free Service"
    elif in_warranty:
        service_type = "Warranty Service"
    else:
        service_type = "Paid Service"
    return {
        "warranty_status": warranty_status,
        "service_type": service_type,
        "order": order,
        "warranty_base": warranty_base,
        "pcb_warranty_date": _add_years(warranty_base, item.pcb_warranty_years),
        "component_warranty_date": _add_years(warranty_base, item.component_warranty_years),
        "machine_warranty_date": machine_warranty_date,
    }


def _required_documents(db: Session, service_type: str | None, warranty_status: str | None, query_type: str | None) -> list[str]:
    stmt = select(ServiceDocumentRule).where(ServiceDocumentRule.is_active == True, ServiceDocumentRule.is_required == True)
    rules = db.scalars(stmt).all()
    docs: list[str] = []
    for rule in rules:
        if rule.service_type and rule.service_type != service_type:
            continue
        if rule.warranty_status and rule.warranty_status != warranty_status:
            continue
        if rule.query_type and rule.query_type != query_type:
            continue
        docs.append(rule.document_type)
    if not docs and service_type in {"Warranty Service", "Paid Service"}:
        docs = ["Invoice Copy"]
        if service_type == "Warranty Service":
            docs.append("Warranty Proof")
    return docs


def _customer_document_types(db: Session, service: ServiceRequest) -> list[str]:
    return customer_document_types(db, service)


def _ensure_order_workflow_unlocked(db: Session, service: ServiceRequest) -> None:
    if order_workflow_unlocked(db, service):
        return
    if service.status == "Admin Review Document":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Approve customer documents before verifying the order or assigning units.",
        )
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "Customer documents must be uploaded and approved before order verification or unit assignment.",
    )


def _mark_service_notifications_read(db: Session, service: ServiceRequest, user: User) -> None:
    if not _is_service_team(user):
        return
    rows = db.scalars(
        select(ServiceNotification).where(
            ServiceNotification.service_request_id == service.id,
            ServiceNotification.recipient_user_id == user.id,
            ServiceNotification.is_read == False,
        )
    ).all()
    if not rows:
        return
    when = _now()
    for row in rows:
        row.is_read = True
        row.read_at = when


def _notify_service_team(db: Session, service: ServiceRequest, title: str, message: str, notification_type: str) -> None:
    from app.services.pending_action_sync import sync_service_pending_actions

    sync_service_pending_actions(db, service)


def _validate_customer_document_upload(document_type: str, file: UploadFile) -> None:
    if document_type not in CUSTOMER_DOCUMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid customer document type")
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in CUSTOMER_DOCUMENT_EXTENSIONS):
        if file.content_type not in CUSTOMER_DOCUMENT_MIME_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF, JPG, JPEG, and PNG files are allowed")


def _send_document_link_email(
    service: ServiceRequest,
    upload_url: str,
    required_documents: list[str] | None = None,
) -> None:
    send_document_upload_link_email(
        to=service.customer_email or "",
        customer_name=service.customer_name,
        ticket_id=service.request_no,
        upload_url=upload_url,
        required_documents=required_documents,
    )


def _log_status(
    db: Session,
    service: ServiceRequest,
    *,
    action: str,
    user: User,
    old_status: str | None,
    new_status: str | None,
    remarks: str | None = None,
    metadata: dict | None = None,
):
    log = ServiceStatusLog(
        service_request_id=service.id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        performed_by=user.id,
        performed_role=user.role,
        remarks=remarks,
        metadata_json=_json_dump(metadata),
        created_at=_now(),
    )
    db.add(log)
    db.flush()
    from app.services.pending_action_sync import sync_service_pending_actions

    sync_service_pending_actions(db, service)


def _write_service_summary_to_serial_history(
    db: Session,
    service: ServiceRequest,
    completion: ServiceCompletion,
    user: User,
) -> None:
    write_service_completion_serial_history(
        db,
        service,
        completion,
        performed_by_user_id=user.id,
        performed_by_name=user.name,
    )


def _enforce_transition(current: str, new_status: str):
    if new_status not in SERVICE_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
    if new_status == current:
        return
    allowed = SERVICE_STATUS_FLOW.get(current, set())
    if new_status not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Status transition from '{current}' to '{new_status}' is not allowed")


def _doc_out(db: Session, row: ServiceDocument) -> ServiceDocumentOut:
    return ServiceDocumentOut(
        id=row.id,
        document_type=row.document_type,
        file_path=to_public_upload_path(row.file_path) or row.file_path,
        uploaded_by_type=row.uploaded_by_type,
        uploaded_by_user_id=row.uploaded_by_user_id,
        uploaded_by_customer_name=row.uploaded_by_customer_name,
        status=row.status,
        reviewed_by=row.reviewed_by,
        reviewed_by_name=_user_name(db, row.reviewed_by),
        reviewed_at=row.reviewed_at,
        review_remarks=row.review_remarks,
        uploaded_at=row.uploaded_at,
    )


def _assignment_out(db: Session, row: ServiceAssignment) -> ServiceAssignmentOut:
    return ServiceAssignmentOut(
        id=row.id,
        assignee_type=row.assignee_type,
        assignee_user_id=row.assignee_user_id,
        assignee_user_name=_user_name(db, row.assignee_user_id),
        assignee_vendor_id=row.assignee_vendor_id,
        assignee_vendor_name=_vendor_name(db, row.assignee_vendor_id),
        assigned_by=row.assigned_by,
        assigned_by_name=_user_name(db, row.assigned_by),
        assigned_at=row.assigned_at,
        remarks=row.remarks,
        is_active=row.is_active,
    )


def _observation_out(db: Session, row: ServiceObservation) -> ServiceObservationOut:
    return ServiceObservationOut(
        id=row.id,
        service_request_unit_id=row.service_request_unit_id,
        submitted_by_user_id=row.submitted_by_user_id,
        submitted_by_name=_user_name(db, row.submitted_by_user_id),
        serial_no=row.serial_no,
        warranty_status=row.warranty_status,
        service_type=row.service_type,
        problem_found=row.problem_found,
        observation=row.observation,
        recommended_action=row.recommended_action,
        parts_required=_json_load(row.parts_required_json, []),
        estimated_service_charge=float(row.estimated_service_charge) if row.estimated_service_charge is not None else None,
        estimated_parts_charge=float(row.estimated_parts_charge) if row.estimated_parts_charge is not None else None,
        remarks=row.remarks,
        submitted_at=row.submitted_at,
    )


def _approval_out(db: Session, row: ServiceApproval) -> ServiceApprovalOut:
    return ServiceApprovalOut(
        id=row.id,
        observation_id=row.observation_id,
        decision=row.decision,
        remarks=row.remarks,
        approved_by=row.approved_by,
        approved_by_name=_user_name(db, row.approved_by),
        approved_at=row.approved_at,
    )


def _completion_out(db: Session, row: ServiceCompletion) -> ServiceCompletionOut:
    return ServiceCompletionOut(
        id=row.id,
        performed_by_type=row.performed_by_type,
        performed_by_user_id=row.performed_by_user_id,
        performed_by_name=_user_name(db, row.performed_by_user_id),
        performed_by_vendor_id=row.performed_by_vendor_id,
        performed_by_vendor_name=_vendor_name(db, row.performed_by_vendor_id),
        work_performed=row.work_performed,
        parts_replaced=_json_load(row.parts_replaced_json, []),
        service_notes=row.service_notes,
        service_date=row.service_date,
        old_part_serial_no=row.old_part_serial_no,
        new_part_serial_no=row.new_part_serial_no,
        customer_acknowledgement_path=row.customer_acknowledgement_path,
        final_amount=float(row.final_amount) if row.final_amount is not None else None,
        completion_remarks=row.completion_remarks,
        engineer_completion_code=row.engineer_completion_code,
        completed_at=row.completed_at,
    )


def _payment_out(db: Session, row: ServicePaymentRequest) -> ServicePaymentRequestOut:
    return ServicePaymentRequestOut(
        id=row.id,
        requested_by_type=row.requested_by_type,
        requested_by_user_id=row.requested_by_user_id,
        requested_by_name=_user_name(db, row.requested_by_user_id),
        requested_by_vendor_id=row.requested_by_vendor_id,
        requested_by_vendor_name=_vendor_name(db, row.requested_by_vendor_id),
        service_type=row.service_type,
        customer_charge_amount=float(row.customer_charge_amount) if row.customer_charge_amount is not None else None,
        settlement_service_amount=float(row.settlement_service_amount) if row.settlement_service_amount is not None else None,
        settlement_parts_amount=float(row.settlement_parts_amount) if row.settlement_parts_amount is not None else None,
        total_requested_amount=float(row.total_requested_amount) if row.total_requested_amount is not None else None,
        payment_type=row.payment_type,
        payment_qr_code_path=row.payment_qr_code_path,
        approved_amount=float(row.approved_amount) if row.approved_amount is not None else None,
        remarks=row.remarks,
        status=row.status,
        processed_at=row.processed_at,
        processed_by_user_id=row.processed_by_user_id,
        processed_by_name=_user_name(db, row.processed_by_user_id),
        payment_transaction_id=row.payment_transaction_id,
        created_at=row.created_at,
    )


def _hydrate_service(db: Session, service: ServiceRequest) -> ServiceOut:
    order = db.get(Order, service.order_id) if service.order_id else None
    order_item = db.get(OrderItem, service.order_item_id) if service.order_item_id else None
    serial_context = _derive_service_context(db, order_item) if order_item else {}
    documents = db.scalars(select(ServiceDocument).where(ServiceDocument.service_request_id == service.id).order_by(desc(ServiceDocument.uploaded_at))).all()
    assignments = db.scalars(select(ServiceAssignment).where(ServiceAssignment.service_request_id == service.id).order_by(desc(ServiceAssignment.assigned_at))).all()
    observations = db.scalars(select(ServiceObservation).where(ServiceObservation.service_request_id == service.id).order_by(desc(ServiceObservation.submitted_at))).all()
    approvals = db.scalars(select(ServiceApproval).where(ServiceApproval.service_request_id == service.id).order_by(desc(ServiceApproval.approved_at))).all()
    completions = db.scalars(select(ServiceCompletion).where(ServiceCompletion.service_request_id == service.id).order_by(desc(ServiceCompletion.completed_at))).all()
    payment_requests = db.scalars(select(ServicePaymentRequest).where(ServicePaymentRequest.service_request_id == service.id).order_by(desc(ServicePaymentRequest.created_at))).all()
    complaint = db.get(Complaint, service.complaint_id) if service.complaint_id else None
    return ServiceOut(
        id=service.id,
        request_no=service.request_no,
        request_date=service.request_date,
        query_type=service.query_type,
        customer_name=service.customer_name,
        customer_mobile=service.customer_mobile,
        customer_email=service.customer_email,
        customer_address=service.customer_address,
        model_details=service.model_details,
        problem_description=service.problem_description,
        additional_remarks=service.additional_remarks,
        status=service.status,
        status_date=service.status_date,
        source=service.source,
        created_by=service.created_by,
        created_by_name=_user_name(db, service.created_by),
        complaint_id=service.complaint_id,
        complaint_no=complaint.comp_no if complaint else None,
        order_id=service.order_id,
        order_item_id=service.order_item_id,
        order_no=order.order_no if order else None,
        serial_no=service.serial_no,
        pcb_warranty_date=serial_context.get("pcb_warranty_date"),
        component_warranty_date=serial_context.get("component_warranty_date"),
        machine_warranty_date=serial_context.get("machine_warranty_date"),
        service_type=service.service_type,
        warranty_status=service.warranty_status,
        assigned_engineer_id=service.assigned_engineer_id,
        assigned_engineer_name=_user_name(db, service.assigned_engineer_id),
        assigned_vendor_id=service.assigned_vendor_id,
        assigned_vendor_name=_vendor_name(db, service.assigned_vendor_id),
        requires_documents=service.requires_documents,
        ask_for_documents=service.ask_for_documents,
        document_request_sent_at=service.document_request_sent_at,
        document_access_token=service.document_access_token,
        upload_url=build_public_upload_url(service.document_access_token) if service.document_access_token else None,
        customer_identified_at=service.customer_identified_at,
        approved_at=service.approved_at,
        completed_at=service.completed_at,
        closed_at=service.closed_at,
        completion_code=service.completion_code,
        created_at=service.created_at,
        updated_at=service.updated_at,
        documents=[_doc_out(db, row) for row in documents],
        assignments=[_assignment_out(db, row) for row in assignments],
        observations=[_observation_out(db, row) for row in observations],
        approvals=[_approval_out(db, row) for row in approvals],
        completions=[_completion_out(db, row) for row in completions],
        payment_requests=[_payment_out(db, row) for row in payment_requests],
        order_items=[ServiceOrderItemSummary(**row) for row in build_order_item_summaries(db, service.id)],
        units=[ServiceRequestUnitOut(**row) for row in build_unit_rows(db, service.id)],
        required_document_types=customer_document_types(db, service),
        customer_documents_approved=customer_documents_approved(db, service),
    )


@router.get("/summary", response_model=ServiceSummary)
def service_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))
    if _is_engineer(user):
        stmt = stmt.where(engineer_visible_service_filter(user.id))
    elif _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None:
            return ServiceSummary(new_requests=0, unassigned=0, assigned=0, pending_observation=0, pending_approval=0, approved=0, in_progress=0, payment_pending=0, completed=0, closed=0, unread_notifications=0)
        stmt = stmt.where(ServiceRequest.assigned_vendor_id == vendor.id)
    def cnt(status_value: str) -> int:
        return db.scalar(select(func.count()).select_from(stmt.where(ServiceRequest.status == status_value).subquery())) or 0
    unassigned_stmt = select(func.count()).select_from(
        select(ServiceRequest).where(
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.assigned_engineer_id.is_(None),
            ServiceRequest.assigned_vendor_id.is_(None),
        ).subquery()
    )
    if _is_engineer(user) or _is_vendor(user):
        unassigned = 0
    else:
        unassigned = db.scalar(unassigned_stmt) or 0
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
        unread_notifications=_count_unread_notifications(db, user),
    )


@router.get("", response_model=ServiceListResponse)
def list_services(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    service_type: str | None = None,
    engineer_id: int | None = None,
    vendor_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))
    if _is_engineer(user):
        stmt = stmt.where(engineer_visible_service_filter(user.id))
    elif not (_is_service_team(user) or _is_call_center(user)):
        return ServiceListResponse(items=[], total=0, page=page, per_page=per_page)
    if status_filter:
        stmt = stmt.where(ServiceRequest.status == status_filter)
    if service_type:
        stmt = stmt.where(ServiceRequest.service_type == service_type)
    if engineer_id:
        stmt = stmt.where(ServiceRequest.assigned_engineer_id == engineer_id)
    if vendor_id:
        stmt = stmt.where(ServiceRequest.assigned_vendor_id == vendor_id)
    if date_from:
        stmt = stmt.where(ServiceRequest.request_date >= date_from)
    if date_to:
        stmt = stmt.where(ServiceRequest.request_date <= date_to)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ServiceRequest.request_no.ilike(like),
                ServiceRequest.customer_name.ilike(like),
                ServiceRequest.customer_mobile.ilike(like),
                ServiceRequest.serial_no.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(desc(ServiceRequest.created_at)).offset((page - 1) * per_page).limit(per_page)).all()
    items: list[ServiceListItem] = []
    for row in rows:
        order = db.get(Order, row.order_id) if row.order_id else None
        complaint = db.get(Complaint, row.complaint_id) if row.complaint_id else None
        items.append(
            ServiceListItem(
                id=row.id,
                request_no=row.request_no,
                request_date=row.request_date,
                customer_name=row.customer_name,
                customer_mobile=row.customer_mobile,
                order_no=order.order_no if order else None,
                serial_no=row.serial_no,
                status=row.status,
                service_type=row.service_type,
                warranty_status=row.warranty_status,
                assigned_engineer_name=_user_name(db, row.assigned_engineer_id),
                assigned_vendor_name=_vendor_name(db, row.assigned_vendor_id),
                requires_documents=row.requires_documents,
                document_count=_count_service_documents(db, row.id),
                complaint_id=row.complaint_id,
                complaint_no=complaint.comp_no if complaint else None,
                created_at=row.created_at,
            )
        )
    return ServiceListResponse(items=items, total=total, page=page, per_page=per_page)


def _queue_service_request_acknowledgment_email(background_tasks: BackgroundTasks, service: ServiceRequest) -> None:
    if not service.customer_email:
        return
    background_tasks.add_task(
        send_service_request_acknowledgment_email,
        service.customer_email,
        service.request_no,
    )


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _is_call_center(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create service requests")
    service = ServiceRequest(
        request_no=_generate_request_no(),
        request_date=body.request_date or date.today(),
        query_type=body.query_type,
        customer_name=body.customer_name,
        customer_mobile=body.customer_mobile,
        customer_email=body.customer_email,
        customer_address=body.customer_address,
        model_details=body.model_details,
        problem_description=body.problem_description,
        additional_remarks=body.additional_remarks,
        status="New",
        status_date=_now(),
        source="callcenter",
        created_by=user.id,
        document_access_token=_generate_access_token(),
    )
    docs = _required_documents(db, service.service_type, service.warranty_status, service.query_type)
    service.requires_documents = bool(docs)
    service.ask_for_documents = bool(docs)
    if docs:
        service.document_request_sent_at = _now()
    db.add(service)
    db.flush()
    _log_status(db, service, action="Request Created", user=user, old_status=None, new_status="New", remarks=body.additional_remarks, metadata={"requested_documents": docs})
    db.commit()
    db.refresh(service)
    _queue_service_request_acknowledgment_email(background_tasks, service)
    return _hydrate_service(db, service)


@router.get("/lookup/engineers")
def engineer_lookup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (_is_service_team(user) or _is_call_center(user)):
        return []
    rows = db.scalars(select(User).where(User.deleted_at.is_(None), User.is_active == True, func.lower(User.role) == "engineer").order_by(User.name)).all()
    return [{"id": row.id, "name": row.name, "email": row.email, "phone": row.phone} for row in rows]


@router.get("/lookup/vendors")
def vendor_lookup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (_is_service_team(user) or _is_call_center(user)):
        return []
    rows = db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None), Vendor.is_active == True).order_by(Vendor.name_of_firm)).all()
    return [
        {
            "id": row.id,
            "name": row.name_of_firm,
            "email": row.email,
            "phone": row.contact_mobile,
            "vendor_type": row.vendor_type,
        }
        for row in rows
    ]


@router.get("/customers/search")
def customer_search(
    mobile: str | None = None,
    name: str | None = None,
    order_no: str | None = None,
    serial: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (_is_service_team(user) or _is_call_center(user)):
        return []
    seen: set[tuple] = set()
    results: list[dict] = []

    def add_result(payload: dict) -> None:
        key = (
            (payload.get("customer_name") or "").strip().lower(),
            (payload.get("customer_mobile") or "").strip(),
            payload.get("order_id"),
        )
        if key in seen:
            return
        seen.add(key)
        results.append(payload)

    stmt = select(Order).where(Order.deleted_at.is_(None))
    order_terms = []
    if mobile and mobile.strip():
        order_terms.append(Order.customer_contact.ilike(f"%{mobile.strip()}%"))
    if name and name.strip():
        order_terms.append(Order.customer_name.ilike(f"%{name.strip()}%"))
    if order_no and order_no.strip():
        order_terms.append(Order.order_no.ilike(f"%{order_no.strip()}%"))
    if serial and serial.strip():
        serial_term = f"%{serial.strip()}%"
        order_terms.append(
            exists(
                select(OrderItem.id).where(
                    OrderItem.order_id == Order.id,
                    or_(
                        OrderItem.serial_no.ilike(serial_term),
                        OrderItem.serial_no_2.ilike(serial_term),
                    ),
                )
            )
        )
    if order_terms:
        stmt = stmt.where(or_(*order_terms))
    rows = db.scalars(stmt.order_by(desc(Order.created_at)).limit(20)).all()
    for row in rows:
        add_result({
            "order_id": row.id,
            "order_no": row.order_no,
            "customer_name": row.customer_name,
            "customer_mobile": row.customer_contact,
            "customer_email": row.customer_email,
            "customer_address": row.customer_address,
            "source_type": "order",
        })

    complaint_stmt = select(Complaint).where(Complaint.deleted_at.is_(None))
    complaint_terms = []
    if mobile and mobile.strip():
        complaint_terms.append(Complaint.customer_mobile.ilike(f"%{mobile.strip()}%"))
    if name and name.strip():
        complaint_terms.append(Complaint.customer_name.ilike(f"%{name.strip()}%"))
    if complaint_terms:
        complaint_stmt = complaint_stmt.where(or_(*complaint_terms))
    complaint_rows = db.scalars(complaint_stmt.order_by(desc(Complaint.created_at)).limit(20)).all()
    for row in complaint_rows:
        add_result({
            "order_id": None,
            "order_no": None,
            "customer_name": row.customer_name,
            "customer_mobile": row.customer_mobile,
            "customer_email": row.customer_email,
            "customer_address": row.customer_address,
            "source_type": "complaint",
        })
    return results[:20]


@router.get("/my-assigned-units", response_model=list[EngineerAssignedUnitGroup])
def my_assigned_units(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not _is_engineer(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only engineers can view assigned units")
    return [EngineerAssignedUnitGroup(**group) for group in build_engineer_unit_groups(db, user.id)]


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    backfill_unit_verification_from_service(db, service)
    backfill_unit_statuses(db, service)
    sync_aggregate_service_status(db, service)
    _mark_service_notifications_read(db, service, user)
    old_status = service.status
    if sync_document_workflow_status(db, service):
        _log_status(
            db,
            service,
            action="Document Workflow Synced",
            user=user,
            old_status=old_status,
            new_status=service.status,
        )
    db.commit()
    return _hydrate_service(db, service)


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, body: ServiceUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not (_is_service_team(user) or (_is_call_center(user) and service.created_by == user.id)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot update this service request")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/identify-customer", response_model=ServiceOut)
def identify_customer(service_id: int, body: ServiceIdentifyCustomer, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can identify customer context")
    order = db.get(Order, body.order_id) if body.order_id else None
    item = db.get(OrderItem, body.order_item_id) if body.order_item_id else None
    if item and order is None:
        order = db.get(Order, item.order_id)
    if item and order and item.order_id != order.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order item does not belong to selected order")
    if order:
        # Customer context only — order is linked when service team runs verify-order (loads units).
        service.customer_name = order.customer_name or service.customer_name
        service.customer_mobile = order.customer_contact or service.customer_mobile
        service.customer_email = order.customer_email or service.customer_email
        service.customer_address = order.customer_address or service.customer_address
    elif any([body.customer_name, body.customer_mobile, body.customer_email, body.customer_address]):
        service.customer_name = body.customer_name or service.customer_name
        service.customer_mobile = body.customer_mobile or service.customer_mobile
        service.customer_email = body.customer_email or service.customer_email
        service.customer_address = body.customer_address or service.customer_address
    if item:
        service.order_item_id = item.id
        if not service.serial_no:
            service.serial_no = item.serial_no or item.serial_no_2
        context = _derive_service_context(db, item)
        service.warranty_status = context["warranty_status"]
        service.service_type = context["service_type"]
        docs = _required_documents(db, service.service_type, service.warranty_status, service.query_type)
        service.requires_documents = bool(docs)
        service.ask_for_documents = bool(docs)
    old_status = service.status
    if service.status == "New":
        service.status = "Service Team Review"
        service.status_date = _now()
    service.customer_identified_at = _now()
    _log_status(db, service, action="Customer Identified", user=user, old_status=old_status, new_status=service.status, metadata={"order_id": service.order_id, "order_item_id": service.order_item_id})
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/restart-team-review", response_model=ServiceOut)
def restart_service_team_review(
    service_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can restart service team review")
    if service.status != "Service Team Review":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Restart is only available while the request is in Service Team Review",
        )
    if not customer_documents_approved(db, service):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Approve all required customer documents before restarting this step",
        )
    old_status = service.status
    on_enter_service_team_review(db, service)
    service.status = "Service Team Review"
    service.status_date = _now()
    _log_status(
        db,
        service,
        action="Service Team Review Restarted",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks="Cleared order verification and assignment; documents kept.",
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/verify-order", response_model=ServiceOut)
def verify_order_for_service_request(
    service_id: int,
    body: ServiceVerifyOrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin/Indcool Service can verify orders")
    _ensure_order_workflow_unlocked(db, service)
    if not body.order_id and not body.order_no:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order number or order id is required")

    old_status = service.status
    order = verify_order_for_service(
        db,
        service,
        order_id=body.order_id,
        order_no=body.order_no,
        serial_no=body.serial_no,
    )
    if service.order_item_id:
        item = db.get(OrderItem, service.order_item_id)
        if item is not None:
            context = _derive_service_context(db, item)
            service.warranty_status = context["warranty_status"]
            service.service_type = context["service_type"]
    _log_status(
        db,
        service,
        action="Order Verified",
        user=user,
        old_status=old_status,
        new_status=service.status,
        metadata={
            "order_id": order.id,
            "order_no": order.order_no,
            "serial_no": service.serial_no,
        },
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.get("/{service_id}/units", response_model=list[ServiceRequestUnitOut])
def list_service_units(
    service_id: int,
    item_code: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    engineer_filter = user.id if _is_engineer(user) else None
    return [
        ServiceRequestUnitOut(**row)
        for row in build_unit_rows(db, service.id, item_code=item_code, engineer_id=engineer_filter)
    ]


@router.post("/{service_id}/assign-units", response_model=ServiceOut)
def assign_service_units(
    service_id: int,
    body: ServiceAssignUnitsIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin/Indcool Service can assign units")
    _ensure_order_workflow_unlocked(db, service)

    completion_code, should_send_happy_code = issue_completion_code(service)

    units = assign_units_to_engineer(
        db,
        service,
        body.unit_ids,
        body.engineer_id,
        user.id,
        body.remarks,
        body.billing_type,
    )
    order = db.get(Order, service.order_id) if service.order_id else None
    engineer = db.get(User, body.engineer_id)
    unit_rows = build_unit_rows(db, service.id)
    assigned_rows = [row for row in unit_rows if row["id"] in body.unit_ids]
    _log_status(
        db,
        service,
        action="Units Assigned",
        user=user,
        old_status=service.status,
        new_status=service.status,
        remarks=body.remarks,
        metadata={
            "engineer_id": body.engineer_id,
            "unit_ids": body.unit_ids,
            "quantity": len(units),
        },
    )
    db.commit()
    db.refresh(service)

    if engineer and engineer.email:
        background_tasks.add_task(
            send_service_unit_assignment_email,
            to=engineer.email,
            engineer_name=engineer.name,
            request_no=service.request_no,
            order_no=order.order_no if order else None,
            customer_name=service.customer_name,
            customer_address=service.customer_address,
            problem_description=service.problem_description,
            assigned_units=assigned_rows,
        )

    if should_send_happy_code:
        notify_customer_happy_code(
            background_tasks,
            service,
            completion_code=completion_code,
        )

    return _hydrate_service(db, service)


@router.post("/{service_id}/units/add-by-serial", response_model=ServiceOut)
def add_service_unit_by_serial_endpoint(
    service_id: int,
    body: ServiceAddUnitBySerialIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add an installation-complete serial to this request and assign it to an engineer (bulk visit workflow)."""
    service = _load_visible_service(db, service_id, user)
    _ensure_order_workflow_unlocked(db, service)

    if _is_engineer(user):
        if not _engineer_can_work_on_service(db, service, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        engineer_id = user.id
        assigned_by = user.id
    elif _is_service_team(user):
        engineer_id = body.engineer_id or service.assigned_engineer_id
        if engineer_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select an engineer or assign the service request first")
        assigned_by = user.id
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot add serials to this service request")

    old_status = service.status
    unit = add_service_unit_by_serial(
        db,
        service,
        serial_no=body.serial_no,
        engineer_id=engineer_id,
        assigned_by_user_id=assigned_by,
        billing_type=body.billing_type,
        remarks=body.remarks,
    )
    if unit.assigned_engineer_id is None:
        assign_units_to_engineer(
            db,
            service,
            [unit.id],
            engineer_id,
            assigned_by,
            body.remarks,
            body.billing_type,
        )
        db.refresh(unit)
    _log_status(
        db,
        service,
        action="Unit Added By Serial",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=body.remarks,
        metadata={"unit_id": unit.id, "serial_no": body.serial_no, "engineer_id": engineer_id},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/assign", response_model=ServiceOut)
def assign_service(
    service_id: int,
    body: ServiceAssignmentIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can assign requests")
    active_assignment = db.scalar(
        select(ServiceAssignment)
        .where(ServiceAssignment.service_request_id == service.id, ServiceAssignment.is_active == True)
        .order_by(desc(ServiceAssignment.assigned_at))
    )
    if active_assignment is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This request is already assigned. Cancel the current assignment before reassigning.")
    old_status = service.status
    if body.assignee_type == "engineer":
        engineer = db.get(User, body.assignee_id)
        if engineer is None or engineer.deleted_at is not None or not engineer.is_active or _role(engineer) != "engineer":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected engineer is not active")
        service.assigned_engineer_id = engineer.id
        service.assigned_vendor_id = None
        completion_code, _ = issue_completion_code(service, regenerate=True)
    else:
        vendor = db.get(Vendor, body.assignee_id)
        if vendor is None or vendor.deleted_at is not None or not vendor.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected vendor is not active")
        service.assigned_vendor_id = vendor.id
        service.assigned_engineer_id = None
        clear_completion_code(service)
    db.query(ServiceAssignment).filter(ServiceAssignment.service_request_id == service.id, ServiceAssignment.is_active == True).update({ServiceAssignment.is_active: False}, synchronize_session=False)
    db.add(
        ServiceAssignment(
            service_request_id=service.id,
            assignee_type=body.assignee_type,
            assignee_user_id=service.assigned_engineer_id if body.assignee_type == "engineer" else None,
            assignee_vendor_id=service.assigned_vendor_id if body.assignee_type == "vendor" else None,
            assigned_by=user.id,
            assigned_at=_now(),
            remarks=body.remarks,
            is_active=True,
        )
    )
    if service.status in {"New", "Service Team Review", "Rejected"}:
        service.status = "Assigned"
        service.status_date = _now()
    _log_status(db, service, action="Assigned", user=user, old_status=old_status, new_status=service.status, remarks=body.remarks, metadata={"assignee_type": body.assignee_type, "assignee_id": body.assignee_id})
    if body.assignee_type == "engineer" and service.complaint_id:
        complaint = db.get(Complaint, service.complaint_id)
        if complaint is not None and complaint.deleted_at is None:
            complaint.assigned_engineer = service.assigned_engineer_id
    db.commit()
    db.refresh(service)
    order = db.get(Order, service.order_id) if service.order_id else None
    if body.assignee_type == "engineer":
        engineer = db.get(User, body.assignee_id)
        if engineer is not None:
            notify_engineer_service_assigned(
                background_tasks,
                engineer=engineer,
                service=service,
                order_no=order.order_no if order else None,
                remarks=body.remarks,
            )
            notify_customer_happy_code(
                background_tasks,
                service,
                completion_code=completion_code,
            )
    else:
        vendor = db.get(Vendor, body.assignee_id)
        if vendor is not None:
            notify_vendor_service_assigned(
                background_tasks,
                vendor=vendor,
                service=service,
                remarks=body.remarks,
            )
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=body.remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/assignment-cancel", response_model=ServiceOut)
def cancel_assignment(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    vendor = _active_vendor_for_user(db, user) if _is_vendor(user) else None
    if not _is_service_team(user):
        if _is_engineer(user):
            if not _engineer_can_work_on_service(db, service, user):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        elif _is_vendor(user):
            if vendor is None or service.assigned_vendor_id != vendor.id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel assignments")

    active_assignments = db.scalars(
        select(ServiceAssignment).where(
            ServiceAssignment.service_request_id == service.id,
            ServiceAssignment.is_active == True,
        )
    ).all()
    if not active_assignments and service.assigned_engineer_id is None and service.assigned_vendor_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This request does not have an active assignment")

    for assignment in active_assignments:
        assignment.is_active = False

    old_status = service.status
    service.assigned_engineer_id = None
    service.assigned_vendor_id = None
    clear_completion_code(service)
    service.status = "Service Team Review"
    service.status_date = _now()
    _log_status(
        db,
        service,
        action="Assignment Cancelled",
        user=user,
        old_status=old_status,
        new_status=service.status,
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/units/billing", response_model=ServiceOut)
def set_service_unit_billing(
    service_id: int,
    body: ServiceUnitBillingIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool Service can set billing")
    _ensure_order_workflow_unlocked(db, service)

    old_status = service.status
    if body.unit_id is None:
        apply_service_billing_choice(db, service, body.billing_type)
        action = "Service Billing Updated"
        metadata = {"billing_type": body.billing_type}
    else:
        unit = db.get(ServiceRequestUnit, body.unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found on this service request")
        if (unit.unit_status or "") in BILLING_LOCKED_UNIT_STATUSES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Billing cannot be changed after payment is completed or the unit is closed",
            )
        order_item = db.get(OrderItem, unit.order_item_id) if unit.order_item_id else None
        if order_item is None and unit.serial_no:
            order_item = _find_order_item_by_serial(db, unit.serial_no.strip())
        apply_unit_billing_choice(db, unit, body.billing_type, order_item=order_item)
        sync_service_request_from_units(db, service, engineer_id=unit.assigned_engineer_id)
        action = "Unit Billing Updated"
        metadata = {"unit_id": unit.id, "serial_no": unit.serial_no, "billing_type": body.billing_type}

    _log_status(
        db,
        service,
        action=action,
        user=user,
        old_status=old_status,
        new_status=service.status,
        metadata=metadata,
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/verify-serial", response_model=ServiceOut)
def verify_serial(service_id: int, body: ServiceSerialVerifyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot verify serials")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    old_status = service.status
    engineer_id = user.id if _is_engineer(user) else None
    work_units = list_work_units(db, service.id, engineer_id=engineer_id)

    if body.unit_id is not None:
        unit = db.get(ServiceRequestUnit, body.unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found on this service request")
        verify_unit_serial(
            db,
            service,
            unit,
            user,
            _derive_service_context,
            _find_order_item_by_serial,
            serial_no=body.serial_no,
        )
    elif work_units:
        serial_no = (body.serial_no or "").strip()
        if not serial_no:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number or unit id is required")
        matching = [unit for unit in work_units if serial_matches_unit(unit, serial_no)]
        if not matching:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial does not match any of your assigned units")
        verify_unit_serial(
            db,
            service,
            matching[0],
            user,
            _derive_service_context,
            _find_order_item_by_serial,
            serial_no=serial_no,
        )
    else:
        serial_no = (body.serial_no or "").strip()
        if not serial_no:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required")
        item = _find_order_item_by_serial(db, serial_no)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found")
        context = _derive_service_context(db, item)
        order = context["order"]
        service.serial_no = serial_no
        service.order_item_id = item.id
        service.order_id = order.id if order else service.order_id
        service.warranty_status = context["warranty_status"]
        service.service_type = context["service_type"]
        docs = _required_documents(db, service.service_type, service.warranty_status, service.query_type)
        service.requires_documents = bool(docs)
        service.ask_for_documents = bool(docs)
        if service.status in {"Assigned", "Engineer Visit"}:
            service.status = "Serial Verified"
            service.status_date = _now()

    _log_status(
        db,
        service,
        action="Serial Verified",
        user=user,
        old_status=old_status,
        new_status=service.status,
        metadata={"serial_no": body.serial_no, "unit_id": body.unit_id, "service_type": service.service_type, "warranty_status": service.warranty_status},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/serial-verification-review", response_model=ServiceOut)
def review_serial_verification(
    service_id: int,
    body: ServiceSerialReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool Service can review serial verification")
    unit = db.get(ServiceRequestUnit, body.unit_id)
    if unit is None or unit.service_request_id != service.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found on this service request")
    if unit.unit_status != "Serial Verification Pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This serial is not awaiting verification review")
    decision = body.decision.strip().lower()
    if decision not in {"approve", "reject", "override"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decision must be Approve, Reject, or Override")
    old_status = service.status
    if decision == "reject":
        unit.serial_verified_at = None
        unit.unit_status = "Assigned"
        action = "Serial Verification Rejected"
    else:
        serial_no = (body.serial_no or unit.serial_no or "").strip()
        serial_no_2 = (body.serial_no_2 or unit.serial_no_2 or "").strip() or None
        if not serial_no:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required")

        order_id = service.order_id
        if order_id is None:
            item_row = db.get(ServiceRequestItem, unit.service_request_item_id)
            order_id = item_row.order_id if item_row else None
        if order_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service request must be linked to an order before serial approval")

        template_item = db.get(OrderItem, unit.order_item_id)
        item = _find_order_item_by_serial(db, serial_no)
        if item is None and order_id:
            item = find_order_item_by_serial_on_order(db, order_id, serial_no, serial_no_2)
        if item is None and body.associate_serial_with_order:
            item = associate_serial_with_service_order(
                db,
                order_id=order_id,
                serial_no=serial_no,
                serial_no_2=serial_no_2,
                template_item=template_item,
            )
        elif item is None and decision == "override":
            item = associate_serial_with_service_order(
                db,
                order_id=order_id,
                serial_no=serial_no,
                serial_no_2=serial_no_2,
                template_item=template_item,
            )
        elif item is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Serial number not found in order records. Reject, override with a corrected serial, or associate with order.",
            )

        if decision == "override" and item.order_id == order_id:
            item.serial_no = serial_no
            if serial_no_2:
                item.serial_no_2 = serial_no_2

        context = _derive_service_context(db, item)
        unit.serial_no = serial_no
        unit.serial_no_2 = serial_no_2
        unit.order_item_id = item.id
        unit.serial_verified_at = datetime.now(timezone.utc)
        if body.billing_type:
            apply_unit_billing_choice(db, unit, body.billing_type, order_item=item)
        else:
            unit.warranty_status = context["warranty_status"]
            unit.service_type = context["service_type"]
        unit.unit_status = "Serial Verified"
        action = "Serial Verification Approved" if decision == "approve" else "Serial Override Approved"
    sync_service_request_from_units(db, service, engineer_id=unit.assigned_engineer_id)
    _log_status(
        db,
        service,
        action=action,
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=body.remarks,
        metadata={"unit_id": unit.id, "serial_no": unit.serial_no, "decision": decision},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/verify-serials-bulk", response_model=ServiceOut)
def verify_serials_bulk(
    service_id: int,
    body: ServiceBulkSerialVerifyIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot verify serials")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    old_status = service.status
    verified = bulk_verify_units(
        db,
        service,
        user,
        _derive_service_context,
        _find_order_item_by_serial,
        unit_ids=body.unit_ids,
    )
    _log_status(
        db,
        service,
        action="Serials Verified (Bulk)",
        user=user,
        old_status=old_status,
        new_status=service.status,
        metadata={"unit_ids": [unit.id for unit in verified]},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/observations", response_model=ServiceOut)
def submit_observation(service_id: int, body: ServiceObservationIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only engineer or vendor can submit observation")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    old_status = service.status
    engineer_id = user.id if _is_engineer(user) else None
    work_units = list_work_units(db, service.id, engineer_id=engineer_id)

    if body.unit_id is not None:
        unit = db.get(ServiceRequestUnit, body.unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found on this service request")
        submit_unit_observation(db, service, unit, user, body, _json_dump)
    elif work_units:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select a unit (serial row) for this observation")
    else:
        if service.status == "Pending Service Approval":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Observation is already submitted. Cancel it before submitting again.")
        observation = ServiceObservation(
            service_request_id=service.id,
            submitted_by_user_id=user.id,
            serial_no=service.serial_no,
            warranty_status=service.warranty_status,
            service_type=service.service_type,
            problem_found=body.problem_found,
            observation=body.observation,
            recommended_action=body.recommended_action,
            parts_required_json=_json_dump(body.parts_required),
            estimated_service_charge=body.estimated_service_charge,
            estimated_parts_charge=body.estimated_parts_charge,
            remarks=body.remarks,
            submitted_at=_now(),
        )
        db.add(observation)
        service.status = "Pending Service Approval"
        service.status_date = _now()

    _log_status(db, service, action="Observation Submitted", user=user, old_status=old_status, new_status=service.status, remarks=body.remarks)
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/observations/bulk", response_model=ServiceOut)
def submit_observations_bulk(
    service_id: int,
    body: ServiceBulkObservationsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only engineer or vendor can submit observations")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    old_status = service.status
    for item in body.observations:
        if item.unit_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "unit_id is required for each observation row")
    created = bulk_submit_observations(db, service, user, body.observations, _json_dump)
    _log_status(
        db,
        service,
        action="Observations Submitted (Bulk)",
        user=user,
        old_status=old_status,
        new_status=service.status,
        metadata={"unit_ids": [row.service_request_unit_id for row in created]},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/observations/cancel", response_model=ServiceOut)
def cancel_observation(
    service_id: int,
    body: ServiceObservationCancelIn = Body(default_factory=ServiceObservationCancelIn),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel observations")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    engineer_id = user.id if _is_engineer(user) else None
    unit_id = body.unit_id
    old_status = service.status

    if unit_id is not None:
        observation = db.scalar(
            select(ServiceObservation).where(
                ServiceObservation.service_request_id == service.id,
                ServiceObservation.service_request_unit_id == unit_id,
            )
        )
        if observation is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No observation found for this unit")
        linked_approval = db.scalar(select(ServiceApproval).where(ServiceApproval.observation_id == observation.id))
        if linked_approval is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Observation already has an approval decision")
        db.delete(observation)
        sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
    else:
        if service.status != "Pending Service Approval":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only pending observations can be cancelled")

        latest_observation = db.scalar(
            select(ServiceObservation)
            .where(ServiceObservation.service_request_id == service.id)
            .order_by(desc(ServiceObservation.submitted_at))
        )
        if latest_observation is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No observation found to cancel")

        linked_approval = db.scalar(select(ServiceApproval).where(ServiceApproval.observation_id == latest_observation.id))
        if linked_approval is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Observation already has an approval decision")

        db.delete(latest_observation)
        work_units = list_work_units(db, service.id, engineer_id=engineer_id)
        if work_units:
            sync_service_request_from_units(db, service, engineer_id=engineer_id if engineer_id else None)
        else:
            service.status = "Serial Verified"
            service.status_date = _now()

    _log_status(
        db,
        service,
        action="Observation Cancelled",
        user=user,
        old_status=old_status,
        new_status=service.status,
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/approval", response_model=ServiceOut)
def service_approval(
    service_id: int,
    body: ServiceApprovalIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can approve service")
    if body.decision == "Reject" and not body.remarks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Remarks are mandatory when rejecting")

    old_status = service.status
    work_units = list_work_units(db, service.id)

    if body.unit_id is not None:
        unit = db.get(ServiceRequestUnit, body.unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        observations = observations_for_service(db, service.id)
        observation = observations.get(unit.id)
        if observation is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No observation found for this unit")
        approve_unit(db, service, unit, user, body.decision, body.remarks, observation)
    elif work_units:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Approve each serial row individually or use bulk approval for all pending units",
        )
    else:
        if service.status != "Pending Service Approval":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Approval is enabled only after observation is submitted")
        latest_observation = db.scalar(
            select(ServiceObservation)
            .where(ServiceObservation.service_request_id == service.id)
            .order_by(desc(ServiceObservation.submitted_at))
        )
        approval = ServiceApproval(
            service_request_id=service.id,
            observation_id=latest_observation.id if latest_observation else None,
            decision=body.decision,
            remarks=body.remarks,
            approved_by=user.id,
            approved_at=_now(),
        )
        db.add(approval)
        service.status = "Approved for Service" if body.decision == "Approve" else "Rejected"
        service.status_date = _now()
        if body.decision == "Approve":
            service.approved_at = _now()

    _log_status(db, service, action="Service Approved" if body.decision == "Approve" else "Service Rejected", user=user, old_status=old_status, new_status=service.status, remarks=body.remarks)
    db.commit()
    db.refresh(service)
    after_service_approval(background_tasks, db, service, decision=body.decision, remarks=body.remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/approval/bulk", response_model=ServiceOut)
def service_approval_bulk(
    service_id: int,
    body: ServiceBulkApprovalIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can approve service")
    if body.decision == "Reject" and not body.remarks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Remarks are mandatory when rejecting")

    old_status = service.status
    approved = bulk_approve_units(db, service, user, body.decision, body.remarks, body.unit_ids)
    _log_status(
        db,
        service,
        action="Service Approved (Bulk)" if body.decision == "Approve" else "Service Rejected (Bulk)",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=body.remarks,
        metadata={"unit_ids": [row.service_request_unit_id for row in approved]},
    )
    db.commit()
    db.refresh(service)
    after_service_approval(background_tasks, db, service, decision=body.decision, remarks=body.remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/approval/cancel", response_model=ServiceOut)
def cancel_service_approval(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can cancel approval")
    if service.status not in {"Approved for Service", "Rejected"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only the current approval decision can be cancelled")

    latest_approval = db.scalar(
        select(ServiceApproval)
        .where(ServiceApproval.service_request_id == service.id)
        .order_by(desc(ServiceApproval.approved_at))
    )
    if latest_approval is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No approval decision found to cancel")

    db.delete(latest_approval)
    old_status = service.status
    service.status = "Pending Service Approval"
    service.status_date = _now()
    service.approved_at = None
    _log_status(db, service, action="Approval Cancelled", user=user, old_status=old_status, new_status=service.status)
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/completion", response_model=ServiceOut)
async def complete_service(
    service_id: int,
    background_tasks: BackgroundTasks,
    unit_id: int | None = Form(None),
    work_performed: str | None = Form(None),
    parts_replaced: str | None = Form(None),
    service_notes: str | None = Form(None),
    service_date: date | None = Form(None),
    old_part_serial_no: str | None = Form(None),
    new_part_serial_no: str | None = Form(None),
    final_amount: float | None = Form(None),
    completion_remarks: str | None = Form(None),
    completion_code: str | None = Form(None),
    proof_document: UploadFile | None = File(None),
    completion_status: str = Form("Service Completed"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only engineer or vendor can complete service")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")
    allowed_completion_statuses = {"Service Completed", "Waiting for Part", "Customer Not Available"}
    if completion_status not in allowed_completion_statuses:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid completion status")
    is_completed = completion_status == "Service Completed"
    if is_completed and (proof_document is None or not proof_document.filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Completion proof document is required")
    try:
        verified_code = validate_engineer_completion_code(service, completion_code) if is_completed else None
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    proof_path = await save_upload(proof_document, module="services") if proof_document and proof_document.filename else None
    old_status = service.status

    completion_body = ServiceCompletionIn(
        unit_id=unit_id,
        work_performed=work_performed,
        parts_replaced=_json_load(parts_replaced, []),
        service_notes=service_notes,
        service_date=service_date or date.today(),
        old_part_serial_no=old_part_serial_no,
        new_part_serial_no=new_part_serial_no,
        final_amount=final_amount,
        completion_remarks=completion_remarks,
        engineer_completion_code=verified_code,
        completion_status=completion_status,
    )

    if unit_id is not None:
        unit = db.get(ServiceRequestUnit, unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        completion = complete_unit(
            db,
            service,
            unit,
            user,
            _is_engineer(user),
            _is_vendor(user),
            service.assigned_vendor_id if _is_vendor(user) else None,
            completion_body,
            proof_path,
            _json_dump,
            _json_load,
        )
    elif list_work_units(db, service.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unit_id is required when completing a specific serial")
    else:
        if service.status not in {"Approved for Service", "Service In Progress"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Service can be completed only after approval")
        completion = ServiceCompletion(
            service_request_id=service.id,
            performed_by_type="engineer" if _is_engineer(user) else "vendor",
            performed_by_user_id=user.id if _is_engineer(user) else None,
            performed_by_vendor_id=service.assigned_vendor_id if _is_vendor(user) else None,
            work_performed=work_performed,
            parts_replaced_json=_json_dump(_json_load(parts_replaced, [])),
            service_notes=service_notes,
            service_date=service_date or date.today(),
            old_part_serial_no=old_part_serial_no,
            new_part_serial_no=new_part_serial_no,
            customer_acknowledgement_path=proof_path,
            final_amount=final_amount,
            completion_remarks=completion_remarks,
            engineer_completion_code=verified_code,
            completed_at=_now(),
        )
        db.add(completion)
        service.status = "Completion Pending Approval" if completion_status == "Service Completed" else completion_status
        service.status_date = _now()
        if is_completed:
            service.completed_at = _now()
        if service.order_item_id:
            item = db.get(OrderItem, service.order_item_id)
            if item is not None and service.service_type == "Free Service":
                item.service_consume_count = (item.service_consume_count or 0) + 1

    _log_status(
        db,
        service,
        action=completion_status,
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=completion_remarks,
        metadata={"proof_document": proof_path},
    )
    _write_service_summary_to_serial_history(db, service, completion, user)
    db.commit()
    db.refresh(service)
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=completion_remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/completion/cancel", response_model=ServiceOut)
def cancel_service_completion(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel service completion")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")
    if service.status == "Service Completed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cancel payment request before cancelling completion")
    if service.status != "Completion Pending Approval":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a pending or submitted completion can be cancelled")

    latest_completion = db.scalar(
        select(ServiceCompletion)
        .where(ServiceCompletion.service_request_id == service.id)
        .order_by(desc(ServiceCompletion.completed_at))
    )
    if latest_completion is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No completion found to cancel")

    db.delete(latest_completion)
    old_status = service.status
    service.status = "Approved for Service"
    service.status_date = _now()
    service.completed_at = None
    if service.order_item_id:
        item = db.get(OrderItem, service.order_item_id)
        if item is not None and service.service_type == "Free Service" and (item.service_consume_count or 0) > 0:
            item.service_consume_count = (item.service_consume_count or 0) - 1
    _log_status(db, service, action="Completion Cancelled", user=user, old_status=old_status, new_status=service.status)
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/completion-approval", response_model=ServiceOut)
def review_completion(
    service_id: int,
    unit_id: int | None = Form(None),
    decision: str = Form(...),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_workflow_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool Service can review completion")
    old_status = service.status
    unit = db.get(ServiceRequestUnit, unit_id) if unit_id is not None else None
    if unit_id is not None and (unit is None or unit.service_request_id != service.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
    if unit is None and service.status != "Completion Pending Approval":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This completion is not awaiting approval")
    if unit is not None and unit.unit_status != "Completion Pending Approval":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This completion is not awaiting approval")
    if decision.strip().lower() == "approve":
        if unit is not None:
            unit.unit_status = "Service Completed"
        else:
            service.status = "Service Completed"
        action = "Completion Approved"
    elif decision.strip().lower() == "reject":
        if unit is not None:
            completion = db.scalar(
                select(ServiceCompletion).where(
                    ServiceCompletion.service_request_id == service.id,
                    ServiceCompletion.service_request_unit_id == unit.id,
                )
            )
            if completion is not None:
                db.delete(completion)
            unit.unit_status = "Approved for Service"
        else:
            service.status = "Approved for Service"
        action = "Completion Rejected"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decision must be Approve or Reject")
    sync_aggregate_service_status(db, service)
    _log_status(db, service, action=action, user=user, old_status=old_status, new_status=service.status, remarks=remarks, metadata={"unit_id": unit_id})
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/payment-request", response_model=ServiceOut)
async def raise_payment_request(
    service_id: int,
    unit_id: int | None = Form(None),
    customer_charge_amount: float | None = Form(None),
    settlement_service_amount: float | None = Form(None),
    settlement_parts_amount: float | None = Form(None),
    total_requested_amount: float | None = Form(None),
    payment_type: str | None = Form(None),
    remarks: str | None = Form(None),
    qr_code: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot raise payment request")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")
    normalized_payment_type = (payment_type or "").strip()
    if normalized_payment_type not in {"Cash", "UPI"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")
    if normalized_payment_type == "UPI" and (qr_code is None or not qr_code.filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required when payment type is UPI")
    qr_path = None
    if qr_code is not None and qr_code.filename:
        qr_path = await save_upload(qr_code, module="services")
    old_status = service.status
    requested_by_type = "service_team" if _is_service_team(user) else "engineer" if _is_engineer(user) else "vendor"
    has_unit_workflow = bool(list_work_units(db, service.id))

    if unit_id is not None:
        unit = db.get(ServiceRequestUnit, unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        payment_request = raise_payment_for_unit(
            db,
            service,
            unit,
            user,
            requested_by_type,
            service.assigned_vendor_id if _is_vendor(user) else None,
            normalized_payment_type,
            qr_path,
            customer_charge_amount,
            settlement_service_amount,
            settlement_parts_amount,
            total_requested_amount,
            remarks,
        )
    elif has_unit_workflow:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unit_id is required when raising payment for a specific serial")
    else:
        if service.status != "Service Completed":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment request is enabled only after service completion")
        payment_request = ServicePaymentRequest(
            service_request_id=service.id,
            requested_by_type=requested_by_type,
            requested_by_user_id=user.id if requested_by_type != "vendor" else None,
            requested_by_vendor_id=service.assigned_vendor_id if requested_by_type == "vendor" else None,
            service_type=service.service_type,
            customer_charge_amount=customer_charge_amount,
            settlement_service_amount=settlement_service_amount,
            settlement_parts_amount=settlement_parts_amount,
            total_requested_amount=total_requested_amount,
            payment_type=normalized_payment_type,
            payment_qr_code_path=qr_path,
            remarks=remarks,
            status="Requested",
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(payment_request)
        service.status = "Payment Requested"
        service.status_date = _now()

    _log_status(
        db,
        service,
        action="Payment Requested",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=remarks,
        metadata={"payment_type": normalized_payment_type, "payment_qr_code_path": qr_path},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/payment-request/cancel", response_model=ServiceOut)
def cancel_payment_request(
    service_id: int,
    unit_id: int | None = Form(None),
    remarks: str | None = Form(None),
    reject: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not (_is_engineer(user) or _is_vendor(user) or _is_service_team(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot cancel payment request")
    if reject and not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can reject payment requests")
    if reject and not (remarks or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Remarks are required when rejecting a payment request")
    if _is_engineer(user) and not _engineer_can_work_on_service(db, service, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
    if _is_vendor(user):
        vendor = _active_vendor_for_user(db, user)
        if vendor is None or service.assigned_vendor_id != vendor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your vendor")

    old_status = service.status
    action = "Payment Rejected" if reject else "Payment Request Cancelled"

    if unit_id is not None:
        unit = db.get(ServiceRequestUnit, unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        cancel_payment_for_unit(db, service, unit)
    else:
        if service.status != "Payment Requested":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only active payment requests can be cancelled")
        latest_payment = db.scalar(
            select(ServicePaymentRequest)
            .where(ServicePaymentRequest.service_request_id == service.id)
            .order_by(desc(ServicePaymentRequest.created_at))
        )
        if latest_payment is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment request found to cancel")
        db.delete(latest_payment)
        service.status = "Service Completed"
        service.status_date = _now()

    _log_status(
        db,
        service,
        action=action,
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=remarks,
        metadata={"unit_id": unit_id} if unit_id is not None else None,
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/payment-approval", response_model=ServiceOut)
def approve_service_payment(
    service_id: int,
    body: ServicePaymentCompleteIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can approve payment")
    if body.unit_id is None and service.status != "Payment Requested":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment can be approved only after a payment request is raised")
    if body.approved_amount < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Approved amount cannot be negative")

    if body.unit_id is not None:
        unit = db.get(ServiceRequestUnit, body.unit_id)
        if unit is None or unit.service_request_id != service.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
        latest_payment = db.scalar(
            select(ServicePaymentRequest)
            .where(
                ServicePaymentRequest.service_request_id == service.id,
                ServicePaymentRequest.service_request_unit_id == unit.id,
            )
            .order_by(desc(ServicePaymentRequest.created_at))
        )
    else:
        if list_work_units(db, service.id) and service.status == "Service In Progress":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "unit_id is required to approve payment for a specific serial")
        if service.status != "Payment Requested":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment can be approved only after a payment request is raised")
        latest_payment = db.scalar(
            select(ServicePaymentRequest)
            .where(ServicePaymentRequest.service_request_id == service.id)
            .order_by(desc(ServicePaymentRequest.created_at))
        )

    if latest_payment is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment request found to approve")

    payment_type = body.payment_type or latest_payment.payment_type or "Cash"
    if payment_type == "UPI" and not latest_payment.payment_qr_code_path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required before approving UPI payment")

    transaction = PaymentTransaction(
        payment_type=payment_type,
        total_amount=body.approved_amount,
        request_count=1,
        recorded_by_user_id=user.id,
        engineer_user_id=service.assigned_engineer_id,
    )
    db.add(transaction)
    db.flush()

    latest_payment.status = "Processed"
    latest_payment.approved_amount = body.approved_amount
    latest_payment.processed_at = _now()
    latest_payment.processed_by_user_id = user.id
    latest_payment.payment_transaction_id = transaction.id
    latest_payment.updated_at = _now()
    if body.remarks:
        latest_payment.remarks = body.remarks

    old_status = service.status
    if latest_payment.service_request_unit_id:
        unit = db.get(ServiceRequestUnit, latest_payment.service_request_unit_id)
        if unit is not None:
            unit.unit_status = "Payment Completed"
        sync_aggregate_service_status(db, service)
    else:
        service.status = "Payment Completed"
        service.status_date = _now()

    _log_status(
        db,
        service,
        action="Payment Approved",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=body.remarks,
        metadata={"payment_request_id": latest_payment.id, "approved_amount": body.approved_amount, "payment_transaction_id": transaction.id},
    )
    completion_for_history = None
    if latest_payment.service_request_unit_id:
        completion_for_history = db.scalar(
            select(ServiceCompletion).where(
                ServiceCompletion.service_request_id == service.id,
                ServiceCompletion.service_request_unit_id == latest_payment.service_request_unit_id,
            )
        )
    else:
        completion_for_history = db.scalar(
            select(ServiceCompletion)
            .where(ServiceCompletion.service_request_id == service.id)
            .order_by(desc(ServiceCompletion.completed_at))
        )
    if completion_for_history is not None:
        write_service_completion_serial_history(
            db,
            service,
            completion_for_history,
            performed_by_user_id=completion_for_history.performed_by_user_id,
        )
    _resolve_linked_complaint_from_service(db, service, user, body.remarks)
    db.commit()
    db.refresh(service)
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=body.remarks)
    return _hydrate_service(db, service)


@router.patch("/{service_id}/payment-amount", response_model=ServiceOut)
def admin_update_service_payment_amount(
    service_id: int,
    body: AdminServicePaymentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admin can update payment amounts")
    service = _load_visible_service(db, service_id, user)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment fields provided")

    latest_payment = db.scalar(
        select(ServicePaymentRequest)
        .where(ServicePaymentRequest.service_request_id == service.id)
        .order_by(desc(ServicePaymentRequest.created_at))
    )
    if latest_payment is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payment request found to update")

    for amount_field in (
        "approved_amount",
        "total_requested_amount",
        "customer_charge_amount",
        "settlement_service_amount",
        "settlement_parts_amount",
    ):
        if amount_field in data and data[amount_field] is not None and data[amount_field] < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount cannot be negative")

    if "payment_type" in data and data["payment_type"] is not None:
        normalized = (data["payment_type"] or "").strip()
        if normalized not in {"Cash", "UPI"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")
        data["payment_type"] = normalized

    for field, value in data.items():
        setattr(latest_payment, field, value)
    latest_payment.updated_at = _now()
    if "approved_amount" in data and data["approved_amount"] is not None:
        latest_payment.processed_at = _now()
        latest_payment.processed_by_user_id = user.id
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/close", response_model=ServiceOut)
def close_service_request(
    service_id: int,
    background_tasks: BackgroundTasks,
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can close service requests")
    if service.status == "Closed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This service request is already closed")

    old_status = service.status
    close_service_with_units(db, service)
    sync_aggregate_service_status(db, service)
    if service.status != "Closed":
        _enforce_transition(service.status, "Closed")
        service.status = "Closed"
    service.status_date = _now()
    service.closed_at = _now()
    _log_status(
        db,
        service,
        action="Service Request Closed",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=remarks,
    )
    _resolve_linked_complaint_from_service(db, service, user, remarks)
    db.commit()
    db.refresh(service)
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/reopen-to-engineer", response_model=ServiceOut)
def reopen_service_for_engineer(
    service_id: int,
    background_tasks: BackgroundTasks,
    remarks: str | None = Form(None),
    unit_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can reopen service requests")
    if not remarks or not remarks.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Remarks are required when reopening to engineer")

    old_status = service.status
    reopen_service_to_engineer(db, service, unit_id=unit_id)
    service.status_date = _now()
    _log_status(
        db,
        service,
        action="Reopened to Engineer",
        user=user,
        old_status=old_status,
        new_status=service.status,
        remarks=remarks.strip(),
        metadata={"unit_id": unit_id} if unit_id else None,
    )
    db.commit()
    db.refresh(service)
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=remarks)
    return _hydrate_service(db, service)


@router.post("/{service_id}/status", response_model=ServiceOut)
def update_service_status(
    service_id: int,
    background_tasks: BackgroundTasks,
    new_status: str = Form(...),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_workflow_admin(user):
        _enforce_transition(service.status, new_status)
    elif new_status not in SERVICE_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
    old_status = service.status
    entering_team_review = (
        new_status == "Service Team Review"
        and (
            new_status == old_status
            or old_status == "Admin Review Document"
            or service_workflow_is_revert(old_status, new_status)
        )
    )
    if _is_workflow_admin(user) and entering_team_review:
        on_enter_service_team_review(db, service)
    elif _is_workflow_admin(user) and (
        service_workflow_is_revert(old_status, new_status) or new_status == old_status
    ):
        reset_service_workflow_from_status(db, service, new_status)
    align_units_to_service_status(db, service, new_status)
    service.status = new_status
    service.status_date = _now()
    if new_status == "Closed":
        service.closed_at = _now()
    _log_status(db, service, action="Status Changed", user=user, old_status=old_status, new_status=new_status, remarks=remarks)
    _resolve_linked_complaint_from_service(db, service, user, remarks)
    db.commit()
    db.refresh(service)
    after_service_status_change(background_tasks, db, service, old_status=old_status, remarks=remarks)
    return _hydrate_service(db, service)


@router.get("/{service_id}/history", response_model=list[ServiceHistoryEntry])
def service_history(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    rows = db.scalars(select(ServiceStatusLog).where(ServiceStatusLog.service_request_id == service.id).order_by(desc(ServiceStatusLog.created_at))).all()
    return [
        ServiceHistoryEntry(
            id=row.id,
            action=row.action,
            old_status=row.old_status,
            new_status=row.new_status,
            performed_by=row.performed_by,
            performed_by_name=_user_name(db, row.performed_by),
            performed_role=row.performed_role,
            remarks=row.remarks,
            metadata=_json_load(row.metadata_json, None),
            created_at=row.created_at,
        )
        for row in rows
    ]

@router.get("/{service_id}/documents", response_model=list[ServiceDocumentOut])
def list_documents(service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    rows = db.scalars(select(ServiceDocument).where(ServiceDocument.service_request_id == service.id).order_by(desc(ServiceDocument.uploaded_at))).all()
    return [_doc_out(db, row) for row in rows]


@router.post("/{service_id}/documents/upload", response_model=ServiceOut)
async def upload_document(
    service_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if _is_vendor(user) or _is_call_center(user) or _is_engineer(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Use the customer document link flow for customer documents")
    path = await save_upload(file, module="services")
    row = ServiceDocument(
        service_request_id=service.id,
        document_type=document_type,
        file_path=path,
        uploaded_by_type=_role(user),
        uploaded_by_user_id=user.id,
        uploaded_by_customer_name=None,
        status="Uploaded",
        uploaded_at=_now(),
    )
    db.add(row)
    _log_status(db, service, action="Document Uploaded", user=user, old_status=service.status, new_status=service.status, metadata={"document_type": document_type, "file_path": path})
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


@router.post("/{service_id}/documents/{document_id}/review", response_model=ServiceOut)
def review_document(service_id: int, document_id: int, body: ServiceDocumentReviewIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can review documents")
    document = db.get(ServiceDocument, document_id)
    if document is None or document.service_request_id != service.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    old_status = service.status
    document.status = body.status
    document.reviewed_by = user.id
    document.reviewed_at = _now()
    document.review_remarks = body.remarks
    new_status = service.status
    if body.status in {"Reviewed", "Approved"} and customer_documents_approved(db, service):
        if service.status == "Admin Review Document":
            _enforce_transition(service.status, "Service Team Review")
            on_enter_service_team_review(db, service)
            service.status = "Service Team Review"
            service.status_date = _now()
            new_status = service.status
    _log_status(
        db,
        service,
        action="Document Reviewed",
        user=user,
        old_status=old_status,
        new_status=new_status,
        remarks=body.remarks,
        metadata={"document_id": document_id, "document_status": body.status},
    )
    db.commit()
    db.refresh(service)
    return _hydrate_service(db, service)


def _document_link_out(db: Session, service: ServiceRequest) -> ServiceDocumentLinkOut:
    upload_url = build_public_upload_url(service.document_access_token) if service.document_access_token else ""
    return ServiceDocumentLinkOut(
        service_request_id=service.id,
        upload_url=upload_url,
        customer_email=service.customer_email,
        document_request_sent_at=service.document_request_sent_at,
        status=service.status,
    )


def _ensure_document_access_token(service: ServiceRequest) -> str:
    if not service.document_access_token:
        service.document_access_token = _generate_access_token()
        service.ask_for_documents = True
    return service.document_access_token


@router.post("/{service_id}/documents/ensure-link", response_model=ServiceDocumentLinkOut)
def ensure_document_upload_link(
    service_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can manage document upload links")
    _ensure_document_access_token(service)
    db.commit()
    db.refresh(service)
    return _document_link_out(db, service)


@router.post("/{service_id}/documents/resend-link", response_model=ServiceDocumentLinkOut)
def resend_document_upload_link(
    service_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can resend document upload links")
    if not service.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required before resending upload link")
    _ensure_document_access_token(service)
    if not service.document_request_sent_at:
        service.document_request_sent_at = _now()
    upload_url = build_public_upload_url(service.document_access_token)
    required_documents = _customer_document_types(db, service)
    background_tasks.add_task(_send_document_link_email, service, upload_url, required_documents)
    _log_status(
        db,
        service,
        action="Document Link Resent",
        user=user,
        old_status=service.status,
        new_status=service.status,
        metadata={
            "upload_url": upload_url,
            "required_documents": required_documents,
        },
    )
    db.commit()
    db.refresh(service)
    return _document_link_out(db, service)


@router.post("/{service_id}/documents/request-link", response_model=ServiceDocumentLinkOut)
def request_documents(
    service_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = _load_visible_service(db, service_id, user)
    if not _is_service_team(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Indcool Service can request documents")
    if not service.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required before sending document upload link")
    service.document_access_token = _generate_access_token()
    service.ask_for_documents = True
    service.document_request_sent_at = _now()
    upload_url = build_public_upload_url(service.document_access_token)
    required_documents = _customer_document_types(db, service)
    background_tasks.add_task(_send_document_link_email, service, upload_url, required_documents)
    _log_status(
        db,
        service,
        action="Documents Requested",
        user=user,
        old_status=service.status,
        new_status=service.status,
        metadata={
            "upload_url": upload_url,
            "required_documents": _customer_document_types(db, service),
            "requested_by_host": str(request.base_url).rstrip("/"),
        },
    )
    db.commit()
    return _document_link_out(db, service)


@router.get("/public/{token}", response_model=ServicePublicDocumentContext)
def public_upload_context(token: str, db: Session = Depends(get_db)):
    service = db.scalar(select(ServiceRequest).where(ServiceRequest.document_access_token == token, ServiceRequest.deleted_at.is_(None)))
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload link not found")
    order = db.get(Order, service.order_id) if service.order_id else None
    return ServicePublicDocumentContext(
        service_request_id=service.id,
        request_no=service.request_no,
        customer_name=service.customer_name,
        customer_email=service.customer_email,
        model_details=service.model_details,
        order_no=order.order_no if order else None,
        serial_no=service.serial_no,
        serial_no_locked=bool((service.serial_no or "").strip()),
        problem_description=service.problem_description,
        required_documents=_customer_document_types(db, service),
        status=service.status,
    )


@router.post("/public/{token}/upload", response_model=dict)
async def public_upload(
    token: str,
    document_type: str = Form(...),
    customer_name: str | None = Form(None),
    serial_no: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = db.scalar(select(ServiceRequest).where(ServiceRequest.document_access_token == token, ServiceRequest.deleted_at.is_(None)))
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload link not found")
    _validate_customer_document_upload(document_type, file)
    if serial_no and serial_no.strip() and not (service.serial_no or "").strip():
        _apply_customer_serial_to_service(db, service, serial_no)
    elif serial_no and serial_no.strip() and (service.serial_no or "").strip().lower() != serial_no.strip().lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A different serial number is already linked to this service request.",
        )
    path = await save_upload(file, module="services")
    old_status = service.status
    db.add(
        ServiceDocument(
            service_request_id=service.id,
            document_type=document_type,
            file_path=path,
            uploaded_by_type="customer",
            uploaded_by_customer_name=customer_name,
            status="Uploaded",
            uploaded_at=_now(),
        )
    )
    if service.status in {"New", "Service Team Review", "Rejected"}:
        service.status = "Admin Review Document"
        service.status_date = _now()
    _notify_service_team(
        db,
        service,
        title="Customer documents received",
        message=f"Customer uploaded {document_type} for {service.request_no}.",
        notification_type="customer_document_uploaded",
    )
    db.add(
        ServiceStatusLog(
            service_request_id=service.id,
            action="Customer Document Uploaded",
            old_status=old_status,
            new_status=service.status,
            performed_by=None,
            performed_role="customer",
            remarks=document_type,
            metadata_json=_json_dump({
                "document_type": document_type,
                "file_path": path,
                "serial_no": service.serial_no,
            }),
            created_at=_now(),
        )
    )
    db.commit()
    return {"ok": True, "service_request_id": service.id, "message": "Documents uploaded successfully"}


@router.get("/serials/lookup", response_model=SerialLookup)
def lookup_serial(serial_no: str = Query(..., min_length=1), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (_is_service_team(user) or _is_call_center(user) or _is_engineer(user) or _is_vendor(user)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot look up serials")
    item = _find_order_item_by_serial(db, serial_no)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found")
    context = _derive_service_context(db, item)
    order = context["order"]
    return SerialLookup(
        order_item_id=item.id,
        serial_no=item.serial_no or serial_no,
        serial_no_2=item.serial_no_2,
        item_name=None,
        item_code=item.item_code,
        order_no=order.order_no if order else None,
        customer_name=order.customer_name if order else None,
        customer_contact=order.customer_contact if order else None,
        pcb_warranty_date=context["pcb_warranty_date"],
        component_warranty_date=context["component_warranty_date"],
        machine_warranty_date=context["machine_warranty_date"],
        installation_status=item.installation_status,
        free_service_count=item.free_service_count,
        service_consume_count=item.service_consume_count,
    )
