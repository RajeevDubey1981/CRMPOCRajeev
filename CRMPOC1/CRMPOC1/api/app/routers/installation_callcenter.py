"""Call-center installation workflow API endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.installation import InstallationDocument, InstallationEngineerSerial, InstallationRequest, InstallationStatusLog
from app.models.order import Order
from app.models.user import User
from app.schemas.installation import (
    InstallationDocumentOut,
    InstallationEngineerSerialFinalizeRequest,
    InstallationEngineerSerialOut,
    InstallationEngineerSerialRequest,
    InstallationEngineerSerialSubmitRequest,
    InstallationHistoryEntry,
    InstallationOrderSearchResult,
    InstallationOut,
    InstallationPublicDocumentContext,
    InstallationVerifyOrderRequest,
    InstallationVerifySerialRequest,
)
from app.services.email_service import send_document_upload_link_email
from app.services.file_service import read_upload_bytes, save_upload, to_public_upload_path
from app.services.role_access import is_operations_admin
from app.services.installation_workflow import (
    BILLING_TYPES,
    CUSTOMER_DOCUMENT_OPTIONS,
    apply_verified_serial_to_installation,
    associate_serial_with_order,
    document_upload_url,
    ensure_document_token,
    find_order_item_by_serial_on_order,
    is_callcenter_source,
    prepare_vendor_installation_for_engineer_workflow,
    return_installation_to_engineer_for_rework,
    supports_engineer_installation_workflow,
    log_installation_action,
    now_utc,
    split_installations_from_approved_serials,
    apply_installation_workflow_step,
    sync_callcenter_order_item_on_completion,
    validate_customer_document_upload,
    installation_completion_proofs_complete,
    installation_requires_second_serial_proof,
    replace_completion_proof_serial_2,
    sync_order_item_for_service_eligibility,
)
from app.services.permissions import can_act_on
from app.services.payment_approval_workflow import approval_stage_payload, first_payment_stage, notify_payment_stage

router = APIRouter(tags=["installations"])

ENGINEER_UNIT_STATUSES = {"Installed", "In Progress", "Issue Found", "Pending"}
ENGINEER_SUBMIT_STATUSES = {"Assigned", "In Progress", "Serial Pending Verification"}


def _serial_out(row: InstallationEngineerSerial) -> InstallationEngineerSerialOut:
    return InstallationEngineerSerialOut(
        id=row.id,
        line_no=row.line_no,
        serial_no=row.serial_no,
        serial_no_2=row.serial_no_2,
        observation=row.observation,
        unit_status=row.unit_status,
        verification_status=row.verification_status,
        admin_remark=row.admin_remark,
        verified_at=row.verified_at,
        submitted_at=row.submitted_at,
    )


def _list_engineer_serials(db: Session, installation_id: int) -> list[InstallationEngineerSerialOut]:
    rows = db.scalars(
        select(InstallationEngineerSerial)
        .where(InstallationEngineerSerial.installation_request_id == installation_id)
        .order_by(InstallationEngineerSerial.line_no, InstallationEngineerSerial.id)
    ).all()
    return [_serial_out(row) for row in rows]


def _split_installation_group(db: Session, inst: InstallationRequest) -> list[InstallationRequest]:
    parent_id = inst.parent_installation_id or inst.id
    rows = db.scalars(
        select(InstallationRequest).where(
            or_(
                InstallationRequest.id == parent_id,
                InstallationRequest.parent_installation_id == parent_id,
            )
        )
    ).all()
    return sorted(rows, key=lambda row: (row.parent_installation_id is not None, row.id))


def _is_callcenter_user(user: User) -> bool:
    return (user.role or "").lower() == "callcenter"


def _hydrate_callcenter(db: Session, inst: InstallationRequest) -> dict:
    from app.routers.installations import _hydrate

    return _hydrate(db, inst)


@router.get("/orders/search", response_model=list[InstallationOrderSearchResult])
def search_orders_for_installation(
    mobile: str | None = None,
    name: str | None = None,
    order_no: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (_is_callcenter_user(user) or is_operations_admin(user)):
        return []
    stmt = select(Order).where(Order.deleted_at.is_(None))
    terms = []
    if mobile and mobile.strip():
        terms.append(Order.customer_contact.ilike(f"%{mobile.strip()}%"))
    if name and name.strip():
        terms.append(Order.customer_name.ilike(f"%{name.strip()}%"))
    if order_no and order_no.strip():
        terms.append(Order.order_no.ilike(f"%{order_no.strip()}%"))
    if not terms:
        return []
    stmt = stmt.where(or_(*terms)).order_by(desc(Order.created_at)).limit(20)
    return [
        InstallationOrderSearchResult(
            order_id=row.id,
            order_no=row.order_no,
            customer_name=row.customer_name,
            customer_mobile=row.customer_contact,
            customer_email=row.customer_email,
            customer_address=row.customer_address,
        )
        for row in db.scalars(stmt).all()
    ]


@router.get("/public/{token}", response_model=InstallationPublicDocumentContext)
def public_upload_context(token: str, db: Session = Depends(get_db)):
    inst = db.scalar(
        select(InstallationRequest).where(InstallationRequest.document_access_token == token)
    )
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload link not found")
    order_no, _ = None, inst.order_id
    if inst.order_id:
        order = db.get(Order, inst.order_id)
        order_no = order.order_no if order else None
    return InstallationPublicDocumentContext(
        installation_request_id=inst.id,
        request_no=f"INST-{inst.id}",
        customer_name=inst.customer_name,
        customer_email=inst.customer_email,
        model_details=inst.product_name,
        order_no=order_no,
        serial_no=inst.serial_no,
        serial_no_locked=bool((inst.serial_no or "").strip()),
        problem_description=None,
        required_documents=CUSTOMER_DOCUMENT_OPTIONS,
        status=inst.status,
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
    inst = db.scalar(
        select(InstallationRequest).where(InstallationRequest.document_access_token == token)
    )
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload link not found")
    validate_customer_document_upload(document_type, file)
    path = await save_upload(file, module="installations")
    old_status = inst.status
    db.add(
        InstallationDocument(
            installation_request_id=inst.id,
            document_type=document_type,
            file_path=path,
            uploaded_by_type="customer",
            uploaded_by_customer_name=customer_name,
            status="Uploaded",
            uploaded_at=now_utc(),
        )
    )
    if inst.status in {"Pending", "Document Requested"}:
        inst.status = "Admin Review Document"
    if serial_no and serial_no.strip() and not (inst.serial_no or "").strip():
        inst.engineer_entered_serial_no = serial_no.strip()
    log_installation_action(
        db,
        inst,
        action="Customer Document Uploaded",
        old_status=old_status,
        new_status=inst.status,
        performed_role="customer",
        remarks=document_type,
        metadata={"document_type": document_type, "file_path": path},
    )
    db.commit()
    return {"ok": True, "installation_request_id": inst.id, "message": "Documents uploaded successfully"}


@router.get("/{installation_id}/documents", response_model=list[InstallationDocumentOut])
def list_documents(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst) and not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Documents are only available for call-center installations")
    rows = db.scalars(
        select(InstallationDocument)
        .where(InstallationDocument.installation_request_id == inst.id)
        .order_by(desc(InstallationDocument.uploaded_at))
    ).all()
    return [
        InstallationDocumentOut(
            id=row.id,
            document_type=row.document_type,
            file_path=to_public_upload_path(row.file_path) or row.file_path,
            uploaded_by_type=row.uploaded_by_type,
            uploaded_by_customer_name=row.uploaded_by_customer_name,
            status=row.status,
            uploaded_at=row.uploaded_at,
            review_remarks=row.review_remarks,
        )
        for row in rows
    ]


@router.post("/{installation_id}/documents/request-link", response_model=dict)
def request_document_link(
    installation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can request documents")
    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Document upload links are only for call-center installations")
    if not inst.customer_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer email is required before sending upload link")
    token = ensure_document_token(inst)
    inst.ask_for_documents = True
    inst.document_request_sent_at = now_utc()
    old_status = inst.status
    if inst.status == "Pending":
        inst.status = "Document Requested"
    upload_url = document_upload_url(inst) or ""
    log_installation_action(
        db,
        inst,
        action="Documents Requested",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        metadata={"upload_url": upload_url},
    )
    db.commit()
    background_tasks.add_task(
        send_document_upload_link_email,
        inst.customer_email or "",
        inst.customer_name,
        f"INST-{inst.id}",
        upload_url,
        CUSTOMER_DOCUMENT_OPTIONS,
    )
    return {
        "installation_request_id": inst.id,
        "upload_url": upload_url,
        "document_request_sent_at": inst.document_request_sent_at,
        "status": inst.status,
    }


@router.post("/{installation_id}/verify-order", response_model=InstallationOut)
def verify_order(
    installation_id: int,
    body: InstallationVerifyOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can verify orders")
    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order verification applies only to call-center installations")
    order = db.get(Order, body.order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    old_status = inst.status
    inst.order_id = order.id
    inst.order_verified_at = now_utc()
    inst.order_verified_by = user.id
    inst.customer_name = order.customer_name or inst.customer_name
    inst.contact_number = order.customer_contact or inst.contact_number
    inst.customer_email = order.customer_email or inst.customer_email
    inst.address = order.customer_address or inst.address
    inst.status = "Order Verified"
    log_installation_action(
        db,
        inst,
        action="Order Verified",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=f"Order {order.order_no} verified",
        metadata={"order_id": order.id, "order_no": order.order_no},
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.get("/{installation_id}/engineer-serials", response_model=list[InstallationEngineerSerialOut])
def list_engineer_serials(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Engineer serials are only for call-center installations")
    return _list_engineer_serials(db, inst.id)


@router.post("/{installation_id}/engineer-serials/submit", response_model=dict)
def submit_engineer_serials(
    installation_id: int,
    body: InstallationEngineerSerialSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if user.role != "engineer" or inst.assigned_engineer != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the assigned engineer can submit serial numbers")
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Engineer serial entry is only for call-center installations")
    if inst.serial_verified_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial numbers are already verified")
    if inst.status not in ENGINEER_SUBMIT_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serials can be submitted only while Assigned or In Progress")

    cleaned = []
    for idx, line in enumerate(body.serials, start=1):
        serial = (line.serial_no or "").strip()
        if not serial:
            continue
        unit_status = (line.unit_status or "Installed").strip()
        if unit_status not in ENGINEER_UNIT_STATUSES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid unit status: {unit_status}")
        cleaned.append(
            InstallationEngineerSerial(
                installation_request_id=inst.id,
                line_no=idx,
                serial_no=serial,
                serial_no_2=(line.serial_no_2 or "").strip() or None,
                observation=(line.observation or "").strip() or None,
                unit_status=unit_status,
                verification_status="Pending",
                submitted_by=user.id,
                submitted_at=now_utc(),
            )
        )
    if not cleaned:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add at least one serial number")

    old_status = inst.status
    existing = db.scalars(
        select(InstallationEngineerSerial).where(InstallationEngineerSerial.installation_request_id == inst.id)
    ).all()
    for row in existing:
        if row.verification_status != "Approved":
            db.delete(row)

    for row in cleaned:
        db.add(row)

    first = cleaned[0]
    inst.engineer_entered_serial_no = first.serial_no
    inst.engineer_entered_serial_no_2 = first.serial_no_2
    inst.engineer_site_remarks = (body.site_remarks or "").strip() or None
    inst.engineer_serials_submitted_at = now_utc()
    if body.status and body.status.strip() in {"Assigned", "In Progress"}:
        inst.status = body.status.strip()
    elif inst.status == "Assigned":
        inst.status = "In Progress"
    inst.status = "Serial Pending Verification"

    log_installation_action(
        db,
        inst,
        action="Engineer Serials Submitted",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=inst.engineer_site_remarks,
        metadata={
            "serial_count": len(cleaned),
            "serials": [row.serial_no for row in cleaned],
        },
    )
    db.commit()
    db.refresh(inst)
    return {
        "installation_request_id": inst.id,
        "status": inst.status,
        "serials": _list_engineer_serials(db, inst.id),
    }


@router.post("/{installation_id}/engineer-serials/finalize", response_model=InstallationOut)
def finalize_engineer_serials(
    installation_id: int,
    body: InstallationEngineerSerialFinalizeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can verify serial numbers")
    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial verification applies only to call-center installations")
    if inst.status != "Serial Pending Verification":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation is not waiting for serial verification")
    if not inst.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must be verified before serial verification")
    if not body.lines:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select a verification decision for each serial")

    rows = {
        row.id: row
        for row in db.scalars(
            select(InstallationEngineerSerial).where(InstallationEngineerSerial.installation_request_id == inst.id)
        ).all()
    }
    if not rows:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No engineer serials found to verify")

    old_status = inst.status
    approved_rows: list[InstallationEngineerSerial] = []
    rejected_count = 0
    seen_ids: set[int] = set()

    for line in body.lines:
        row = rows.get(line.serial_id)
        if row is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Serial line {line.serial_id} not found")
        if line.serial_id in seen_ids:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Duplicate decision for serial line {line.serial_id}")
        seen_ids.add(line.serial_id)
        decision = (line.decision or "").strip().lower()
        if decision not in {"approve", "reject"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Each line decision must be approve or reject")
        row.admin_remark = (line.admin_remark or "").strip() or None
        row.verified_by = user.id
        row.verified_at = now_utc()
        if decision == "reject":
            row.verification_status = "Rejected"
            rejected_count += 1
            continue
        row.verification_status = "Approved"
        approved_rows.append(row)

    if seen_ids != set(rows.keys()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verify every submitted serial line")

    if not approved_rows:
        inst.status = "Assigned"
        inst.admin_approval_remark = body.overall_remark
        log_installation_action(
            db, inst, action="Serials Rejected", user=user,
            old_status=old_status, new_status=inst.status, remarks=body.overall_remark,
        )
        db.commit()
        db.refresh(inst)
        return InstallationOut(**_hydrate_callcenter(db, inst))

    billing = (body.billing_type or "Free").strip()
    if billing not in BILLING_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "billing_type must be Free or Paid")

    split_requests = split_installations_from_approved_serials(
        db,
        inst,
        approved_rows,
        actor=user,
        billing_type=billing,
        overall_remark=body.overall_remark,
    )
    if billing == "Paid" and body.payment_amount is not None and body.payment_amount > 0:
        for split_request in split_requests:
            split_request.payment_type_requested = split_request.payment_type_requested or "Cash"

    log_installation_action(
        db,
        inst,
        action="Serials Verified",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=body.overall_remark,
        metadata={
            "approved_count": len(approved_rows),
            "rejected_count": rejected_count,
            "billing_type": billing,
            "split_installation_ids": [row.id for row in split_requests],
        },
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/engineer-serial", response_model=InstallationOut)
def engineer_enter_serial(
    installation_id: int,
    body: InstallationEngineerSerialRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.schemas.installation import InstallationEngineerSerialLine

    submit_body = InstallationEngineerSerialSubmitRequest(
        serials=[
            InstallationEngineerSerialLine(
                serial_no=body.serial_no,
                serial_no_2=body.serial_no_2,
                unit_status="Installed",
            ),
        ],
    )
    submit_engineer_serials(installation_id, submit_body, db, user)
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/verify-serial", response_model=InstallationOut)
def verify_serial(
    installation_id: int,
    body: InstallationVerifySerialRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Incool can verify serial numbers")
    inst = _load_visible(db, user, installation_id)
    if not is_callcenter_source(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial verification applies only to call-center installations")
    if inst.status != "Serial Pending Verification":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation is not waiting for serial verification")
    if not inst.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must be verified before serial verification")

    decision = (body.decision or "").strip().lower()
    old_status = inst.status

    if decision == "reject":
        inst.status = "Rejected"
        inst.admin_approval_remark = body.remark
        log_installation_action(
            db, inst, action="Serial Rejected", user=user,
            old_status=old_status, new_status=inst.status, remarks=body.remark,
        )
        db.commit()
        db.refresh(inst)
        return InstallationOut(**_hydrate_callcenter(db, inst))

    serial_no = (body.serial_no or inst.engineer_entered_serial_no or "").strip()
    serial_no_2 = (body.serial_no_2 or inst.engineer_entered_serial_no_2 or "").strip() or None
    if not serial_no:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial number is required")

    item = find_order_item_by_serial_on_order(db, inst.order_id, serial_no, serial_no_2)
    if item is None and body.associate_serial_with_order:
        item = associate_serial_with_order(
            db,
            order_id=inst.order_id,
            serial_no=serial_no,
            serial_no_2=serial_no_2,
            actor=user,
            inst=inst,
        )
    elif item is None and decision != "override":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Serial number not found on the verified order. Reject, override, or associate with order.",
        )

    if decision == "override":
        if not body.serial_no:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Override requires the corrected serial number")
        item = find_order_item_by_serial_on_order(db, inst.order_id, body.serial_no, body.serial_no_2)
        if item is None:
            item = associate_serial_with_order(
                db,
                order_id=inst.order_id,
                serial_no=body.serial_no,
                serial_no_2=body.serial_no_2,
                actor=user,
                inst=inst,
            )
        apply_verified_serial_to_installation(
            db, inst, item, actor=user,
            override_serial_no=body.serial_no,
            override_serial_no_2=body.serial_no_2,
        )
    elif item is not None:
        apply_verified_serial_to_installation(db, inst, item, actor=user)

    billing = (body.billing_type or "Free").strip()
    if billing not in BILLING_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "billing_type must be Free or Paid")
    inst.admin_billing_type = billing
    inst.admin_approval_remark = body.remark
    inst.admin_approved_at = now_utc()
    inst.admin_approved_by = user.id
    inst.serial_verified_at = now_utc()
    inst.serial_verified_by = user.id
    if billing == "Paid":
        if body.payment_amount is None or body.payment_amount <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Paid installation requires payment_amount")
        inst.payment_amount_requested = body.payment_amount
        inst.payment_type_requested = inst.payment_type_requested or "Cash"
    else:
        inst.payment_amount_requested = 0

    inst.status = "In Progress"
    log_installation_action(
        db,
        inst,
        action="Serial Verified",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=body.remark,
        metadata={
            "serial_no": inst.serial_no,
            "billing_type": billing,
            "payment_amount": body.payment_amount,
        },
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


def _ensure_assigned_engineer(inst: InstallationRequest, user: User) -> None:
    if user.role != "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only assigned engineer can perform this action")
    if inst.assigned_engineer != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This installation is not assigned to you")


def _prepare_engineer_payment_request(
    db: Session,
    inst: InstallationRequest,
    *,
    payment_amount: float,
    payment_type: str,
    work_report: str | None,
    qr_blob: bytes | None,
    qr_filename: str | None,
    qr_content_type: str | None,
    qr_size_bytes: int | None,
    user: User,
) -> None:
    old_status = inst.status
    inst.payment_amount_requested = float(payment_amount)
    inst.payment_type_requested = payment_type
    inst.payment_requested_at = now_utc()
    if work_report:
        inst.work_report = work_report.strip()
    if qr_blob:
        inst.payment_qr_code_blob = qr_blob
        inst.payment_qr_code_filename = qr_filename
        inst.payment_qr_code_content_type = qr_content_type
        inst.payment_qr_code_size_bytes = qr_size_bytes
        inst.payment_qr_code_path = None
    payload = approval_stage_payload(first_payment_stage().key)
    inst.payment_approval_status = "Pending"
    inst.payment_approval_stage = payload["payment_approval_stage"]
    inst.payment_approval_stage_label = payload["payment_approval_stage_label"]
    inst.payment_approval_step = payload["payment_approval_step"]
    inst.payment_approval_total_steps = payload["payment_approval_total_steps"]
    inst.payment_next_approver_role = payload["payment_next_approver_role"]
    inst.status = "Payment Pending"

    log_installation_action(
        db,
        inst,
        action="Payment Requested",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=work_report,
        metadata={
            "payment_amount": payment_amount,
            "payment_type": payment_type,
        },
    )
    notify_payment_stage(
        db,
        module="installations",
        entity_id=inst.id,
        title=f"Installation {inst.id}",
        href=f"/installations/{inst.id}",
        entity_status=inst.status,
        stage_key=inst.payment_approval_stage,
        occurred_at=inst.payment_requested_at,
    )


@router.post("/{installation_id}/complete-installation", response_model=InstallationOut)
async def complete_installation(
    installation_id: int,
    installation_date: str = Form(...),
    work_report: str | None = Form(None),
    proof_document: UploadFile = File(...),
    proof_document_serial_2: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if not supports_engineer_installation_workflow(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This workflow applies only to assigned installation requests")
    prepare_vendor_installation_for_engineer_workflow(db, inst, actor=user)
    if not inst.serial_verified_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial numbers must be verified before completing installation")
    _ensure_assigned_engineer(inst, user)
    if inst.status not in {"Assigned", "In Progress", "Returned", "Rejected"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation can be completed only while Assigned, In Progress, or Returned for rework")
    if proof_document is None or not proof_document.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation proof document is required")
    if installation_requires_second_serial_proof(db, inst):
        if proof_document_serial_2 is None or not proof_document_serial_2.filename:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Installation proof for Serial 2 is required when this unit has a second serial number",
            )

    proof_path = await save_upload(proof_document, module="installations")
    proof_path_2 = None
    if proof_document_serial_2 and proof_document_serial_2.filename:
        proof_path_2 = await save_upload(proof_document_serial_2, module="installations")
        replace_completion_proof_serial_2(db, inst, proof_path_2, user)
    old_status = inst.status
    inst.installation_date = datetime.fromisoformat(installation_date)
    inst.work_report = (work_report or "").strip() or inst.work_report
    inst.work_report_file_path = proof_path

    inst.status = "Completion Pending Approval"

    log_installation_action(
        db,
        inst,
        action="Installation Completed",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=work_report,
        metadata={
            "proof_document": proof_path,
            "proof_document_serial_2": proof_path_2,
            "billing_type": inst.admin_billing_type,
        },
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/completion-approval", response_model=InstallationOut)
def review_installation_completion(
    installation_id: int,
    decision: str = Form(...),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool can review installation completion")
    inst = _load_visible(db, user, installation_id)
    if inst.status != "Completion Pending Approval":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation completion is not awaiting approval")
    old_status = inst.status
    if decision.strip().lower() == "approve":
        if not installation_completion_proofs_complete(db, inst):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Upload completion proof for every serial on this unit before approving",
            )
        inst.status = "Installation Completed"
        sync_order_item_for_service_eligibility(db, inst)
        action = "Completion Approved"
    elif decision.strip().lower() == "reject":
        if not (remarks or "").strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Remarks are required when returning installation completion to the engineer",
            )
        inst.admin_approval_remark = remarks.strip()
        inst.status = return_installation_to_engineer_for_rework(inst, reject_stage="completion")
        action = "Completion Rejected"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decision must be Approve or Reject")
    log_installation_action(db, inst, action=action, user=user, old_status=old_status, new_status=inst.status, remarks=remarks)
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/resume-workflow", response_model=InstallationOut)
def resume_installation_workflow(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if not supports_engineer_installation_workflow(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This workflow applies only to assigned installation requests")
    _ensure_assigned_engineer(inst, user)
    if inst.status not in {"Rejected", "Returned"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only rejected or returned installations can be resumed")
    old_status = inst.status
    inst.status = return_installation_to_engineer_for_rework(inst, reject_stage="completion")
    log_installation_action(
        db,
        inst,
        action="Installation Resumed",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=inst.admin_approval_remark,
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/payment-request", response_model=InstallationOut)
async def raise_installation_payment_request(
    installation_id: int,
    payment_amount: float = Form(...),
    payment_type: str = Form(...),
    work_report: str | None = Form(None),
    qr_code: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import PAYMENT_TYPES, _load_visible

    inst = _load_visible(db, user, installation_id)
    if not supports_engineer_installation_workflow(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This workflow applies only to assigned installation requests")
    if not inst.serial_verified_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Serial numbers must be verified before raising payment")
    _ensure_assigned_engineer(inst, user)
    if inst.status != "Installation Completed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admin must approve installation completion before payment")

    normalized_payment_type = (payment_type or "").strip()
    if normalized_payment_type not in PAYMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")
    if payment_amount < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount cannot be negative")
    if normalized_payment_type == "UPI" and (qr_code is None or not qr_code.filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required when payment type is UPI")

    qr_blob = None
    qr_filename = None
    qr_content_type = None
    qr_size_bytes = None
    if qr_code is not None and qr_code.filename:
        qr_blob, qr_filename, qr_content_type, qr_size_bytes = await read_upload_bytes(qr_code)

    _prepare_engineer_payment_request(
        db,
        inst,
        payment_amount=payment_amount,
        payment_type=normalized_payment_type,
        work_report=work_report,
        qr_blob=qr_blob,
        qr_filename=qr_filename,
        qr_content_type=qr_content_type,
        qr_size_bytes=qr_size_bytes,
        user=user,
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/bulk-payment-request", response_model=list[InstallationOut])
async def raise_bulk_installation_payment_request(
    installation_ids: str = Form(...),
    payment_amount: float | None = Form(None),
    payment_amounts_json: str | None = Form(None),
    payment_type: str = Form(...),
    work_report: str | None = Form(None),
    qr_code: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import PAYMENT_TYPES, _load_visible

    try:
        parsed_ids = [int(raw.strip()) for raw in installation_ids.split(",") if raw.strip()]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid installation id list")
    if not parsed_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No installation requests selected")

    normalized_payment_type = (payment_type or "").strip()
    if normalized_payment_type not in PAYMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment type must be Cash or UPI")

    row_amounts: dict[int, float] = {}
    if payment_amounts_json:
        try:
            raw_amounts = json.loads(payment_amounts_json)
            row_amounts = {int(key): float(value) for key, value in raw_amounts.items()}
        except (TypeError, ValueError, json.JSONDecodeError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid per-installation payment amounts")

    rows = [_load_visible(db, user, installation_id) for installation_id in parsed_ids]
    for inst in rows:
        if not supports_engineer_installation_workflow(inst):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Installation #{inst.id} is not assigned workflow")
        if not inst.serial_verified_at:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Installation #{inst.id} serial numbers are not verified")
        _ensure_assigned_engineer(inst, user)
        if inst.status != "Installation Completed":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Installation #{inst.id} is not ready for payment")

    if row_amounts:
        missing_amounts = [inst.id for inst in rows if inst.id not in row_amounts]
        if missing_amounts:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing payment amount for installation id(s): {missing_amounts}")
        if any(amount < 0 for amount in row_amounts.values()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount cannot be negative")
    else:
        if payment_amount is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount is required")
        if payment_amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount cannot be negative")
        row_amounts = {inst.id: float(payment_amount) for inst in rows}

    if normalized_payment_type == "UPI" and (qr_code is None or not qr_code.filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR Code is required when payment type is UPI")

    qr_blob = None
    qr_filename = None
    qr_content_type = None
    qr_size_bytes = None
    if qr_code is not None and qr_code.filename:
        qr_blob, qr_filename, qr_content_type, qr_size_bytes = await read_upload_bytes(qr_code)

    for inst in rows:
        _prepare_engineer_payment_request(
            db,
            inst,
            payment_amount=row_amounts[inst.id],
            payment_type=normalized_payment_type,
            work_report=work_report,
            qr_blob=qr_blob,
            qr_filename=qr_filename,
            qr_content_type=qr_content_type,
            qr_size_bytes=qr_size_bytes,
            user=user,
        )

    db.commit()
    for inst in rows:
        db.refresh(inst)
    return [InstallationOut(**_hydrate_callcenter(db, inst)) for inst in rows]


@router.post("/{installation_id}/send-to-service-review", response_model=InstallationOut)
def send_installation_to_service_review(
    installation_id: int,
    observation: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    if not supports_engineer_installation_workflow(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This workflow applies only to assigned installation requests")
    _ensure_assigned_engineer(inst, user)
    remark = (observation or "").strip()
    if not remark:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Observation is required")

    old_status = inst.status
    inst.engineer_site_remarks = remark
    inst.status = "Service Team Review"
    log_installation_action(
        db,
        inst,
        action="Sent to Service Role",
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=remark,
        metadata={
            "serial_no": inst.serial_no,
            "serial_no_2": inst.serial_no_2,
        },
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/service-review", response_model=InstallationOut)
def review_installation_service_observation(
    installation_id: int,
    decision: str = Form(...),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Service role can review engineer observations")
    inst = _load_visible(db, user, installation_id)
    if not supports_engineer_installation_workflow(inst):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This workflow applies only to assigned installation requests")
    if inst.status != "Service Team Review":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Installation is not waiting for service review")

    normalized = (decision or "").strip().lower()
    note = (remarks or "").strip()
    old_status = inst.status
    if normalized == "approve":
        group_rows = _split_installation_group(db, inst)
        rows_to_advance = [
            row for row in group_rows
            if row.status in {"Assigned", "Service Team Review"} and row.assigned_engineer == inst.assigned_engineer
        ]
        if inst not in rows_to_advance:
            rows_to_advance.append(inst)
        for row in rows_to_advance:
            row_old_status = row.status
            row.status = "In Progress"
            if row.id == inst.id:
                continue
            log_installation_action(
                db,
                row,
                action="Service Observation Approved",
                user=user,
                old_status=row_old_status,
                new_status=row.status,
                remarks=note,
                metadata={
                    "approved_with_installation_id": inst.id,
                    "engineer_observation": inst.engineer_site_remarks,
                },
            )
        action = "Service Observation Approved"
    elif normalized in {"return", "reject"}:
        if not note:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Remarks are required when returning to engineer")
        inst.admin_approval_remark = note
        inst.status = return_installation_to_engineer_for_rework(inst, reject_stage="completion")
        action = "Service Observation Returned"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decision must be approve or return")

    log_installation_action(
        db,
        inst,
        action=action,
        user=user,
        old_status=old_status,
        new_status=inst.status,
        remarks=note,
        metadata={"engineer_observation": inst.engineer_site_remarks},
    )
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.post("/{installation_id}/reset-workflow", response_model=InstallationOut)
def reset_installation_workflow(
    installation_id: int,
    target_step: int = Form(1),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    inst = _load_visible(db, user, installation_id)
    apply_installation_workflow_step(db, inst, target_step, user, remarks=remarks)
    db.commit()
    db.refresh(inst)
    return InstallationOut(**_hydrate_callcenter(db, inst))


@router.get("/{installation_id}/history", response_model=list[InstallationHistoryEntry])
def installation_history(
    installation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.routers.installations import _load_visible

    _load_visible(db, user, installation_id)
    logs = db.scalars(
        select(InstallationStatusLog)
        .where(InstallationStatusLog.installation_request_id == installation_id)
        .order_by(desc(InstallationStatusLog.created_at))
    ).all()
    out: list[InstallationHistoryEntry] = []
    for log in logs:
        performer_name = None
        if log.performed_by:
            performer = db.get(User, log.performed_by)
            performer_name = performer.name if performer else None
        out.append(InstallationHistoryEntry(
            id=log.id,
            action=log.action,
            old_status=log.old_status,
            new_status=log.new_status,
            performed_by_name=performer_name,
            performed_role=log.performed_role,
            remarks=log.remarks,
            metadata_json=log.metadata_json,
            created_at=log.created_at,
        ))
    return out
