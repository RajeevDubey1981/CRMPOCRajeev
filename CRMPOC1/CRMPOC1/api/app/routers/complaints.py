import csv
import io
import secrets
import time
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.call import Call
from app.models.complaint import Complaint, ComplaintStatusLog
from app.models.installation import InstallationDocument, InstallationRequest
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.vendor import Vendor
from app.models.service import ServiceDocument, ServiceRequest
from app.models.user import User
from app.schemas.complaint import (
    ACTIONS,
    QUERY_TYPES,
    STATUSES,
    ComplaintActionRecord,
    ComplaintCreate,
    ComplaintHistoryEntry,
    ComplaintLinkCustomer,
    ComplaintListItem,
    ComplaintListResponse,
    ComplaintModelOption,
    ComplaintOut,
    ComplaintStatusUpdate,
    ComplaintUpdate,
)
from app.services.email_bounce import bounce_info, bounced_map
from app.services.email_service import (
    send_complaint_created_email,
    send_document_upload_link_email,
    send_service_request_acknowledgment_email,
)
from app.services.file_service import save_upload, to_public_upload_path
from app.services.permissions import can_act_on, sub_module_scope
from app.services.role_access import is_operations_admin
from app.services.installation_workflow import (
    CUSTOMER_DOCUMENT_OPTIONS,
    PRE_ORDER_VERIFIED_STATUSES,
    document_upload_url,
    ensure_document_token,
    log_installation_action,
    now_utc,
    payment_qr_view_url,
    serialize_datetime,
)
from app.services.service_documents import (
    build_public_upload_url,
    customer_document_types,
    customer_documents_approved,
    latest_customer_documents_by_type,
)
from app.services.engineer_service_scope import engineer_visible_complaint_filter
from app.services.workflow_notifications import notify_engineer_complaint_assigned
from app.services.serial_history import EVENT_TYPES, create_serial_history_event

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


def _apply_view_scope(stmt, db: Session, user: User):
    """Restrict a complaint query to the user's allowed query types.

    Returns (stmt, has_any_access). When has_any_access is False the caller
    should short-circuit with an empty result.
    """
    scope = sub_module_scope(db, user, "complaints", "can_view")
    if scope is None:
        scoped = stmt
    elif not scope:
        return stmt, False
    else:
        scoped = stmt.where(Complaint.query_type.in_(scope))
    if (user.role or "").lower() == "engineer":
        scoped = scoped.where(engineer_visible_complaint_filter(user.id))
    return scoped, True


def _sync_linked_service_engineer(db: Session, complaint: Complaint) -> None:
    if not complaint.assigned_engineer:
        return
    service = _find_linked_service_request(db, complaint.id)
    if service is None:
        return
    if service.assigned_engineer_id == complaint.assigned_engineer:
        return
    service.assigned_engineer_id = complaint.assigned_engineer
    service.assigned_vendor_id = None
    if service.status in {"New", "Service Team Review", "Rejected"}:
        service.status = "Assigned"
        service.status_date = datetime.now(timezone.utc)


# complaint field -> linked service request field, kept in sync when staff correct customer details
# (e.g. an email the voice agent misheard) so later service emails go to the right person.
_COMPLAINT_TO_SERVICE_CONTACT_FIELDS = {
    "customer_name": "customer_name",
    "customer_mobile": "customer_mobile",
    "customer_email": "customer_email",
    "customer_address": "customer_address",
    "model_details": "model_details",
    "problem_description": "problem_description",
    "remark": "additional_remarks",
}


def _sync_linked_service_contact(db: Session, complaint: Complaint, changed_fields) -> None:
    service = _find_linked_service_request(db, complaint.id)
    if service is None:
        return
    for complaint_field, service_field in _COMPLAINT_TO_SERVICE_CONTACT_FIELDS.items():
        if complaint_field in changed_fields:
            setattr(service, service_field, getattr(complaint, complaint_field))


def _sync_linked_installation_engineer(db: Session, complaint: Complaint) -> None:
    if not complaint.assigned_engineer:
        return
    inst = _find_linked_installation_request(db, complaint)
    if inst is None:
        return
    if inst.assigned_engineer == complaint.assigned_engineer:
        return
    inst.assigned_engineer = complaint.assigned_engineer
    if inst.status == "Order Verified":
        inst.status = "Assigned"


def _linked_installation_payload(db: Session, inst: InstallationRequest | None) -> dict:
    if inst is None:
        return {
            "installation_request_id": None,
            "status": None,
            "upload_url": None,
            "document_request_sent_at": None,
            "order_id": None,
            "order_no": None,
            "order_verified_at": None,
            "assigned_engineer": None,
            "assigned_engineer_name": None,
            "engineer_site_remarks": None,
            "engineer_serials_submitted_at": None,
            "serial_verified_at": None,
        }
    order_no = None
    if inst.order_id:
        order = db.get(Order, inst.order_id)
        order_no = order.order_no if order else None
    engineer_name = None
    if inst.assigned_engineer:
        engineer = db.get(User, inst.assigned_engineer)
        engineer_name = engineer.name if engineer else None
    item_code = None
    if inst.order_item_id:
        order_item = db.get(OrderItem, inst.order_item_id)
        item_code = order_item.item_code if order_item else None
    return {
        "installation_request_id": inst.id,
        "status": inst.status,
        "upload_url": document_upload_url(inst),
        "document_request_sent_at": serialize_datetime(inst.document_request_sent_at),
        "order_id": inst.order_id,
        "order_no": order_no,
        "order_verified_at": serialize_datetime(inst.order_verified_at),
        "assigned_engineer": inst.assigned_engineer,
        "assigned_engineer_name": engineer_name,
        "engineer_site_remarks": inst.engineer_site_remarks,
        "engineer_serials_submitted_at": serialize_datetime(inst.engineer_serials_submitted_at),
        "serial_verified_at": serialize_datetime(inst.serial_verified_at),
        "item_code": item_code,
        "serial_no": inst.serial_no,
        "serial_no_2": inst.serial_no_2,
        "admin_billing_type": inst.admin_billing_type,
        "parent_installation_id": inst.parent_installation_id,
        "payment_amount_requested": float(inst.payment_amount_requested) if inst.payment_amount_requested is not None else None,
        "payment_type_requested": inst.payment_type_requested,
        "payment_qr_code_path": payment_qr_view_url(inst),
        "payment_proof_file_path": to_public_upload_path(inst.payment_proof_file_path),
        "work_report_file_path": to_public_upload_path(inst.work_report_file_path),
        "installation_date": serialize_datetime(inst.installation_date),
    }


