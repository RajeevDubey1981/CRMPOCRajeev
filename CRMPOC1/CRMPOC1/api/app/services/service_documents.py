from datetime import datetime, timezone
from urllib.parse import urljoin

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.field_photo import FieldPhoto
from app.models.payment import PaymentTransaction
from app.models.payment_approval import PaymentApprovalLog
from app.models.pending_action import UserPendingAction
from app.models.service import (
    ServiceAssignment,
    ServiceApproval,
    ServiceCompletion,
    ServiceDocument,
    ServiceDocumentRule,
    ServiceNotification,
    ServiceObservation,
    ServicePaymentRequest,
    ServiceRequest,
    ServiceRequestItem,
    ServiceStatusLog,
    ServiceRequestUnit,
    ServiceUnitAssignment,
)

CUSTOMER_DOCUMENT_APPROVED_STATUSES = {"Reviewed", "Approved"}

CUSTOMER_DOCUMENT_TYPES = {
    "Purchase Order",
    "Original Purchase Bill/Invoice",
}
CUSTOMER_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
}
CUSTOMER_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def build_public_upload_url(token: str) -> str:
    base = (settings.app_public_url or "").strip()
    if not base:
        base = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:5173"
    return urljoin(base.rstrip("/") + "/", f"services/public-upload/{token}")


def _required_documents_from_rules(
    db: Session,
    service_type: str | None,
    warranty_status: str | None,
    query_type: str | None,
) -> list[str]:
    stmt = select(ServiceDocumentRule).where(
        ServiceDocumentRule.is_active == True,
        ServiceDocumentRule.is_required == True,
    )
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


def customer_document_types(db: Session, service: ServiceRequest) -> list[str]:
    configured = [
        doc
        for doc in _required_documents_from_rules(
            db, service.service_type, service.warranty_status, service.query_type
        )
        if doc in CUSTOMER_DOCUMENT_TYPES
    ]
    if configured:
        return configured
    return sorted(CUSTOMER_DOCUMENT_TYPES)


def latest_customer_documents_by_type(db: Session, service_id: int) -> dict[str, ServiceDocument]:
    rows = db.scalars(
        select(ServiceDocument)
        .where(
            ServiceDocument.service_request_id == service_id,
            ServiceDocument.uploaded_by_type == "customer",
        )
        .order_by(desc(ServiceDocument.uploaded_at))
    ).all()
    latest: dict[str, ServiceDocument] = {}
    for row in rows:
        if row.document_type not in latest:
            latest[row.document_type] = row
    return latest


def mark_latest_customer_documents_for_resubmission(
    db: Session,
    service: ServiceRequest,
    *,
    remarks: str | None = None,
) -> None:
    """Keep existing files, but make the current customer document set require a fresh upload."""
    now = datetime.now(timezone.utc)
    for row in latest_customer_documents_by_type(db, service.id).values():
        row.status = "Rejected"
        row.reviewed_at = now
        row.review_remarks = remarks or "Sent back for a new document upload."
        db.add(row)


SERVICE_WORKFLOW_RANK = {
    "New": 0,
    "Admin Review Document": 10,
    "Service Team Review": 20,
    "Assigned": 30,
    "Engineer Visit": 40,
    "Serial Verification Review": 45,
    "Serial Verified": 50,
    "Pending Service Approval": 60,
    "Approved for Service": 70,
    "Service In Progress": 80,
    "Service Completed": 90,
    "Completion Pending Approval": 92,
    "Payment Requested": 95,
    "Payment Completed": 98,
    "Closed": 100,
    "Rejected": 5,
    "Cancelled": 5,
}


def service_workflow_rank(status: str | None) -> int:
    return SERVICE_WORKFLOW_RANK.get((status or "").strip(), 999)


def service_workflow_is_revert(old_status: str, new_status: str) -> bool:
    return service_workflow_rank(new_status) < service_workflow_rank(old_status)


