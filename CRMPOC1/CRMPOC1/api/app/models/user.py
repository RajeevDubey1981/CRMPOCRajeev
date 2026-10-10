from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="callcenter")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)  # where an engineer works
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_pincodes: Mapped[str | None] = mapped_column(Text, nullable=True)  # other pin codes an engineer covers, comma separated
    coverage: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON, see app/services/coverage.py
    vendor_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list: GeM, CSD, Retail, SSD ... a vendor can be several at once
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of item categories the engineer works on; empty = any
    can_manage_bids: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