def _sync_installation_order_from_complaint(
    db: Session,
    complaint: Complaint,
    order: Order,
    item: OrderItem | None,
    user: User,
    inst: InstallationRequest | None = None,
) -> InstallationRequest | None:
    if (complaint.query_type or "").lower() != "installation":
        return None
    if inst is None:
        inst = _find_linked_installation_request(db, complaint)
    if inst is None:
        inst = InstallationRequest(
            complaint_id=complaint.id,
            source="callcenter",
            created_by=user.id,
            customer_name=complaint.customer_name,
            contact_number=complaint.customer_mobile,
            customer_email=complaint.customer_email,
            address=complaint.customer_address,
            order_id=complaint.order_id,
            order_item_id=complaint.order_item_id,
            product_name=complaint.model_details,
            serial_no=complaint.serial_no,
            request_date=datetime.now(timezone.utc),
            status="Pending",
        )
        ensure_document_token(inst)
        db.add(inst)
        db.flush()
        log_installation_action(
            db,
            inst,
            action="Created From Complaint",
            user=user,
            new_status=inst.status,
            metadata={"complaint_id": complaint.id, "comp_no": complaint.comp_no},
        )
    old_status = inst.status
    inst.order_id = order.id
    if item is not None:
        inst.order_item_id = item.id
        inst.serial_no = complaint.serial_no or item.serial_no or item.serial_no_2 or inst.serial_no
    inst.customer_name = order.customer_name or inst.customer_name
    inst.contact_number = order.customer_contact or inst.contact_number
    inst.customer_email = order.customer_email or inst.customer_email
    inst.address = order.customer_address or inst.address
    inst.order_verified_at = now_utc()
    inst.order_verified_by = user.id
    if inst.status in PRE_ORDER_VERIFIED_STATUSES:
        inst.status = "Order Verified"
    log_installation_action(
        db,
        inst,
        action="Order Verified",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=f"Order {order.order_no} linked from complaint {complaint.comp_no}",
        metadata={"order_id": order.id, "order_no": order.order_no, "complaint_id": complaint.id},
    )
    return inst


def _generate_comp_no() -> str:
    return f"IDC_{int(time.time() * 1000)}"


def _generate_access_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _generate_service_access_token() -> str:
    return secrets.token_urlsafe(24)


def _order_link_fields(db: Session, complaint: Complaint) -> dict[str, int | str | None]:
    if complaint.order_id:
        order = db.get(Order, complaint.order_id)
        return {
            "order_id": complaint.order_id,
            "order_no": order.order_no if order else None,
        }
    if not complaint.order_item_id:
        return {"order_id": None, "order_no": None}
    item = db.get(OrderItem, complaint.order_item_id)
    if item is None:
        return {"order_id": None, "order_no": None}
    order = db.get(Order, item.order_id)
    if order is None:
        return {"order_id": None, "order_no": None}
    return {"order_id": order.id, "order_no": order.order_no}


def _bounce_fields(db: Session, email_address: str | None) -> dict:
    bounced, reason = bounce_info(db, email_address)
    return {"email_bounced": bounced, "email_bounce_reason": reason}


def _with_bounce_flags(db: Session, items: list[ComplaintListItem]) -> list[ComplaintListItem]:
    flagged = bounced_map(db, [i.customer_email for i in items])
    for i in items:
        reason = flagged.get((i.customer_email or "").strip().lower())
        i.email_bounced = reason is not None
        i.email_bounce_reason = reason
    return items


def _hydrate(db: Session, c: Complaint) -> dict:
    engineer_name = None
    if c.assigned_engineer:
        u = db.get(User, c.assigned_engineer)
        engineer_name = u.name if u else None
    created_by_name = None
    if c.created_by:
        u = db.get(User, c.created_by)
        created_by_name = u.name if u else None
    return {
        **{k: getattr(c, k) for k in (
            "id", "comp_no", "comp_date", "customer_name", "customer_mobile",
            "customer_email", "customer_address", "model_details",
            "problem_description", "query_type", "status", "status_date",
            "assigned_engineer", "remark", "service_proof_path", "access_code",
            "send_sms", "created_by", "order_id", "order_item_id", "serial_no", "source", "created_at", "updated_at",
        )},
        "assigned_engineer_name": engineer_name,
        "created_by_name": created_by_name,
        **_bounce_fields(db, c.customer_email),
        **_order_link_fields(db, c),
    }


def _list_row(
    db: Session,
    c: Complaint,
    call_count: int = 0,
    pending_followup_count: int = 0,
    last_action_taken: str | None = None,
    document_link_sent: bool = False,
    customer_documents_received: bool = False,
    service_request_id: int | None = None,
    service_request_no: str | None = None,
    service_request_status: str | None = None,
    installation_request_id: int | None = None,
    installation_request_status: str | None = None,
) -> ComplaintListItem:
    engineer_name = None
    if c.assigned_engineer:
        u = db.get(User, c.assigned_engineer)
        engineer_name = u.name if u else None
    created_by_name = None
    if c.created_by:
        u = db.get(User, c.created_by)
        created_by_name = u.name if u else None
    return ComplaintListItem(
        id=c.id,
        comp_no=c.comp_no,
        customer_name=c.customer_name,
        customer_mobile=c.customer_mobile,
        customer_email=c.customer_email,
        customer_address=c.customer_address,
        model_details=c.model_details,
        problem_description=c.problem_description,
        query_type=c.query_type,
        status=c.status,
        status_date=c.status_date,
        assigned_engineer_name=engineer_name,
        remark=c.remark,
        created_by_name=created_by_name,
        serial_no=c.serial_no,
        order_item_id=c.order_item_id,
        created_at=c.created_at,
        call_count=call_count,
        pending_followup_count=pending_followup_count,
        last_action_taken=last_action_taken,
        document_link_sent=document_link_sent,
        customer_documents_received=customer_documents_received,
        service_request_id=service_request_id,
        service_request_no=service_request_no,
        service_request_status=service_request_status,
        installation_request_id=installation_request_id,
        installation_request_status=installation_request_status,
    )


