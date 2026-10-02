from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.claim import Claim
from app.models.complaint import Complaint, ComplaintStatusLog
from app.models.installation import InstallationRequest
from app.models.order import Order
from app.models.service import ServiceNotification, ServicePaymentRequest, ServiceRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.services.permissions import can_act_on
from app.services.pending_action_service import (
    get_operations_admin_users,
    get_users_by_roles,
    notify_users,
    resolve_all_for_entity,
    upsert_pending_action,
)
from app.services.payment_approval_workflow import notify_payment_stage


def _coalesce_dt(*values: datetime | None) -> datetime:
    for value in values:
        if value is not None:
            return value
    return _now()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _complaint_users(db: Session, complaint: Complaint) -> list[User]:
    users = db.scalars(
        select(User).where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            func.lower(func.trim(User.role)).in_(
                {"admin", "incool", "indcool", "indcool service", "indcool_service", "service", "callcenter", "sales"}
            ),
        )
    ).all()
    return [
        user for user in users
        if can_act_on(db, user, "complaints", "can_view", complaint.query_type)
    ]


def _vendor_user(db: Session, vendor_id: int | None) -> User | None:
    if vendor_id is None:
        return None
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or not vendor.email:
        return None
    return db.scalar(
        select(User).where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            func.lower(User.email) == vendor.email.strip().lower(),
        )
    )


def _complaint_document_pending(db: Session, complaint_id: int) -> bool:
    link_sent = db.scalar(
        select(func.count()).select_from(ComplaintStatusLog).where(
            ComplaintStatusLog.complaint_id == complaint_id,
            ComplaintStatusLog.action_taken == "Request Sent",
        )
    ) or 0
    if link_sent:
        return False
    asked = db.scalar(
        select(func.count()).select_from(ComplaintStatusLog).where(
            ComplaintStatusLog.complaint_id == complaint_id,
            ComplaintStatusLog.action_taken == "Ask for Invoice",
        )
    ) or 0
    return asked == 0


def sync_complaint_pending_actions(db: Session, complaint: Complaint) -> None:
    if complaint.deleted_at is not None:
        resolve_all_for_entity(db, module="complaints", entity_id=complaint.id)
        return

    resolve_all_for_entity(db, module="complaints", entity_id=complaint.id)
    occurred = _coalesce_dt(complaint.status_date, complaint.updated_at, complaint.created_at)
    title = f"Complaint {complaint.comp_no}"
    href = f"/complaints/{complaint.id}"
    recipients = _complaint_users(db, complaint)

    if complaint.status in {"Pending", "Under Process", "In Process"}:
        notify_users(
            db,
            recipients,
            module="complaints",
            entity_id=complaint.id,
            action_type="triage_complaint",
            title=title,
            message=f"Complaint is {complaint.status}. Review and take action.",
            action_label="Open complaint",
            href=href,
            entity_status=complaint.status,
            occurred_at=occurred,
        )

    if complaint.status in {"Pending", "Under Process", "In Process"} and _complaint_document_pending(db, complaint.id):
        notify_users(
            db,
            recipients,
            module="complaints",
            entity_id=complaint.id,
            action_type="request_documents",
            title=title,
            message="Customer documents have not been requested yet.",
            action_label="Request documents",
            href=href,
            entity_status=complaint.status,
            occurred_at=occurred,
        )

    if complaint.assigned_engineer and complaint.status in {"Under Process", "In Process"}:
        engineer = db.get(User, complaint.assigned_engineer)
        if engineer is not None:
            notify_users(
                db,
                [engineer],
                module="complaints",
                entity_id=complaint.id,
                action_type="work_complaint",
                title=title,
                message=f"Assigned complaint is {complaint.status}.",
                action_label="Open complaint",
                href=href,
                entity_status=complaint.status,
                occurred_at=occurred,
            )


