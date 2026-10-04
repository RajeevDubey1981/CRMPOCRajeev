from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin

GRN_SOURCES = ("Purchase", "Return", "Faulty", "Repaired", "Opening stock")
STOCK_TYPES = ("Fresh", "Spare", "Returned")
CONDITIONS = ("OK", "Damaged")
GRN_STATUSES = ("Draft", "Pending Approval", "Posted")
STOCK_STATUSES = ("Available", "Quarantine", "Reserved", "Issued", "Scrapped")


class StoreGrn(Base, TimestampMixin):
    """Goods receipt note. Nothing is in stock until a GRN is posted."""

    __tablename__ = "store_grns"

    id: Mapped[int] = mapped_column(primary_key=True)
    grn_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Draft", nullable=False, index=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StoreGrnLine(Base):
    __tablename__ = "store_grn_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    grn_id: Mapped[int] = mapped_column(ForeignKey("store_grns.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    stock_type: Mapped[str] = mapped_column(String(20), default="Fresh", nullable=False)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    condition: Mapped[str] = mapped_column(String(20), default="OK", nullable=False)
    bin_location: Mapped[str | None] = mapped_column(String(50), nullable=True)


class StoreStock(Base, TimestampMixin):
    """One row per received serial, or one row per received batch for items counted by quantity."""

    __tablename__ = "store_stock"
    __table_args__ = (
        UniqueConstraint("serial_no", name="uq_store_stock_serial_no"),
        UniqueConstraint("serial_no_2", name="uq_store_stock_serial_no_2"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    grn_line_id: Mapped[int | None] = mapped_column(ForeignKey("store_grn_lines.id"), nullable=True)
    grn_id: Mapped[int | None] = mapped_column(ForeignKey("store_grns.id"), nullable=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stock_type: Mapped[str] = mapped_column(String(20), default="Fresh", nullable=False)
    condition: Mapped[str] = mapped_column(String(20), default="OK", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Available", nullable=False, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    bin_location: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    # set while the unit is held for, or has gone out against, one order line
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True, index=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatch_id: Mapped[int | None] = mapped_column(ForeignKey("store_dispatches.id"), nullable=True, index=True)


class StoreDispatch(Base, TimestampMixin):
    """One dispatch of an order out of the store: the bill it went against and the transport details."""

    __tablename__ = "store_dispatches"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    bill_no: Mapped[str] = mapped_column(String(100), nullable=False)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    lrn_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StoreLedger(Base):
    """Every stock movement with its document number and the person who did it."""

    __tablename__ = "store_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    doc_no: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_masters.id"), nullable=False, index=True)
    stock_id: Mapped[int | None] = mapped_column(ForeignKey("store_stock.id"), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    qty_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