def _load_visible_complaint(db: Session, complaint_id: int, user: User) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None or complaint.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint not found")
    if not can_act_on(db, user, "complaints", "can_view", complaint.query_type):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint not found")
    return complaint


def _find_linked_service_request(db: Session, complaint_id: int) -> ServiceRequest | None:
    return db.scalar(
        select(ServiceRequest).where(
            ServiceRequest.complaint_id == complaint_id,
            ServiceRequest.deleted_at.is_(None),
        )
    )


def _is_callcenter(user: User) -> bool:
    return (user.role or "").lower() == "callcenter"


def _is_complaint_editor_role(user: User) -> bool:
    return (user.role or "").strip().lower() in {
        "callcenter",
        "call center",
        "admin",
        "incool",
        "indcool",
        "indcool service",
        "indcool_service",
    }


def _callcenter_workflow_locked(db: Session, complaint: Complaint) -> bool:
    service = _find_linked_service_request(db, complaint.id)
    if service is not None and service.document_request_sent_at is not None:
        return True
    if (complaint.query_type or "").lower() == "installation":
        inst = _find_linked_installation_request(db, complaint)
        if inst is not None and inst.document_request_sent_at is not None:
            return True
    return False


def _assert_callcenter_can_edit(db: Session, user: User, complaint: Complaint) -> None:
    if _is_complaint_editor_role(user) and _callcenter_workflow_locked(db, complaint):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This complaint cannot be edited after the customer document link has been sent",
        )


def _document_link_sent_map(db: Session, complaint_ids: list[int]) -> dict[int, bool]:
    if not complaint_ids:
        return {}
    result: dict[int, bool] = {}
    service_rows = db.execute(
        select(ServiceRequest.complaint_id)
        .where(
            ServiceRequest.complaint_id.in_(complaint_ids),
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.document_request_sent_at.is_not(None),
        )
    ).all()
    for row in service_rows:
        result[row.complaint_id] = True
    installation_rows = db.execute(
        select(InstallationRequest.complaint_id)
        .where(
            InstallationRequest.complaint_id.in_(complaint_ids),
            InstallationRequest.document_request_sent_at.is_not(None),
        )
    ).all()
    for row in installation_rows:
        if row.complaint_id is not None:
            result[row.complaint_id] = True
    return result


def _customer_documents_received_map(db: Session, complaint_ids: list[int]) -> dict[int, bool]:
    if not complaint_ids:
        return {}
    result: dict[int, bool] = {}
    service_rows = db.execute(
        select(ServiceRequest.complaint_id)
        .join(ServiceDocument, ServiceDocument.service_request_id == ServiceRequest.id)
        .where(
            ServiceRequest.complaint_id.in_(complaint_ids),
            ServiceRequest.deleted_at.is_(None),
            ServiceDocument.uploaded_by_type == "customer",
        )
        .distinct()
    ).all()
    for row in service_rows:
        result[row.complaint_id] = True
    installation_rows = db.execute(
        select(InstallationRequest.complaint_id)
        .join(
            InstallationDocument,
            InstallationDocument.installation_request_id == InstallationRequest.id,
        )
        .where(
            InstallationRequest.complaint_id.in_(complaint_ids),
            InstallationDocument.uploaded_by_type == "customer",
        )
        .distinct()
    ).all()
    for row in installation_rows:
        if row.complaint_id is not None:
            result[row.complaint_id] = True
    return result


def _linked_service_map(db: Session, complaint_ids: list[int]) -> dict[int, tuple[int, str, str]]:
    if not complaint_ids:
        return {}
    rows = db.execute(
        select(ServiceRequest.complaint_id, ServiceRequest.id, ServiceRequest.request_no, ServiceRequest.status)
        .where(
            ServiceRequest.complaint_id.in_(complaint_ids),
            ServiceRequest.deleted_at.is_(None),
        )
    ).all()
    return {row.complaint_id: (row.id, row.request_no, row.status) for row in rows}


def _find_linked_installation_request(db: Session, complaint: Complaint) -> InstallationRequest | None:
    inst = db.scalar(
        select(InstallationRequest)
        .where(InstallationRequest.complaint_id == complaint.id)
        .order_by(desc(InstallationRequest.created_at))
    )
    if inst is not None:
        return inst
    if complaint.order_item_id:
        inst = db.scalar(
            select(InstallationRequest)
            .where(InstallationRequest.order_item_id == complaint.order_item_id)
            .order_by(desc(InstallationRequest.created_at))
        )
        if inst is not None:
            return inst
    serial = (complaint.serial_no or "").strip()
    if serial:
        return db.scalar(
            select(InstallationRequest)
            .where(
                or_(
                    func.lower(InstallationRequest.serial_no) == func.lower(serial),
                    func.lower(InstallationRequest.serial_no_2) == func.lower(serial),
                )
            )
            .order_by(desc(InstallationRequest.created_at))
        )
    return None


def _ensure_installation_request_for_complaint(db: Session, complaint: Complaint, user: User) -> InstallationRequest:
    existing = _find_linked_installation_request(db, complaint)
    if existing is not None:
        if complaint.order_id:
            order = db.get(Order, complaint.order_id)
            item = db.get(OrderItem, complaint.order_item_id) if complaint.order_item_id else None
            needs_order_sync = (
                not existing.order_verified_at
                or existing.order_id != complaint.order_id
                or existing.status in PRE_ORDER_VERIFIED_STATUSES
            )
            if order is not None and needs_order_sync:
                _sync_installation_order_from_complaint(db, complaint, order, item, user, inst=existing)
        return existing
    if (complaint.query_type or "").lower() != "installation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only Installation complaints can create linked installation requests")
    inst = InstallationRequest(
        complaint_id=complaint.id,
        source="callcenter",
        created_by=user.id,
        customer_name=complaint.customer_name,
        contact_number=complaint.customer_mobile,
        customer_email=complaint.customer_email,
        address=complaint.customer_address,
        order_id=complaint.order_id,
        order_item_id=complaint.order_item_id,
        product_name=complaint.model_details,
        serial_no=complaint.serial_no,
        request_date=datetime.now(timezone.utc),
        status="Pending",
    )
    ensure_document_token(inst)
    db.add(inst)
    db.flush()
    log_installation_action(
        db,
        inst,
        action="Created From Complaint",
        user=user,
        new_status=inst.status,
        metadata={"complaint_id": complaint.id, "comp_no": complaint.comp_no},
    )
    return inst


