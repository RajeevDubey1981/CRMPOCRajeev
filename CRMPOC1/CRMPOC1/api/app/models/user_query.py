from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin


class UserQuery(Base, TimestampMixin):
    """A question raised by a user (engineer, vendor, service team ...) to the Admin and Sub Admin, answered in a thread.

    owner_id is the person the thread is with; created_by is who started it (the owner, or an Admin / Sub Admin who
    wrote to the owner first).
    """

    __tablename__ = "user_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="General")
    related_to: Mapped[str | None] = mapped_column(String(200), nullable=True)  # a complaint / order / request number
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Open", index=True)  # Open | Answered | Closed
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class UserQueryMessage(Base):
    __tablename__ = "user_query_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserQueryRead(Base):
    """How far a person has read a thread: messages after this one (from others) count as unread for them."""

    __tablename__ = "user_query_reads"
    __table_args__ = (UniqueConstraint("query_id", "user_id", name="uq_user_query_reads"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    last_read_message_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
