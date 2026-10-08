from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class InstallationRequest(Base, TimestampMixin):
    __tablename__ = "installation_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="vendor", index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    assigned_engineer: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_service_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    installation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_report_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    settlement_approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payment_amount_requested: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    payment_type_requested: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_qr_code_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_qr_code_blob: Mapped[bytes | None] = mapped_column(LargeBinary().with_variant(LargeBinary(length=(2**32) - 1), "mysql"), nullable=True)
    payment_qr_code_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_qr_code_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_qr_code_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_proof_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_amount_paid: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    payment_type_paid: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payment_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("payment_transactions.id"), nullable=True)
    payment_approval_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payment_approval_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_approval_stage_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_approval_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_approval_total_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_next_approver_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    document_access_token: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ask_for_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    document_request_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    engineer_entered_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    engineer_entered_serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    serial_verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    admin_billing_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    admin_approval_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    engineer_site_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    engineer_serials_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_installation_id: Mapped[int | None] = mapped_column(ForeignKey("installation_requests.id"), nullable=True, index=True)


class InstallationEngineerSerial(Base):
    __tablename__ = "installation_engineer_serials"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_request_id: Mapped[int] = mapped_column(ForeignKey("installation_requests.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    serial_no: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    admin_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    split_installation_request_id: Mapped[int | None] = mapped_column(ForeignKey("installation_requests.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InstallationDocument(Base):
    __tablename__ = "installation_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_request_id: Mapped[int] = mapped_column(ForeignKey("installation_requests.id"), nullable=False, index=True)
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


class InstallationStatusLog(Base):
    __tablename__ = "installation_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_request_id: Mapped[int] = mapped_column(ForeignKey("installation_requests.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    performed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    performed_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