def _linked_installation_map(db: Session, complaints: list[Complaint]) -> dict[int, tuple[int, str]]:
    if not complaints:
        return {}
    linked: dict[int, tuple[int, str]] = {}
    complaint_ids = [c.id for c in complaints]
    if complaint_ids:
        rows = db.scalars(
            select(InstallationRequest)
            .where(InstallationRequest.complaint_id.in_(complaint_ids))
            .order_by(desc(InstallationRequest.created_at))
        ).all()
        for row in rows:
            if row.complaint_id and row.complaint_id not in linked:
                linked[row.complaint_id] = (row.id, row.status)
    order_item_ids = [c.order_item_id for c in complaints if c.order_item_id]
    if order_item_ids:
        rows = db.scalars(
            select(InstallationRequest)
            .where(InstallationRequest.order_item_id.in_(order_item_ids))
            .order_by(desc(InstallationRequest.created_at))
        ).all()
        by_order_item: dict[int, InstallationRequest] = {}
        for row in rows:
            if row.order_item_id and row.order_item_id not in by_order_item:
                by_order_item[row.order_item_id] = row
        for complaint in complaints:
            if complaint.order_item_id and complaint.order_item_id in by_order_item:
                row = by_order_item[complaint.order_item_id]
                linked[complaint.id] = (row.id, row.status)
    for complaint in complaints:
        if complaint.id in linked:
            continue
        inst = _find_linked_installation_request(db, complaint)
        if inst is not None:
            linked[complaint.id] = (inst.id, inst.status)
    return linked


def _ensure_service_request_for_complaint(db: Session, complaint: Complaint, user: User) -> ServiceRequest:
    existing = _find_linked_service_request(db, complaint.id)
    if existing is not None:
        return existing
    now = datetime.now(timezone.utc)
    service = ServiceRequest(
        request_no=f"SRV_{int(time.time() * 1000)}",
        request_date=complaint.comp_date or date.today(),
        query_type=complaint.query_type or "Service",
        customer_name=complaint.customer_name,
        customer_mobile=complaint.customer_mobile,
        customer_email=complaint.customer_email,
        customer_address=complaint.customer_address,
        model_details=complaint.model_details,
        problem_description=complaint.problem_description,
        additional_remarks=complaint.remark,
        status="Service Team Review",
        status_date=datetime.now(timezone.utc),
        source=complaint.source or "callcenter",
        created_by=complaint.created_by or user.id,
        complaint_id=complaint.id,
        order_item_id=complaint.order_item_id,
        serial_no=complaint.serial_no,
        document_access_token=_generate_service_access_token(),
        created_at=now,
        updated_at=now,
    )
    db.add(service)
    db.flush()
    return service


def _queue_complaint_confirmation_email(
    background_tasks: BackgroundTasks,
    complaint: Complaint,
    service: ServiceRequest | None = None,
) -> None:
    if not complaint.customer_email:
        return
    if service is not None and (complaint.query_type or "").lower() == "service":
        background_tasks.add_task(
            send_service_request_acknowledgment_email,
            complaint.customer_email,
            complaint.comp_no,
        )
        return
    background_tasks.add_task(
        send_complaint_created_email,
        complaint.customer_email,
        complaint.customer_name,
        complaint.comp_no,
        complaint.query_type,
        complaint.status,
        complaint.customer_mobile,
        complaint.problem_description,
    )


