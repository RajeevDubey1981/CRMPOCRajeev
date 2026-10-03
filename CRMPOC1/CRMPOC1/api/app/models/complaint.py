from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class Complaint(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    comp_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    comp_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    status_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_engineer: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_proof_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    send_sms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="callcenter", nullable=False)
    # "High" complaints are marked by the call centre / service team, blink in the list and are shown first.
    priority: Mapped[str] = mapped_column(String(10), default="Normal", server_default="Normal", nullable=False, index=True)
    priority_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ComplaintStatusLog(Base):
    __tablename__ = "complaint_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
