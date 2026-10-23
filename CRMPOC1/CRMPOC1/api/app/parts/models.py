"""Tables of the Parts database. Columns named crm_* hold a number or a reference that points into the CRM
database (a user, an item code, a service/installation request, a Queries thread); there is no foreign key to it.

- SparePart / SparePartFitment: the spare-parts catalogue, and which item codes each part fits.
- ItemRequest: one unified queue for everything that needs someone's say-so from the field: a spare part, a
  miscellaneous expense, an on-demand (not-in-catalogue) part, or a whole-unit replacement. Its stage is the
  approval state; ItemRequestEvent is its timeline/history; ItemRequestPhoto its mandatory proof photos;
  crm_query_id links it to a "discuss" thread in Queries when the approver needs to ask something first.
- PartWarrantySwap: the record made when a part is physically swapped (old serial out, new serial in), with the
  warranty-restart choice (fresh vs carry-forward) that was made at the time.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.parts.db import PartsBase


class Stamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SparePart(PartsBase, Stamped):
    """A spare part: its own code and EAN, its price, and whether engineers may see it when raising a request."""

    __tablename__ = "parts_spare_part"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    part_name: Mapped[str] = mapped_column(String(255), nullable=False)
    part_ean: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    engineer_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    crm_created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SparePartFitment(PartsBase):
    """Which CRM item codes (products / models) a spare part fits. Many-to-many, by item_code reference."""

    __tablename__ = "parts_fitment"
    __table_args__ = (UniqueConstraint("spare_part_id", "crm_item_code", name="uq_parts_fitment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    spare_part_id: Mapped[int] = mapped_column(ForeignKey("parts_spare_part.id"), nullable=False, index=True)
    crm_item_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    crm_item_name_cache: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


REQUEST_KINDS = ("part", "expense", "ondemand", "unit")
REQUEST_STAGES = ("svm", "sub", "done", "rejected", "returned")  # waiting on Service Manager | waiting on Admin/Sub Admin | approved | rejected | sent back to the service team to fix


class ItemRequest(PartsBase, Stamped):
    """One request raised from the field: a spare part, a misc. expense, an on-demand part, or a whole-unit
    replacement. `stage` is the single source of truth for who must act next; see app.parts.rules for the chain."""

    __tablename__ = "parts_item_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # part | expense | ondemand | unit

    crm_service_request_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    crm_service_request_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crm_installation_request_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    crm_installation_request_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crm_item_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    crm_item_name_cache: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)

    spare_part_id: Mapped[int | None] = mapped_column(ForeignKey("parts_spare_part.id"), nullable=True, index=True)
    part_name_cache: Mapped[str | None] = mapped_column(String(255), nullable=True)  # free text when not yet in the catalogue

    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    stage: Mapped[str] = mapped_column(String(10), nullable=False, default="svm", index=True)
    # Overrides the kind-based photo mandate (e.g. 0 for requests the system auto-raises from an engineer's
    # observation, which already documents the problem). Null means "use the normal rule for this kind".
    required_photos_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    crm_query_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # the "discuss" thread, if any

    crm_raised_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crm_raised_by_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    crm_raised_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    request_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date(), index=True)


class ItemRequestPhoto(PartsBase):
    """A proof photo on a request. Part-issue requests need 4 before they can be sent."""

    __tablename__ = "parts_item_request_photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_request_id: Mapped[int] = mapped_column(ForeignKey("parts_item_request.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ItemRequestEvent(PartsBase):
    """The timeline of a request: raised, discussed, approved/rejected at each stage, supplied, settled."""

    __tablename__ = "parts_item_request_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_request_id: Mapped[int] = mapped_column(ForeignKey("parts_item_request.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    crm_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crm_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class PartWarrantySwap(PartsBase):
    """Recorded when an engineer physically swaps a part (old serial out, new serial in): the warranty-restart
    choice made at that moment, fresh or carried forward from the original installation."""

    __tablename__ = "parts_warranty_swap"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_request_id: Mapped[int | None] = mapped_column(ForeignKey("parts_item_request.id"), nullable=True, index=True)
    crm_service_request_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    crm_item_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    installed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_warranty_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="fresh")  # fresh | carry
    carried_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    swapped_on: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    recorded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