@router.get("", response_model=ComplaintListResponse)
def list_complaints(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: Literal[STATUSES] | None = Query(None, alias="status"),  # type: ignore[valid-type]
    query_type: Literal[QUERY_TYPES] | None = None,  # type: ignore[valid-type]
    search: str | None = None,
    id: int | None = None,
    comp_no: str | None = None,
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = "-created_at",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Complaint).where(Complaint.deleted_at.is_(None))
    stmt, has_access = _apply_view_scope(stmt, db, user)
    if not has_access:
        return ComplaintListResponse(items=[], total=0, page=page, per_page=per_page)
    if id is not None:
        stmt = stmt.where(Complaint.id == id)
    if comp_no:
        stmt = stmt.where(Complaint.comp_no.ilike(f"%{comp_no.strip()}%"))
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    if query_type:
        stmt = stmt.where(Complaint.query_type == query_type)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.customer_name.ilike(like),
                Complaint.customer_mobile.ilike(like),
                Complaint.customer_email.ilike(like),
            )
        )
    if source:
        stmt = stmt.where(Complaint.source == source)
    if date_from:
        stmt = stmt.where(Complaint.comp_date >= date_from)
    if date_to:
        stmt = stmt.where(Complaint.comp_date <= date_to)

    sort_col = sort.lstrip("-")
    col = getattr(Complaint, sort_col, Complaint.created_at)
    stmt = stmt.order_by(desc(col) if sort.startswith("-") else col)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    complaint_ids = [c.id for c in rows]
    call_counts: dict[int, int] = {}
    pending_counts: dict[int, int] = {}
    last_actions: dict[int, str] = {}
    document_links: dict[int, bool] = {}
    documents_received: dict[int, bool] = {}
    linked_services: dict[int, tuple[int, str, str]] = {}
    linked_installations: dict[int, tuple[int, str]] = {}

    if complaint_ids:
        # Batch call counts
        for row in db.execute(
            select(
                Call.complaint_id,
                func.count(Call.id).label("total"),
                func.sum(case((Call.follow_up_status == "Pending", 1), else_=0)).label("pending"),
            )
            .where(Call.complaint_id.in_(complaint_ids))
            .group_by(Call.complaint_id)
        ).all():
            call_counts[row.complaint_id] = row.total
            pending_counts[row.complaint_id] = row.pending or 0

        # Batch last action taken per complaint
        subq = (
            select(
                ComplaintStatusLog.complaint_id,
                ComplaintStatusLog.action_taken,
                func.row_number().over(
                    partition_by=ComplaintStatusLog.complaint_id,
                    order_by=desc(ComplaintStatusLog.changed_at),
                ).label("rn"),
            )
            .where(
                ComplaintStatusLog.complaint_id.in_(complaint_ids),
                ComplaintStatusLog.action_taken.is_not(None),
            )
            .subquery()
        )
        for row in db.execute(
            select(subq.c.complaint_id, subq.c.action_taken).where(subq.c.rn == 1)
        ).all():
            last_actions[row.complaint_id] = row.action_taken

        document_links = _document_link_sent_map(db, complaint_ids)
        documents_received = _customer_documents_received_map(db, complaint_ids)
        linked_services = _linked_service_map(db, complaint_ids)
        linked_installations = _linked_installation_map(db, rows)

    return ComplaintListResponse(
        items=_with_bounce_flags(db, [
            _list_row(
                db, c,
                call_counts.get(c.id, 0),
                pending_counts.get(c.id, 0),
                last_actions.get(c.id),
                document_links.get(c.id, False),
                documents_received.get(c.id, False),
                *(linked_services.get(c.id) or (None, None, None)),
                *(linked_installations.get(c.id) or (None, None)),
            )
            for c in rows
        ]),
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    body: ComplaintCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "complaints", "can_create", body.query_type):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Your role cannot create complaints of type '{body.query_type or 'unspecified'}'",
        )
    complaint = Complaint(
        comp_no=_generate_comp_no(),
        comp_date=body.comp_date or date.today(),
        customer_name=body.customer_name,
        customer_mobile=body.customer_mobile,
        customer_email=body.customer_email,
        customer_address=body.customer_address,
        model_details=body.model_details,
        problem_description=body.problem_description,
        query_type=body.query_type,
        remark=body.remark,
        send_sms=body.send_sms,
        access_code=_generate_access_code(),
        status="Pending",
        created_by=user.id,
        source="callcenter",
    )
    db.add(complaint)
    db.flush()
    db.add(ComplaintStatusLog(
        complaint_id=complaint.id,
        old_status=None,
        new_status="Pending",
        changed_by=user.id,
        remark="Complaint created",
    ))
    linked_service = None
    if (complaint.query_type or "").lower() == "service":
        linked_service = _ensure_service_request_for_complaint(db, complaint, user)
    from app.services.pending_action_sync import sync_complaint_pending_actions

    sync_complaint_pending_actions(db, complaint)
    db.commit()
    db.refresh(complaint)
    _queue_complaint_confirmation_email(background_tasks, complaint, linked_service)
    # NOTE: spec mentions firing an SMS here when send_sms is true.
    # SMS provider integration is Sprint 6 — wire-up point lives in this code path.
    return ComplaintOut(**_hydrate(db, complaint))


@router.post("/{complaint_id}/resend-confirmation-email")
def resend_complaint_confirmation_email(
    complaint_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible_complaint(db, complaint_id, user)
    if not can_act_on(db, user, "complaints", "can_edit", complaint.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot send emails for this complaint")
    if not complaint.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required")
    linked_service = _find_linked_service_request(db, complaint.id)
    _queue_complaint_confirmation_email(background_tasks, complaint, linked_service)
    ticket_id = linked_service.request_no if linked_service else complaint.comp_no
    return {"sent": True, "to": complaint.customer_email, "ticket_id": ticket_id}


@router.get("/export")
def export_csv(
    status_filter: Literal[STATUSES] | None = Query(None, alias="status"),  # type: ignore[valid-type]
    query_type: Literal[QUERY_TYPES] | None = None,  # type: ignore[valid-type]
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    export_scope = sub_module_scope(db, user, "complaints", "can_export")
    if export_scope is not None and not export_scope:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot export complaints")
    stmt = select(Complaint).where(Complaint.deleted_at.is_(None))
    if export_scope is not None:
        stmt = stmt.where(Complaint.query_type.in_(export_scope))
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    if query_type:
        stmt = stmt.where(Complaint.query_type == query_type)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.customer_name.ilike(like),
                Complaint.customer_mobile.ilike(like),
                Complaint.comp_no.ilike(like),
            )
        )
    if date_from:
        stmt = stmt.where(Complaint.comp_date >= date_from)
    if date_to:
        stmt = stmt.where(Complaint.comp_date <= date_to)
    stmt = stmt.order_by(desc(Complaint.created_at))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Ref No", "Comp Date", "Customer Name", "Mobile", "Email",
        "Address", "Query Type", "Model", "Problem", "Status", "Status Date",
        "Assigned Engineer", "Remark", "Created By", "Created At",
    ])
    for c in db.scalars(stmt).all():
        engineer = db.get(User, c.assigned_engineer).name if c.assigned_engineer else ""
        creator = db.get(User, c.created_by).name if c.created_by else ""
        writer.writerow([
            c.id, c.comp_no, c.comp_date, c.customer_name, c.customer_mobile,
            c.customer_email or "", c.customer_address or "", c.query_type or "",
            c.model_details or "", c.problem_description or "", c.status,
            c.status_date.isoformat() if c.status_date else "",
            engineer, c.remark or "", creator,
            c.created_at.isoformat(),
        ])
    buf.seek(0)
    filename = f"complaints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/model-options", response_model=list[ComplaintModelOption])
