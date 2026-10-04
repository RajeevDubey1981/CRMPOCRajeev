from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin

ITEM_SOURCES = ("Buy", "Make", "Both")
ITEM_TYPES = ("Finished good", "Component", "Spare")
BOM_STATUSES = ("Draft", "Active", "Retired")
ASSEMBLY_STATUSES = ("Planned", "Completed", "Cancelled")
PO_STATUSES = ("Draft", "Pending Approval", "Approved", "Part received", "Received", "Cancelled")


class Supplier(Base, TimestampMixin):
    """Whom we buy from: OEMs, component makers and contract manufacturers."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gstin: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_msme: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    msme_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30", nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)


class Bom(Base, TimestampMixin):
    """Bill of materials for one finished item. One version is Active at a time."""

    __tablename__ = "boms"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    labour_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0", nullable=False)
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    activated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BomLine(Base):
    __tablename__ = "bom_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_id: Mapped[int] = mapped_column(ForeignKey("boms.id", ondelete="CASCADE"), nullable=False, index=True)
    component_item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=1, nullable=False)
    scrap_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, server_default="0", nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AssemblyOrder(Base, TimestampMixin):
    """Build finished units from a BOM: components leave the store, finished units come in with serials."""

    __tablename__ = "assembly_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    asm_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    bom_id: Mapped[int] = mapped_column(ForeignKey("boms.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Planned", nullable=False, index=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssemblyPart(Base):
    """Unit passport: which component serial went into which finished serial."""

    __tablename__ = "assembly_parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    assembly_id: Mapped[int] = mapped_column(ForeignKey("assembly_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_serial: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    component_item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False)
    component_serial: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    po_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)
    place_of_supply: Mapped[str | None] = mapped_column(String(100), nullable=True)
    intra_state: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30", nullable=False)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hsn_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=18, nullable=False)
    taxable: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    received_qty: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