def sync_installation_pending_actions(db: Session, inst: InstallationRequest) -> None:
    resolve_all_for_entity(db, module="installations", entity_id=inst.id)
    if inst.status in {"Completed", "Rejected", "Cancelled"}:
        return

    occurred = _coalesce_dt(inst.updated_at, inst.request_date, inst.created_at)
    title = f"Installation #{inst.id}"
    href = f"/installations/{inst.id}?edit=1"
    ops_users = get_operations_admin_users(db)

    if inst.status == "Admin Review Document":
        notify_users(
            db, ops_users,
            module="installations", entity_id=inst.id, action_type="verify_documents",
            title=title, message="Customer documents need admin review.",
            action_label="Review documents", href=href, entity_status=inst.status, occurred_at=occurred,
        )

    if (inst.source or "").lower() == "callcenter" and not inst.order_verified_at and inst.status in {
        "Pending", "Document Requested", "Admin Review Document", "Order Verified", "Assigned", "Submitted",
    }:
        if not inst.order_verified_at and inst.status not in {"Completed", "Rejected"}:
            callcenter_users = get_users_by_roles(db, {"callcenter"})
            notify_users(
                db, callcenter_users,
                module="installations", entity_id=inst.id, action_type="verify_order",
                title=title, message="Linked order needs verification.",
                action_label="Verify order", href=href, entity_status=inst.status, occurred_at=occurred,
            )

    if inst.status == "Serial Pending Verification":
        notify_users(
            db, ops_users,
            module="installations", entity_id=inst.id, action_type="verify_serial",
            title=title, message="Engineer submitted serial numbers for verification.",
            action_label="Verify serial", href=href, entity_status=inst.status, occurred_at=occurred,
        )

    if inst.status == "Completion Pending Approval":
        notify_users(
            db, ops_users,
            module="installations", entity_id=inst.id, action_type="approve_completion",
            title=title, message="Installation completion is waiting for admin approval.",
            action_label="Approve completion", href=href, entity_status=inst.status, occurred_at=occurred,
        )

    if inst.status == "Payment Pending":
        notify_payment_stage(
            db,
            module="installations", entity_id=inst.id,
            title=title, href=href, entity_status=inst.status,
            stage_key=inst.payment_approval_stage,
            occurred_at=_coalesce_dt(inst.payment_requested_at, occurred),
        )

    if inst.status == "Settlement Pending":
        notify_users(
            db, ops_users,
            module="installations", entity_id=inst.id, action_type="approve_settlement",
            title=title, message="Settlement is pending admin approval.",
            action_label="Approve settlement", href=href, entity_status=inst.status, occurred_at=occurred,
        )

    if inst.assigned_engineer and inst.status in {"Assigned", "In Progress", "Returned"}:
        engineer = db.get(User, inst.assigned_engineer)
        if engineer is not None:
            notify_users(
                db, [engineer],
                module="installations", entity_id=inst.id, action_type="complete_installation",
                title=title, message=f"Installation is {inst.status}. Complete work and submit proof.",
                action_label="Complete installation", href=href, entity_status=inst.status, occurred_at=occurred,
            )

    if inst.assigned_engineer and inst.status == "Installation Completed":
        engineer = db.get(User, inst.assigned_engineer)
        if engineer is not None:
            notify_users(
                db, [engineer],
                module="installations", entity_id=inst.id, action_type="raise_payment",
                title=title, message="Admin approved completion. Raise payment request.",
                action_label="Raise payment", href=href, entity_status=inst.status, occurred_at=occurred,
            )

    if (inst.source or "").lower() == "vendor" and inst.status in {"Submitted", "Assigned"} and not inst.serial_verified_at:
        order = db.get(Order, inst.order_id) if inst.order_id else None
        vendor_user = _vendor_user(db, order.vendor_id if order else None)
        if vendor_user is not None:
            notify_users(
                db, [vendor_user],
                module="installations", entity_id=inst.id, action_type="assign_engineer",
                title=title, message="Assign an engineer for this installation.",
                action_label="Assign engineer", href=href, entity_status=inst.status, occurred_at=occurred,
            )