def _delete_engineer_workflow_records(db: Session, service_id: int) -> None:
    payment_request_ids = list(
        db.scalars(
            select(ServicePaymentRequest.id).where(ServicePaymentRequest.service_request_id == service_id)
        )
    )
    payment_log_filters = [
        PaymentApprovalLog.module == "services",
        PaymentApprovalLog.entity_id == service_id,
    ]
    if payment_request_ids:
        payment_log_filters.append(PaymentApprovalLog.service_payment_request_id.in_(payment_request_ids))
    for row in db.scalars(
        select(PaymentApprovalLog).where(or_(*payment_log_filters))
    ):
        db.delete(row)
    db.flush()
    for model in (ServicePaymentRequest, ServiceCompletion, ServiceApproval, ServiceObservation):
        for row in db.scalars(select(model).where(model.service_request_id == service_id)):
            db.delete(row)
        db.flush()


def _delete_unit_photos(db: Session, service_id: int) -> None:
    unit_ids = list(
        db.scalars(
            select(ServiceRequestUnit.id).where(ServiceRequestUnit.service_request_id == service_id)
        )
    )
    if not unit_ids:
        return
    for row in db.scalars(select(FieldPhoto).where(FieldPhoto.service_request_unit_id.in_(unit_ids))):
        db.delete(row)
    db.flush()


def _delete_service_pending_actions(db: Session, service_id: int) -> None:
    for row in db.scalars(
        select(UserPendingAction).where(
            UserPendingAction.module == "services",
            UserPendingAction.entity_id == service_id,
        )
    ):
        db.delete(row)


def _clear_serial_verification_state(db: Session, service: ServiceRequest) -> None:
    """Undo engineer serial verification so Assigned / Engineer Visit can run again."""
    service.serial_no = None
    service.order_item_id = None
    service.warranty_status = None
    db.add(service)
    for unit in db.scalars(select(ServiceRequestUnit).where(ServiceRequestUnit.service_request_id == service.id)):
        unit.serial_verified_at = None
        unit.warranty_status = None
        unit.service_type = None
        db.add(unit)


def reset_service_downstream_workflow_for_documents(db: Session, service: ServiceRequest) -> None:
    """Reset order verification and engineer assignment; keep uploaded customer documents."""
    now = datetime.now(timezone.utc)
    for assignment in db.scalars(
        select(ServiceAssignment).where(ServiceAssignment.service_request_id == service.id)
    ):
        assignment.is_active = False
        db.add(assignment)

    _delete_engineer_workflow_records(db, service.id)
    _delete_unit_photos(db, service.id)

    for unit_assignment in db.scalars(select(ServiceUnitAssignment).where(ServiceUnitAssignment.service_request_id == service.id)):
        db.delete(unit_assignment)
    db.flush()
    for unit in db.scalars(select(ServiceRequestUnit).where(ServiceRequestUnit.service_request_id == service.id)):
        db.delete(unit)
    db.flush()
    for item in db.scalars(select(ServiceRequestItem).where(ServiceRequestItem.service_request_id == service.id)):
        db.delete(item)
    db.flush()

    _clear_serial_verification_state(db, service)

    service.order_id = None
    service.order_item_id = None
    service.assigned_engineer_id = None
    service.assigned_vendor_id = None
    service.approved_at = None
    service.completed_at = None
    service.closed_at = None
    service.completion_code = None
    service.customer_identified_at = None
    service.status_date = now
    db.add(service)


def on_enter_service_team_review(db: Session, service: ServiceRequest) -> None:
    """Entering Service Team Review: keep customer documents, clear order/assignment/engineer steps."""
    reset_service_downstream_workflow_for_documents(db, service)


def reset_service_workflow_from_status(db: Session, service: ServiceRequest, target_status: str) -> None:
    """Admin revert: keep customer documents, clear steps after the selected workflow step."""
    target_rank = service_workflow_rank(target_status)
    team_review_rank = service_workflow_rank("Service Team Review")
    serial_verified_rank = service_workflow_rank("Serial Verified")
    service_completed_rank = service_workflow_rank("Service Completed")

    if target_rank <= team_review_rank:
        reset_service_downstream_workflow_for_documents(db, service)
        return

    _delete_engineer_workflow_records(db, service.id)

    if target_rank < serial_verified_rank:
        _clear_serial_verification_state(db, service)

    if target_rank < service_completed_rank:
        service.completed_at = None
        service.completion_code = None

    if target_rank < service_workflow_rank("Approved for Service"):
        service.approved_at = None

    if target_rank < service_workflow_rank("Closed"):
        service.closed_at = None

    service.status_date = datetime.now(timezone.utc)
    db.add(service)


