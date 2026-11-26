from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin


class WaConversation(Base, TimestampMixin):
    """One WhatsApp thread per customer number."""

    __tablename__ = "wa_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    wa_phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)  # digits with country code, as Meta sends it
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)  # open | needs_staff | closed
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    ai_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WaMessage(Base):
    __tablename__ = "wa_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("wa_conversations.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # in | out
    wa_message_id: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)  # Meta's id: de-duplicates retries
    msg_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    media_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False)  # received | sending | sent | delivered | read | failed
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null on an inbound message
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class WaWebhookEvent(Base):
    """Every verified webhook call, saved before it is processed, so nothing is lost if processing fails."""

    __tablename__ = "wa_webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WaNote(Base):
    """Internal notes on a thread: staff only, never sent to the customer."""

    __tablename__ = "wa_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("wa_conversations.id"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
