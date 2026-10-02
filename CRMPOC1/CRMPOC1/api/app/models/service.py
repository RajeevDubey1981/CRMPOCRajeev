from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class ServiceRequest(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    request_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    query_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Service")
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="New", index=True)
    status_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="callcenter")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    warranty_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_engineer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_service_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    requires_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ask_for_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    document_request_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_access_token: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    customer_identified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)


class ServiceStatusLog(Base):
    __tablename__ = "service_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    performed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    performed_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    serial_history_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceAssignment(Base):
    __tablename__ = "service_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    assignee_type: Mapped[str] = mapped_column(String(20), nullable=False)
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assignee_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ServiceObservation(Base):
    __tablename__ = "service_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    service_request_unit_id: Mapped[int | None] = mapped_column(ForeignKey("service_request_units.id"), nullable=True, index=True)
    submitted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    warranty_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    problem_found: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    parts_required_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_service_charge: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_parts_charge: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceApproval(Base):
    __tablename__ = "service_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("service_observations.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    service_request_unit_id: Mapped[int | None] = mapped_column(ForeignKey("service_request_units.id"), nullable=True, index=True)


class ServiceCompletion(Base):
    __tablename__ = "service_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    performed_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
    performed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    performed_by_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    work_performed: Mapped[str | None] = mapped_column(Text, nullable=True)
    parts_replaced_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    old_part_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_part_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_photos_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_photos_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_acknowledgement_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    completion_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    engineer_completion_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    service_request_unit_id: Mapped[int | None] = mapped_column(ForeignKey("service_request_units.id"), nullable=True, index=True)


class ServiceDocument(Base):
    __tablename__ = "service_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_type: Mapped[str] = mapped_column(String(50), nullable=False)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_by_customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Uploaded")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceDocumentRule(Base, TimestampMixin):
    __tablename__ = "service_document_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    warranty_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    query_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ServicePaymentRequest(Base, TimestampMixin):
    __tablename__ = "service_payment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    requested_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    requested_by_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_charge_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    settlement_service_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    settlement_parts_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_requested_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    payment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_qr_code_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Requested")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payment_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("payment_transactions.id"), nullable=True)
    service_request_unit_id: Mapped[int | None] = mapped_column(ForeignKey("service_request_units.id"), nullable=True, index=True)


class ServiceNotification(Base, TimestampMixin):
    __tablename__ = "service_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    recipient_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    recipient_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServiceRequestItem(Base, TimestampMixin):
    __tablename__ = "service_request_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("item_masters.id"), nullable=True)
    item_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    serial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ServiceRequestUnit(Base, TimestampMixin):
    __tablename__ = "service_request_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    service_request_item_id: Mapped[int] = mapped_column(ForeignKey("service_request_items.id"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_engineer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    serial_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Assigned")


class ServiceUnitAssignment(Base):
    __tablename__ = "service_unit_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False, index=True)
    service_request_unit_id: Mapped[int] = mapped_column(ForeignKey("service_request_units.id"), nullable=False, index=True)
    engineer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
