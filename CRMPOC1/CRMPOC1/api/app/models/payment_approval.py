from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PaymentApprovalLog(Base):
    __tablename__ = "payment_approval_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    service_payment_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_payment_requests.id"), nullable=True, index=True
    )
    stage_key: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_label: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_level: Mapped[int] = mapped_column(Integer, nullable=False)
    total_stages: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
