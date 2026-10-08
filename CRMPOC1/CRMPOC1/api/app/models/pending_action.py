from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin


class UserPendingAction(Base, TimestampMixin):
    __tablename__ = "user_pending_actions"
    __table_args__ = (
        UniqueConstraint(
            "recipient_user_id",
            "module",
            "entity_id",
            "entity_ref",
            "action_type",
            name="uq_user_pending_actions_recipient_entity_action",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    recipient_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    module: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_ref: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_label: Mapped[str] = mapped_column(String(120), nullable=False)
    href: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_status: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # a card with a time limit (a bid to accept or reject, a bid to mark submitted): when it runs out
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
