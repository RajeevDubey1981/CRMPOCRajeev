from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    ref_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    call_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    transferred_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_transferred: Mapped[bool] = mapped_column(default=False, nullable=False)
    duration_secs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    followup_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    # Sarvam's id for this call ("<YYYYMMDD>/<uuid>"); the key to download its recording.
    sarvam_interaction_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class CallRecording(Base, TimestampMixin):
    """The audio of one call, kept apart from the calls table so list queries never load it."""

    __tablename__ = "call_recordings"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="audio/wav")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audio: Mapped[bytes] = mapped_column(LargeBinary().with_variant(LargeBinary(length=(2**32) - 1), "mysql"), nullable=False)