def list_complaint_model_options(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.complaint_model_masters import list_complaint_model_options as load_options

    return load_options(db)


@router.get("/customers/search")
def search_customers_for_complaint(
    search: str | None = None,
    mobile: str | None = None,
    name: str | None = None,
    order_no: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not any(can_act_on(db, user, "complaints", "can_create", query_type) for query_type in QUERY_TYPES):
        return []
    seen: set[tuple] = set()
    results: list[dict] = []

    def add_result(payload: dict) -> None:
        key = (
            (payload.get("customer_name") or "").strip().lower(),
            (payload.get("customer_mobile") or "").strip(),
            payload.get("order_id"),
            payload.get("order_item_id"),
        )
        if key in seen:
            return
        seen.add(key)
        results.append(payload)

    stmt = select(Order, Vendor.name_of_firm.label("vendor_name")).join(
        Vendor, Order.vendor_id == Vendor.id, isouter=True,
    ).where(Order.deleted_at.is_(None))
    order_terms = []
    if search and search.strip():
        query = search.strip()
        order_terms.append(or_(
            Order.customer_contact.ilike(f"%{query}%"),
            Order.customer_name.ilike(f"%{query}%"),
            Order.order_no.ilike(f"%{query}%"),
            Order.oem_bill_no.ilike(f"%{query}%"),
            Vendor.name_of_firm.ilike(f"%{query}%"),
            Vendor.vendor_code.ilike(f"%{query}%"),
        ))
    if mobile and mobile.strip():
        order_terms.append(Order.customer_contact.ilike(f"%{mobile.strip()}%"))
    if name and name.strip():
        order_terms.append(Order.customer_name.ilike(f"%{name.strip()}%"))
    if order_no and order_no.strip():
        order_terms.append(Order.order_no.ilike(f"%{order_no.strip()}%"))
    if order_terms:
        stmt = stmt.where(or_(*order_terms))
    for row, vendor_name in db.execute(stmt.order_by(desc(Order.created_at)).limit(20)).all():
        add_result({
            "order_id": row.id,
            "order_item_id": None,
            "order_no": row.order_no,
            "oem_bill_no": row.oem_bill_no,
            "vendor_name": vendor_name,
            "customer_name": row.customer_name,
            "customer_mobile": row.customer_contact,
            "customer_email": row.customer_email,
            "customer_address": row.customer_address,
            "serial_no": None,
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
    for row in db.scalars(complaint_stmt.order_by(desc(Complaint.created_at)).limit(10)).all():
        add_result({
            "order_id": None,
            "order_item_id": row.order_item_id,
            "order_no": None,
            "customer_name": row.customer_name,
            "customer_mobile": row.customer_mobile,
            "customer_email": row.customer_email,
            "customer_address": row.customer_address,
            "serial_no": row.serial_no,
            "source_type": "complaint",
        })
    return results[:20]


def _load_visible(db: Session, user: User, complaint_id: int) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint not found")
    if not can_act_on(db, user, "complaints", "can_view", c.query_type):
        # Hide existence: 404, not 403.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint not found")
    return c


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = _load_visible(db, user, complaint_id)
    return ComplaintOut(**_hydrate(db, c))


@router.post("/{complaint_id}/link-customer", response_model=ComplaintOut)
def link_complaint_customer(
    complaint_id: int,
    body: ComplaintLinkCustomer,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can link customer/order")
    c = _load_visible(db, user, complaint_id)
    if not can_act_on(db, user, "complaints", "can_edit", c.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this complaint")

    order = db.get(Order, body.order_id) if body.order_id else None
    item = db.get(OrderItem, body.order_item_id) if body.order_item_id else None
    if item and order is None:
        order = db.get(Order, item.order_id)
    if item and order and item.order_id != order.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order item does not belong to selected order")

    serial = (body.serial_no or "").strip()
    if serial and item is None:
        item = db.scalar(
            select(OrderItem).where(
                or_(
                    func.lower(OrderItem.serial_no) == func.lower(serial),
                    func.lower(OrderItem.serial_no_2) == func.lower(serial),
                )
            )
        )
        if item is not None:
            order = db.get(Order, item.order_id)

    if order:
        c.order_id = order.id
        c.customer_name = order.customer_name or c.customer_name
        c.customer_mobile = order.customer_contact or c.customer_mobile
        c.customer_email = order.customer_email or c.customer_email
        c.customer_address = order.customer_address or c.customer_address
    if any([body.customer_name, body.customer_mobile, body.customer_email, body.customer_address]):
        if body.customer_name:
            c.customer_name = body.customer_name
        if body.customer_mobile:
            c.customer_mobile = body.customer_mobile
        if body.customer_email:
            c.customer_email = body.customer_email
        if body.customer_address:
            c.customer_address = body.customer_address

    if item:
        c.order_item_id = item.id
        c.order_id = item.order_id
        c.serial_no = serial or item.serial_no or item.serial_no_2 or c.serial_no
    elif serial:
        c.serial_no = serial

    link_label = "Customer/order linked"
    if order and order.order_no:
        link_label = f"Linked to order {order.order_no}"
    elif body.customer_name:
        link_label = f"Linked customer {body.customer_name}"

    db.add(
        ComplaintStatusLog(
            complaint_id=c.id,
            old_status=c.status,
            new_status=c.status,
            changed_by=user.id,
            remark=link_label,
            action_taken="Link Customer",
        )
    )
    if order is not None:
        _sync_installation_order_from_complaint(db, c, order, item, user)
    db.commit()
    db.refresh(c)
    return ComplaintOut(**_hydrate(db, c))


@router.get("/{complaint_id}/installation-request")
def get_linked_installation_request(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    inst = _find_linked_installation_request(db, complaint)
    return _linked_installation_payload(db, inst)


@router.post("/{complaint_id}/installation-request")
def ensure_linked_installation_request(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    _assert_callcenter_can_edit(db, user, complaint)
    if (complaint.query_type or "").lower() != "installation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only Installation complaints can create linked installation requests")
    inst = _ensure_installation_request_for_complaint(db, complaint, user)
    db.commit()
    db.refresh(inst)
    return _linked_installation_payload(db, inst)


@router.post("/{complaint_id}/installation-request/verify-order")
def verify_complaint_installation_order(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can verify orders")
    complaint = _load_visible(db, user, complaint_id)
    if (complaint.query_type or "").lower() != "installation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only Installation complaints support order verification")
    if not complaint.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link an order before verifying")
    order = db.get(Order, complaint.order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked order not found")
    item = db.get(OrderItem, complaint.order_item_id) if complaint.order_item_id else None
    inst = _ensure_installation_request_for_complaint(db, complaint, user)
    _sync_installation_order_from_complaint(db, complaint, order, item, user, inst=inst)
    db.add(
        ComplaintStatusLog(
            complaint_id=complaint.id,
            old_status=complaint.status,
            new_status=complaint.status,
            changed_by=user.id,
            remark=f"Order {order.order_no} verified for installation workflow",
            action_taken="Order Verified",
        )
    )
    db.commit()
    db.refresh(inst)
    return _linked_installation_payload(db, inst)


@router.post("/{complaint_id}/installation-documents/request-link")
def request_installation_customer_documents(
    complaint_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    _assert_callcenter_can_edit(db, user, complaint)
    if (complaint.query_type or "").lower() != "installation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer upload links are only available for Installation complaints")
    if not complaint.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required before generating upload link")
    inst = _ensure_installation_request_for_complaint(db, complaint, user)
    ensure_document_token(inst)
    inst.ask_for_documents = True
    inst.document_request_sent_at = now_utc()
    if inst.status == "Pending":
        inst.status = "Document Requested"
    upload_url = document_upload_url(inst) or ""
    log_installation_action(
        db,
        inst,
        action="Documents Requested",
        user=user,
        old_status="Pending",
        new_status=inst.status,
        metadata={"upload_url": upload_url, "complaint_id": complaint.id},
    )
    db.add(
        ComplaintStatusLog(
            complaint_id=complaint.id,
            old_status=complaint.status,
            new_status=complaint.status,
            changed_by=user.id,
            remark="Customer installation document upload link generated",
            action_taken="Request Sent",
        )
    )
    db.commit()
    db.refresh(inst)
    background_tasks.add_task(
        send_document_upload_link_email,
        complaint.customer_email or "",
        complaint.customer_name,
        complaint.comp_no,
        upload_url,
        CUSTOMER_DOCUMENT_OPTIONS,
    )
    return {
        "installation_request_id": inst.id,
        "upload_url": upload_url,
        "document_request_sent_at": inst.document_request_sent_at,
        "status": inst.status,
    }


def _linked_service_document_summary(db: Session, service: ServiceRequest) -> list[dict]:
    latest = latest_customer_documents_by_type(db, service.id)
    return [
        {
            "id": row.id,
            "document_type": row.document_type,
            "status": row.status,
            "file_path": to_public_upload_path(row.file_path) or row.file_path,
            "uploaded_at": row.uploaded_at,
        }
        for row in latest.values()
    ]


@router.get("/{complaint_id}/service-request")
def get_linked_service_request(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    service = _find_linked_service_request(db, complaint.id)
    if service is None:
        return {
            "service_request_id": None,
            "request_no": None,
            "upload_url": None,
            "document_request_sent_at": None,
            "status": None,
            "customer_documents_approved": False,
            "documents": [],
        }
    return {
        "service_request_id": service.id,
        "request_no": service.request_no,
        "upload_url": build_public_upload_url(service.document_access_token) if service.document_access_token else None,
        "document_request_sent_at": service.document_request_sent_at,
        "status": service.status,
        "customer_documents_approved": customer_documents_approved(db, service),
        "documents": _linked_service_document_summary(db, service),
    }


@router.post("/{complaint_id}/service-request")
def ensure_linked_service_request(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    _assert_callcenter_can_edit(db, user, complaint)
    if (complaint.query_type or "").lower() != "service":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only Service complaints can create linked service requests")
    service = _ensure_service_request_for_complaint(db, complaint, user)
    db.commit()
    db.refresh(service)
    return {
        "service_request_id": service.id,
        "request_no": service.request_no,
        "upload_url": build_public_upload_url(service.document_access_token) if service.document_access_token else None,
        "document_request_sent_at": service.document_request_sent_at,
        "status": service.status,
        "customer_documents_approved": customer_documents_approved(db, service),
        "documents": _linked_service_document_summary(db, service),
    }


@router.post("/{complaint_id}/documents/request-link")
def request_customer_documents(
    complaint_id: int,
    background_tasks: BackgroundTasks,
    resend: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    complaint = _load_visible(db, user, complaint_id)
    # resend=true (sent by the UI only after the user confirms "send again?") may bypass the
    # "link already sent" lock for roles that have the complaints.can_edit permission.
    existing_service = _find_linked_service_request(db, complaint.id)
    is_resend = bool(
        resend
        and existing_service is not None
        and existing_service.document_request_sent_at is not None
        and can_act_on(db, user, "complaints", "can_edit", complaint.query_type)
    )
    if not is_resend:
        _assert_callcenter_can_edit(db, user, complaint)
    if (complaint.query_type or "").lower() != "service":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer upload links are only available for Service complaints")
    if not complaint.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required before generating upload link")
    service = _ensure_service_request_for_complaint(db, complaint, user)
    service.customer_email = complaint.customer_email
    if not is_resend or not service.document_access_token:
        # first send: fresh token (unchanged behaviour); resend keeps the link the customer already has
        service.document_access_token = _generate_service_access_token()
    service.ask_for_documents = True
    service.document_request_sent_at = datetime.now(timezone.utc)
    db.add(
        ComplaintStatusLog(
            complaint_id=complaint.id,
            old_status=complaint.status,
            new_status=complaint.status,
            changed_by=user.id,
            remark="Customer document upload link re-sent" if is_resend else "Customer document upload link generated",
            action_taken="Request Sent",
        )
    )
    db.commit()
    db.refresh(service)
    upload_url = build_public_upload_url(service.document_access_token)
    background_tasks.add_task(
        send_document_upload_link_email,
        complaint.customer_email or "",
        complaint.customer_name,
        complaint.comp_no or service.request_no,
        upload_url,
        customer_document_types(db, service),
    )
    return {
        "service_request_id": service.id,
        "request_no": service.request_no,
        "upload_url": upload_url,
        "document_request_sent_at": service.document_request_sent_at,
        "status": service.status,
        "customer_documents_approved": customer_documents_approved(db, service),
        "documents": _linked_service_document_summary(db, service),
    }


@router.put("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: int,
    body: ComplaintUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = _load_visible(db, user, complaint_id)
    if not can_act_on(db, user, "complaints", "can_edit", c.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this complaint")
    # Editing follows the role permissions (complaints.can_edit, checked above). It is no longer blocked
    # once the upload link is sent, so a misheard email can be corrected and the link resent.

    data = body.model_dump(exclude_unset=True)
    # Block changing query_type to a type the user has no create/edit perm on.
    if "query_type" in data and data["query_type"] != c.query_type:
        if not can_act_on(db, user, "complaints", "can_edit", data["query_type"]):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Your role cannot move this complaint into '{data['query_type']}'",
            )

    old_status = c.status
    new_status = data.pop("status", None)
    assigned_engineer = data.pop("assigned_engineer", None)

    for field, value in data.items():
        setattr(c, field, value)
    _sync_linked_service_contact(db, c, data.keys())

    if assigned_engineer is not None:
        c.assigned_engineer = assigned_engineer
        _sync_linked_service_engineer(db, c)
        _sync_linked_installation_engineer(db, c)

    if new_status is not None and new_status != old_status:
        if new_status not in STATUSES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
        c.status = new_status
        c.status_date = datetime.now(timezone.utc)
        db.add(
            ComplaintStatusLog(
                complaint_id=c.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user.id,
                remark="Updated via complaint edit",
            )
        )

    from app.services.pending_action_sync import sync_complaint_pending_actions

    sync_complaint_pending_actions(db, c)
    db.commit()
    db.refresh(c)
    return ComplaintOut(**_hydrate(db, c))


@router.delete("/{complaint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = _load_visible(db, user, complaint_id)
    if not can_act_on(db, user, "complaints", "can_delete", c.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete this complaint")
    c.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.put("/{complaint_id}/status", response_model=ComplaintOut)
async def update_status(
    complaint_id: int,
    background_tasks: BackgroundTasks,
    new_status: str = Form(...),
    access_code: str | None = Form(None),
    serial_no: str | None = Form(None),
    assigned_engineer: int | None = Form(None),
    remark: str | None = Form(None),
    document: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if new_status not in STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")

    c = _load_visible(db, user, complaint_id)
    if not can_act_on(db, user, "complaints", "can_edit", c.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit this complaint")
    _assert_callcenter_can_edit(db, user, c)

    linked_item = None
    if serial_no:
        linked_item = db.scalar(
            select(OrderItem).where(
                or_(
                    func.lower(OrderItem.serial_no) == func.lower(serial_no),
                    func.lower(OrderItem.serial_no_2) == func.lower(serial_no),
                )
            )
        )
        if linked_item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial number not found")
        c.order_item_id = linked_item.id
        c.serial_no = serial_no.strip()

    if new_status == "Resolved":
        if not access_code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Access code required to resolve")
        if c.access_code and access_code != c.access_code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Access code is incorrect")

    doc_path = None
    if document is not None and document.filename:
        doc_path = await save_upload(document, module="complaints")

    old_status = c.status
    c.status = new_status
    c.status_date = datetime.now(timezone.utc)
    engineer_assigned_id = assigned_engineer
    if assigned_engineer is not None:
        c.assigned_engineer = assigned_engineer
        _sync_linked_service_engineer(db, c)
        _sync_linked_installation_engineer(db, c)
    if remark is not None:
        c.remark = remark
    if doc_path:
        c.service_proof_path = doc_path

    log = ComplaintStatusLog(
        complaint_id=c.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=user.id,
        remark=remark,
        document_path=doc_path,
    )
    db.add(log)
    db.flush()
    if c.serial_no:
        create_serial_history_event(
            db,
            serial_no=c.serial_no,
            serial_no_2=linked_item.serial_no_2 if linked_item else None,
            order_item_id=c.order_item_id,
            event_type=EVENT_TYPES["COMPLAINT"],
            event_subtype="STATUS_CHANGED",
            event_at=c.status_date or datetime.now(timezone.utc),
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="complaint_status_logs",
            source_id=log.id,
            title="Complaint status updated",
            description=f"Complaint {c.comp_no} status changed from {old_status} to {new_status}.",
            remarks=remark,
            metadata={"comp_no": c.comp_no, "old_status": old_status, "new_status": new_status, "document_path": doc_path},
        )
    from app.services.pending_action_sync import sync_complaint_pending_actions

    sync_complaint_pending_actions(db, c)
    db.commit()
    db.refresh(c)
    if engineer_assigned_id is not None:
        engineer = db.get(User, engineer_assigned_id)
        if engineer is not None:
            notify_engineer_complaint_assigned(background_tasks, engineer=engineer, complaint=c)
    return ComplaintOut(**_hydrate(db, c))


@router.post("/{complaint_id}/action", status_code=status.HTTP_201_CREATED)
def record_action(
    complaint_id: int,
    body: ComplaintActionRecord,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = _load_visible(db, user, complaint_id)
    if not can_act_on(db, user, "complaints", "can_edit", c.query_type):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot act on this complaint")
    _assert_callcenter_can_edit(db, user, c)
    if body.action_taken not in ACTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid action")
    log = ComplaintStatusLog(
        complaint_id=c.id,
        old_status=c.status,
        new_status=c.status,
        changed_by=user.id,
        remark=body.remark,
        action_taken=body.action_taken,
    )
    db.add(log)
    db.flush()
    if c.serial_no:
        create_serial_history_event(
            db,
            serial_no=c.serial_no,
            order_item_id=c.order_item_id,
            event_type=EVENT_TYPES["SERVICE"],
            event_subtype="ACTION_RECORDED",
            event_at=datetime.now(timezone.utc),
            performed_by_user_id=user.id,
            performed_by_name=user.name,
            source_table="complaint_status_logs",
            source_id=log.id,
            title="Complaint action recorded",
            description=f"Complaint action recorded: {body.action_taken}.",
            remarks=body.remark,
            metadata={"comp_no": c.comp_no, "action_taken": body.action_taken},
        )
    from app.services.pending_action_sync import sync_complaint_pending_actions

    sync_complaint_pending_actions(db, c)
    db.commit()
    return {"ok": True, "action_taken": body.action_taken}


@router.get("/{complaint_id}/history", response_model=list[ComplaintHistoryEntry])
def history(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _load_visible(db, user, complaint_id)
    logs = db.scalars(
        select(ComplaintStatusLog)
        .where(ComplaintStatusLog.complaint_id == complaint_id)
        .order_by(ComplaintStatusLog.changed_at.desc())
    ).all()
    out: list[ComplaintHistoryEntry] = []
    for log in logs:
        changed_by_name = None
        if log.changed_by:
            u = db.get(User, log.changed_by)
            changed_by_name = u.name if u else None
        out.append(ComplaintHistoryEntry(
            id=log.id,
            old_status=log.old_status,
            new_status=log.new_status,
            changed_by=log.changed_by,
            changed_by_name=changed_by_name,
            remark=log.remark,
            document_path=log.document_path,
            action_taken=log.action_taken,
            changed_at=log.changed_at,
        ))
    return out