def sync_service_pending_actions(db: Session, service: ServiceRequest) -> None:
    resolve_all_for_entity(db, module="services", entity_id=service.id)
    if service.deleted_at is not None or service.status in {"Closed", "Cancelled", "Rejected"}:
        return

    occurred = _coalesce_dt(service.status_date, service.updated_at, service.created_at)
    title = f"Service {service.request_no}"
    href = f"/services/{service.id}"
    ops_users = get_operations_admin_users(db)

    if service.status in {"New", "Service Team Review"} and not service.assigned_engineer_id and not service.assigned_vendor_id:
        notify_users(
            db, ops_users,
            module="services", entity_id=service.id, action_type="assign_service",
            title=title, message="Service request is unassigned.",
            action_label="Assign service", href=href, entity_status=service.status, occurred_at=occurred,
        )

    if service.status == "Serial Verification Review":
        notify_users(
            db, ops_users,
            module="services", entity_id=service.id, action_type="verify_serial",
            title=title, message="Serial verification is pending admin review.",
            action_label="Review serial", href=href, entity_status=service.status, occurred_at=occurred,
        )

    if service.status == "Pending Service Approval":
        notify_users(
            db, ops_users,
            module="services", entity_id=service.id, action_type="approve_service",
            title=title, message="Service observation is pending approval.",
            action_label="Approve service", href=href, entity_status=service.status, occurred_at=occurred,
        )

    if service.status == "Completion Pending Approval":
        notify_users(
            db, ops_users,
            module="services", entity_id=service.id, action_type="approve_completion",
            title=title, message="Service completion is pending approval.",
            action_label="Approve completion", href=href, entity_status=service.status, occurred_at=occurred,
        )

    if service.status == "Payment Requested":
        latest_payment = db.scalar(
            select(ServicePaymentRequest)
            .where(ServicePaymentRequest.service_request_id == service.id)
            .order_by(ServicePaymentRequest.created_at.desc())
        )
        notify_payment_stage(
            db,
            module="services", entity_id=service.id,
            title=title, href=href, entity_status=service.status, occurred_at=occurred,
            stage_key=latest_payment.approval_stage if latest_payment else None,
            entity_ref=str(latest_payment.id) if latest_payment else "",
        )

    if service.assigned_engineer_id and service.status in {"Assigned", "Engineer Visit", "Service In Progress", "Approved for Service"}:
        engineer = db.get(User, service.assigned_engineer_id)
        if engineer is not None:
            notify_users(
                db, [engineer],
                module="services", entity_id=service.id, action_type="complete_service",
                title=title, message=f"Service is {service.status}. Continue engineer workflow.",
                action_label="Open service", href=href, entity_status=service.status, occurred_at=occurred,
            )

    if service.assigned_engineer_id and service.status == "Service Completed":
        engineer = db.get(User, service.assigned_engineer_id)
        if engineer is not None:
            notify_users(
                db, [engineer],
                module="services", entity_id=service.id, action_type="raise_payment",
                title=title, message="Service completed. Raise payment request.",
                action_label="Raise payment", href=href, entity_status=service.status, occurred_at=occurred,
            )

    if service.assigned_vendor_id and service.status in {"Assigned", "Engineer Visit", "Service In Progress", "Service Completed"}:
        vendor_user = _vendor_user(db, service.assigned_vendor_id)
        if vendor_user is not None:
            action_type = "raise_payment" if service.status == "Service Completed" else "complete_service"
            action_label = "Raise payment" if service.status == "Service Completed" else "Open service"
            message = (
                "Service completed. Raise payment request."
                if service.status == "Service Completed"
                else f"Vendor service is {service.status}."
            )
            notify_users(
                db, [vendor_user],
                module="services", entity_id=service.id, action_type=action_type,
                title=title, message=message,
                action_label=action_label, href=href, entity_status=service.status, occurred_at=occurred,
            )