def delete_service_request_graph(db: Session, service: ServiceRequest) -> None:
    """Hard-delete a service request and rows owned by the service workflow."""
    payment_transaction_ids = {
        payment_transaction_id
        for payment_transaction_id in db.scalars(
            select(ServicePaymentRequest.payment_transaction_id).where(
                ServicePaymentRequest.service_request_id == service.id,
                ServicePaymentRequest.payment_transaction_id.is_not(None),
            )
        )
    }
    _delete_engineer_workflow_records(db, service.id)
    _delete_unit_photos(db, service.id)
    _delete_service_pending_actions(db, service.id)

    for row in db.scalars(select(ServiceUnitAssignment).where(ServiceUnitAssignment.service_request_id == service.id)):
        db.delete(row)
    db.flush()
    for row in db.scalars(select(ServiceRequestUnit).where(ServiceRequestUnit.service_request_id == service.id)):
        db.delete(row)
    db.flush()
    for row in db.scalars(select(ServiceRequestItem).where(ServiceRequestItem.service_request_id == service.id)):
        db.delete(row)
    db.flush()
    for row in db.scalars(select(ServiceAssignment).where(ServiceAssignment.service_request_id == service.id)):
        db.delete(row)
    for row in db.scalars(select(ServiceDocument).where(ServiceDocument.service_request_id == service.id)):
        db.delete(row)
    for row in db.scalars(select(ServiceNotification).where(ServiceNotification.service_request_id == service.id)):
        db.delete(row)
    for row in db.scalars(select(ServiceStatusLog).where(ServiceStatusLog.service_request_id == service.id)):
        db.delete(row)

    for transaction_id in payment_transaction_ids:
        still_used = db.scalar(
            select(ServicePaymentRequest.id)
            .where(ServicePaymentRequest.payment_transaction_id == transaction_id)
            .limit(1)
        )
        if not still_used:
            transaction = db.get(PaymentTransaction, transaction_id)
            if transaction:
                db.delete(transaction)

    db.delete(service)


def document_workflow_active(service: ServiceRequest) -> bool:
    return bool(
        service.ask_for_documents
        or service.document_request_sent_at
        or service.requires_documents
    )


def customer_documents_approved(db: Session, service: ServiceRequest) -> bool:
    if not document_workflow_active(service):
        return True
    configured = customer_document_types(db, service)
    latest = latest_customer_documents_by_type(db, service.id)
    if not latest:
        return False
    required = [doc_type for doc_type in configured if doc_type in latest]
    if not required:
        required = list(latest.keys())
    for doc_type in required:
        row = latest[doc_type]
        if row.status not in CUSTOMER_DOCUMENT_APPROVED_STATUSES:
            return False
    return True


def order_workflow_unlocked(db: Session, service: ServiceRequest) -> bool:
    return customer_documents_approved(db, service)


def sync_document_workflow_status(db: Session, service: ServiceRequest) -> bool:
    """Align service status with customer document upload/review state."""
    if not document_workflow_active(service):
        return False
    latest = latest_customer_documents_by_type(db, service.id)
    if not latest:
        return False
    changed = False
    if customer_documents_approved(db, service):
        if service.status == "Admin Review Document":
            on_enter_service_team_review(db, service)
            service.status = "Service Team Review"
            service.status_date = datetime.now(timezone.utc)
            changed = True
    else:
        pending = any(
            row.status not in CUSTOMER_DOCUMENT_APPROVED_STATUSES for row in latest.values()
        )
        if pending and service.status in {"New", "Service Team Review"}:
            service.status = "Admin Review Document"
            service.status_date = datetime.now(timezone.utc)
            changed = True
    return changed
