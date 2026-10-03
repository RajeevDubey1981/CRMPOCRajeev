"""Domain workflow email notifications for engineers, customers, and vendors."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.order import Order
from app.models.service import ServiceRequest, ServiceRequestUnit
from app.models.user import User
from app.models.vendor import Vendor
from sqlalchemy import select
from app.services.email_service import (
    HELPDESK_EMAIL,
    TOLL_FREE_NUMBER,
    send_service_happy_code_email,
    send_service_rejection_document_request_email,
    send_template_email,
)
from app.services.service_whatsapp import send_service_happy_code_whatsapp
from app.services.service_documents import (
    build_public_upload_url,
    customer_document_types,
    mark_latest_customer_documents_for_resubmission,
    reset_service_downstream_workflow_for_documents,
)

logger = logging.getLogger(__name__)

CUSTOMER_SERVICE_STATUSES = {
    "Closed",
}


def _from_name() -> str:
    return (settings.smtp_from_name or "").strip() or "INDcool Service Team"


def _details_html(rows: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, value in rows:
        if not value:
            continue
        parts.append(
            "<tr>"
            f'<td style="padding:6px 8px;border:1px solid #e2e8f0;color:#64748b;">{label}</td>'
            f'<td style="padding:6px 8px;border:1px solid #e2e8f0;"><strong>{value}</strong></td>'
            "</tr>"
        )
    return "".join(parts)


def _send_workflow_email(
    to: str | None,
    *,
    recipient_name: str,
    subject: str,
    intro: str,
    details: list[tuple[str, str]] | None = None,
    extra_message: str | None = None,
) -> bool:
    email = (to or "").strip()
    if not email:
        return False
    details_html = _details_html(details or [])
    extra_message_html = f"<p>{extra_message}</p>" if extra_message else ""
    text_lines = [f"Dear {recipient_name},", "", intro, ""]
    for label, value in details or []:
        if value:
            text_lines.append(f"{label}: {value}")
    if extra_message:
        text_lines.extend(["", extra_message])
    text_lines.extend(
        [
            "",
            f"For assistance, contact {HELPDESK_EMAIL} or call {TOLL_FREE_NUMBER}.",
            "",
            f"Thank you,\n{_from_name()}",
        ]
    )
    return send_template_email(
        to=email,
        template="workflow_update",
        context={
            "recipient_name": recipient_name,
            "intro": intro,
            "details_html": details_html,
            "extra_message_html": extra_message_html,
            "helpdesk_email": HELPDESK_EMAIL,
            "toll_free_number": TOLL_FREE_NUMBER,
            "from_name": _from_name(),
            "text_body": "\n".join(text_lines),
        },
        subject=subject,
    )


def _queue(background_tasks: BackgroundTasks | None, func, *args, **kwargs) -> None:
    if background_tasks is None:
        func(*args, **kwargs)
        return
    background_tasks.add_task(func, *args, **kwargs)


def notify_customer_service_status(
    background_tasks: BackgroundTasks | None,
    service: ServiceRequest,
    *,
    old_status: str | None,
    new_status: str | None,
    remarks: str | None = None,
) -> None:
    if not service.customer_email:
        return
    status = (new_status or service.status or "").strip()
    if status not in CUSTOMER_SERVICE_STATUSES:
        return
    if old_status == status:
        return
    ticket = (service.request_no or "").strip() or str(service.id)
    if status == "Closed":
        intro = (
            "Greetings from INDcool! Your service request has been completed and closed. "
            "Thank you for choosing INDcool."
        )
    else:
        intro = (
            "Greetings from INDcool! This is a system-generated update on your service request. "
            "One of our service experts is working on your request."
        )
    details = [
        ("Ticket ID", ticket),
        ("Previous Status", old_status or "—"),
        ("Current Status", status),
    ]
    if remarks:
        details.append(("Remarks", remarks))
    _queue(
        background_tasks,
        _send_workflow_email,
        service.customer_email,
        recipient_name=(service.customer_name or "").strip() or "Sir/Ma'am",
        subject=f"Service request update — Ticket ID: {ticket}",
        intro=intro,
        details=details,
    )


def notify_customer_happy_code(
    background_tasks: BackgroundTasks | None,
    service: ServiceRequest,
    *,
    completion_code: str,
) -> None:
    if service.customer_email:
        _queue(
            background_tasks,
            send_service_happy_code_email,
            service.customer_email,
            service_id=service.id,
            completion_code=completion_code,
        )
    if service.customer_mobile:
        _queue(
            background_tasks,
            send_service_happy_code_whatsapp,
            service.customer_mobile,
            customer_name=(service.customer_name or "").strip() or None,
            service_code=str(service.id),
            completion_code=completion_code,
        )


def notify_engineer_service_assigned(
    background_tasks: BackgroundTasks | None,
    *,
    engineer: User,
    service: ServiceRequest,
    order_no: str | None = None,
    remarks: str | None = None,
) -> None:
    if not engineer.email:
        return
    ticket = (service.request_no or "").strip() or str(service.id)
    details = [
        ("Ticket ID", ticket),
        ("Customer", service.customer_name or "—"),
        ("Mobile", service.customer_mobile or "—"),
        ("Address", service.customer_address or "—"),
    ]
    if order_no:
        details.insert(1, ("Order No", order_no))
    if remarks:
        details.append(("Remarks", remarks))
    _queue(
        background_tasks,
        _send_workflow_email,
        engineer.email,
        recipient_name=(engineer.name or "").strip() or "Engineer",
        subject=f"New service assignment — {ticket}",
        intro="You have been assigned a service request. Please log in to Indcool CRM to review and take action.",
        details=details,
        extra_message=f"Service details: {(service.problem_description or '—').strip()}",
    )


def notify_vendor_service_assigned(
    background_tasks: BackgroundTasks | None,
    *,
    vendor: Vendor,
    service: ServiceRequest,
    remarks: str | None = None,
) -> None:
    if not vendor.email:
        return
    ticket = (service.request_no or "").strip() or str(service.id)
    details = [
        ("Ticket ID", ticket),
        ("Customer", service.customer_name or "—"),
        ("Mobile", service.customer_mobile or "—"),
    ]
    if remarks:
        details.append(("Remarks", remarks))
    _queue(
        background_tasks,
        _send_workflow_email,
        vendor.email,
        recipient_name=(vendor.contact_name or vendor.name_of_firm or "").strip() or "Vendor",
        subject=f"Service request assigned — {ticket}",
        intro="A service request has been assigned to your firm. Please log in to Indcool CRM for details.",
        details=details,
    )


def notify_engineer_approval_decision(
    background_tasks: BackgroundTasks | None,
    *,
    engineer: User,
    service: ServiceRequest,
    decision: str,
    remarks: str | None = None,
) -> None:
    if not engineer.email:
        return
    ticket = (service.request_no or "").strip() or str(service.id)
    label = "approved" if decision == "Approve" else "rejected"
    details = [
        ("Ticket ID", ticket),
        ("Decision", decision),
        ("Current Status", service.status or "—"),
    ]
    if remarks:
        details.append(("Remarks", remarks))
    _queue(
        background_tasks,
        _send_workflow_email,
        engineer.email,
        recipient_name=(engineer.name or "").strip() or "Engineer",
        subject=f"Service request {label} — {ticket}",
        intro=f"Your service observation/request for ticket {ticket} has been {label} by the service team.",
        details=details,
    )


def notify_customer_service_approval(
    background_tasks: BackgroundTasks | None,
    service: ServiceRequest,
    *,
    decision: str,
    remarks: str | None = None,
) -> None:
    if not service.customer_email:
        return
    ticket = (service.request_no or "").strip() or str(service.id)
    if decision == "Approve":
        intro = (
            "Greetings from INDcool! Your service request has been reviewed and approved for service. "
            "Our team will proceed with the next steps shortly."
        )
        status_label = "Approved for Service"
    else:
        intro = (
            "Greetings from INDcool! Your service request has been reviewed. "
            "Please see the update below for more information."
        )
        status_label = "Rejected"
    details = [
        ("Ticket ID", ticket),
        ("Status", status_label),
    ]
    if remarks:
        details.append(("Remarks", remarks))
    _queue(
        background_tasks,
        _send_workflow_email,
        service.customer_email,
        recipient_name=(service.customer_name or "").strip() or "Sir/Ma'am",
        subject=f"Service request update — Ticket ID: {ticket}",
        intro=intro,
        details=details,
    )


def notify_customer_order_delivered(
    background_tasks: BackgroundTasks | None,
    order: Order,
) -> None:
    if not order.customer_email:
        return
    order_no = (order.order_no or "").strip() or str(order.id)
    details = [
        ("Order No", order_no),
        ("Status", "Delivered"),
    ]
    if order.actual_delivery_date:
        details.append(("Delivery Date", order.actual_delivery_date.isoformat()))
    _queue(
        background_tasks,
        _send_workflow_email,
        order.customer_email,
        recipient_name=(order.customer_name or "").strip() or "Sir/Ma'am",
        subject=f"Order delivered — {order_no}",
        intro=(
            "Greetings from INDcool! We are pleased to inform you that your order has been delivered. "
            "Thank you for choosing INDcool."
        ),
        details=details,
        extra_message="Please retain your order number for future communication regarding installation or service.",
    )


def notify_vendor_order_update(
    background_tasks: BackgroundTasks | None,
    *,
    vendor: Vendor,
    order: Order,
    changed_fields: dict[str, Any],
    actor_label: str = "Indcool",
) -> None:
    if not vendor.email or not changed_fields:
        return
    order_no = (order.order_no or "").strip() or str(order.id)
    details = [("Order No", order_no), ("Updated By", actor_label)]
    for field, value in changed_fields.items():
        if isinstance(value, dict) and "from" in value and "to" in value:
            details.append((field.replace("_", " ").title(), f"{value['from'] or '—'} → {value['to'] or '—'}"))
        else:
            details.append((field.replace("_", " ").title(), str(value)))
    _queue(
        background_tasks,
        _send_workflow_email,
        vendor.email,
        recipient_name=(vendor.contact_name or vendor.name_of_firm or "").strip() or "Vendor",
        subject=f"Order update — {order_no}",
        intro="There is an update on your order in Indcool CRM. Please review the details below.",
        details=details,
    )


def notify_vendor_new_order(
    background_tasks: BackgroundTasks | None,
    *,
    vendor: Vendor,
    order: Order,
) -> None:
    if not vendor.email:
        return
    order_no = (order.order_no or "").strip() or str(order.id)
    _queue(
        background_tasks,
        _send_workflow_email,
        vendor.email,
        recipient_name=(vendor.contact_name or vendor.name_of_firm or "").strip() or "Vendor",
        subject=f"New order assigned — {order_no}",
        intro="A new order has been assigned to your firm. Please log in to Indcool CRM to review and process it.",
        details=[
            ("Order No", order_no),
            ("Status", order.status or "Pending"),
            ("Customer", order.customer_name or "—"),
        ],
    )


def notify_engineer_installation_assigned(
    background_tasks: BackgroundTasks | None,
    *,
    engineer: User,
    installation_ids: list[int],
    order_nos: list[str],
) -> None:
    if not engineer.email or not installation_ids:
        return
    count = len(installation_ids)
    order_summary = ", ".join(sorted({no for no in order_nos if no})) or "—"
    _queue(
        background_tasks,
        _send_workflow_email,
        engineer.email,
        recipient_name=(engineer.name or "").strip() or "Engineer",
        subject=f"Installation assignment — {count} request(s)",
        intro=f"You have been assigned {count} installation request(s). Please log in to Indcool CRM to review them.",
        details=[
            ("Assignments", str(count)),
            ("Order No(s)", order_summary),
            ("Installation IDs", ", ".join(str(i) for i in installation_ids)),
        ],
    )


def notify_customer_installation_update(
    background_tasks: BackgroundTasks | None,
    *,
    order: Order,
    installation: InstallationRequest,
    old_status: str | None,
    new_status: str,
) -> None:
    if not order.customer_email:
        return
    if new_status not in {"Assigned", "In Progress", "Completed"}:
        return
    if old_status == new_status:
        return
    order_no = (order.order_no or "").strip() or str(order.id)
    _queue(
        background_tasks,
        _send_workflow_email,
        order.customer_email,
        recipient_name=(order.customer_name or "").strip() or "Sir/Ma'am",
        subject=f"Installation update — Order {order_no}",
        intro="Greetings from INDcool! There is an update on your installation request.",
        details=[
            ("Order No", order_no),
            ("Previous Status", old_status or "—"),
            ("Current Status", new_status),
            ("Product", installation.product_name or "—"),
        ],
    )


def notify_engineer_complaint_assigned(
    background_tasks: BackgroundTasks | None,
    *,
    engineer: User,
    complaint: Complaint,
) -> None:
    if not engineer.email:
        return
    ref = (complaint.comp_no or "").strip() or str(complaint.id)
    _queue(
        background_tasks,
        _send_workflow_email,
        engineer.email,
        recipient_name=(engineer.name or "").strip() or "Engineer",
        subject=f"Complaint assigned — {ref}",
        intro="A complaint has been assigned to you. Please log in to Indcool CRM to review and take action.",
        details=[
            ("Reference No", ref),
            ("Customer", complaint.customer_name or "—"),
            ("Mobile", complaint.customer_mobile or "—"),
            ("Type", complaint.query_type or "—"),
            ("Status", complaint.status or "—"),
        ],
        extra_message=(complaint.problem_description or "").strip() or None,
    )


def resolve_service_engineer(db: Session, service: ServiceRequest) -> User | None:
    engineer_id = service.assigned_engineer_id
    if engineer_id is None:
        unit = db.scalar(
            select(ServiceRequestUnit)
            .where(
                ServiceRequestUnit.service_request_id == service.id,
                ServiceRequestUnit.assigned_engineer_id.is_not(None),
            )
            .limit(1)
        )
        engineer_id = unit.assigned_engineer_id if unit else None
    if engineer_id is None:
        return None
    engineer = db.get(User, engineer_id)
    if engineer is None or engineer.deleted_at is not None or not engineer.is_active:
        return None
    return engineer


def after_service_status_change(
    background_tasks: BackgroundTasks | None,
    db: Session,
    service: ServiceRequest,
    *,
    old_status: str | None,
    remarks: str | None = None,
) -> None:
    notify_customer_service_status(
        background_tasks,
        service,
        old_status=old_status,
        new_status=service.status,
        remarks=remarks,
    )


def after_service_approval(
    background_tasks: BackgroundTasks | None,
    db: Session,
    service: ServiceRequest,
    *,
    decision: str,
    remarks: str | None = None,
) -> None:
    engineer = resolve_service_engineer(db, service)
    if engineer is not None:
        notify_engineer_approval_decision(
            background_tasks,
            engineer=engineer,
            service=service,
            decision=decision,
            remarks=remarks,
        )
    if decision != "Reject":
        return

    mark_latest_customer_documents_for_resubmission(db, service, remarks=remarks)
    reset_service_downstream_workflow_for_documents(db, service)
    service.document_access_token = secrets.token_urlsafe(24)
    service.ask_for_documents = True
    service.document_request_sent_at = service.status_date or datetime.now(timezone.utc)
    service.status = "Admin Review Document"
    service.status_date = service.document_request_sent_at
    db.commit()
    db.refresh(service)

    upload_url = build_public_upload_url(service.document_access_token)
    required_documents = customer_document_types(db, service)
    if background_tasks is not None:
        background_tasks.add_task(
            send_service_rejection_document_request_email,
            to=service.customer_email or "",
            customer_name=service.customer_name,
            ticket_id=service.request_no,
            upload_url=upload_url,
            reason=remarks,
            required_documents=required_documents,
        )
    else:
        send_service_rejection_document_request_email(
            to=service.customer_email or "",
            customer_name=service.customer_name,
            ticket_id=service.request_no,
            upload_url=upload_url,
            reason=remarks,
            required_documents=required_documents,
        )