def sync_order_pending_actions(db: Session, order: Order) -> None:
    resolve_all_for_entity(db, module="orders", entity_id=order.id)
    if order.deleted_at is not None or order.status in {"Delivered", "Returned", "Cancelled"}:
        return

    vendor_user = _vendor_user(db, order.vendor_id)
    if vendor_user is None:
        return

    occurred = _coalesce_dt(order.updated_at, order.created_at)
    title = f"Order {order.order_no or order.id}"
    href = f"/orders/{order.id}"

    if order.status == "Pending":
        notify_users(
            db, [vendor_user],
            module="orders", entity_id=order.id, action_type="fulfill_order",
            title=title, message="Order is pending fulfillment.",
            action_label="Fulfill order", href=href, entity_status=order.status, occurred_at=occurred,
        )
    elif order.status in {"Shipped", "In Transit"}:
        notify_users(
            db, [vendor_user],
            module="orders", entity_id=order.id, action_type="update_shipment",
            title=title, message=f"Order is {order.status}. Update shipment details.",
            action_label="Update shipment", href=href, entity_status=order.status, occurred_at=occurred,
        )


def sync_claim_pending_actions(db: Session, claim: Claim) -> None:
    resolve_all_for_entity(db, module="claims", entity_id=claim.id)
    if claim.status != "Processing":
        return

    occurred = _coalesce_dt(claim.updated_at, claim.submitted_at, claim.created_at)
    notify_users(
        db,
        get_operations_admin_users(db),
        module="claims",
        entity_id=claim.id,
        action_type="process_claim",
        title=f"Claim {claim.claim_id}",
        message="Claim is awaiting processing.",
        action_label="Process claim",
        href=f"/claims/{claim.id}",
        entity_status=claim.status,
        occurred_at=occurred,
    )


def sync_call_pending_actions(db: Session, call: Call) -> None:
    resolve_all_for_entity(db, module="calls", entity_id=call.id)
    if (call.follow_up_status or "").strip().lower() != "pending":
        return

    occurred = _coalesce_dt(call.followup_date, call.updated_at, call.created_at)
    recipients: list[User] = []
    if call.assigned_to:
        user = db.get(User, call.assigned_to)
        if user is not None:
            recipients.append(user)
    if not recipients:
        recipients = get_operations_admin_users(db)

    notify_users(
        db,
        recipients,
        module="calls",
        entity_id=call.id,
        action_type="follow_up_call",
        title=f"Call {call.ref_no}",
        message="Follow-up call is pending.",
        action_label="Open call",
        href=f"/calls/{call.id}",
        entity_status=call.follow_up_status or "Pending",
        occurred_at=occurred,
    )


def migrate_service_notifications(db: Session) -> None:
    rows = db.scalars(
        select(ServiceNotification).where(ServiceNotification.is_read.is_(False))
    ).all()
    for row in rows:
        if row.recipient_user_id is None:
            continue
        upsert_pending_action(
            db,
            recipient_user_id=row.recipient_user_id,
            recipient_vendor_id=row.recipient_vendor_id,
            module="services",
            entity_id=row.service_request_id,
            action_type=f"legacy_{row.notification_type}",
            title=row.title,
            message=row.message,
            action_label="Open service",
            href=f"/services/{row.service_request_id}",
            entity_status="Notification",
            occurred_at=_coalesce_dt(row.updated_at, row.created_at),
        )
        row.is_read = True
        db.flush()


def backfill_all_pending_actions(db: Session) -> dict[str, int]:
    counts = {"complaints": 0, "installations": 0, "services": 0, "orders": 0, "claims": 0, "calls": 0}
    migrate_service_notifications(db)
    db.commit()

    for complaint in db.scalars(select(Complaint).where(Complaint.deleted_at.is_(None))):
        sync_complaint_pending_actions(db, complaint)
        counts["complaints"] += 1
    db.commit()

    for inst in db.scalars(select(InstallationRequest)):
        sync_installation_pending_actions(db, inst)
        counts["installations"] += 1
    db.commit()

    for service in db.scalars(select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))):
        sync_service_pending_actions(db, service)
        counts["services"] += 1
    db.commit()

    for order in db.scalars(select(Order).where(Order.deleted_at.is_(None))):
        sync_order_pending_actions(db, order)
        counts["orders"] += 1
    db.commit()

    for claim in db.scalars(select(Claim)):
        sync_claim_pending_actions(db, claim)
        counts["claims"] += 1
    db.commit()

    for call in db.scalars(select(Call)):
        sync_call_pending_actions(db, call)
        counts["calls"] += 1
    db.commit()

    return counts
