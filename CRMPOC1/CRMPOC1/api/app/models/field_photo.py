from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class FieldPhoto(Base):
    """A photo of the machine an engineer found in the field, taken against one serial, with where the phone was."""

    __tablename__ = "field_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # service_unit | installation_serial
    service_request_unit_id: Mapped[int | None] = mapped_column(ForeignKey("service_request_units.id"), nullable=True, index=True)
    installation_engineer_serial_id: Mapped[int | None] = mapped_column(ForeignKey("installation_engineer_serials.id"), nullable=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 1), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # the phone's clock
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # the server's clock
