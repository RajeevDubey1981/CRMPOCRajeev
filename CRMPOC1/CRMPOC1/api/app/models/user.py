from sqlalchemy import Boolean, Integer, LargeBinary, String, Text
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
    can_manage_marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    id_proof_blob: Mapped[bytes | None] = mapped_column(LargeBinary().with_variant(LargeBinary(length=(2**32) - 1), "mysql"), nullable=True)
    id_proof_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    id_proof_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    id_proof_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_picture_blob: Mapped[bytes | None] = mapped_column(LargeBinary().with_variant(LargeBinary(length=(2**32) - 1), "mysql"), nullable=True)
    profile_picture_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_picture_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
