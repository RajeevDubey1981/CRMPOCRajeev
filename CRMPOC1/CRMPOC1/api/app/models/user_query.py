from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, false
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
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="normal", server_default="normal")  # normal | high | urgent
    holder_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)  # who has to answer; empty = the Admin team
    awaiting_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # since when it waits for the holder
    alarm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_alarm_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserQueryMessage(Base):
    __tablename__ = "user_query_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # sent while somebody was taken out of the conversation: only the people in it at that time can read it
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class UserQueryAttachment(Base):
    """A picture or file pasted or attached to a message. It is uploaded first (message_id empty) and joined to the
    message when that is sent, so a pasted screenshot can go with the words or on its own."""

    __tablename__ = "user_query_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("user_query_messages.id"), nullable=True, index=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserQueryPurge(Base):
    """A conversation that was deleted for good three months after it was closed. Only the number and the dates are kept,
    never what was said, so there is a record that it existed and when it went."""

    __tablename__ = "user_query_purges"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_no: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attachment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserQueryRead(Base):
    """How far a person has read a thread: messages after this one (from others) count as unread for them."""

    __tablename__ = "user_query_reads"
    __table_args__ = (UniqueConstraint("query_id", "user_id", name="uq_user_query_reads"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    last_read_message_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserQueryMember(Base):
    """A person in a conversation, for a stretch of time. Taking someone out closes the stretch (left_at); adding them back
    opens a new one, so what was said while they were out stays unseen by them."""

    __tablename__ = "user_query_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="member")  # owner | member | cc
    share_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())  # may read the shared messages from before they came
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class UserQueryEvent(Base):
    """The history of a query: who forwarded it, who was added or taken out, priority changes, reminders, replies."""

    __tablename__ = "user_query_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("user_queries.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
