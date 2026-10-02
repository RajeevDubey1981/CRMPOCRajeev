from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin


class EmailBounce(Base, TimestampMixin):
    """An outbound email that could not be delivered (bad or missing recipient address)."""

    __tablename__ = "email_bounces"

    id: Mapped[int] = mapped_column(primary_key=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="imap")  # imap | smtp
    message_key: Mapped[str | None] = mapped_column(String(300), nullable=True, unique=True)
