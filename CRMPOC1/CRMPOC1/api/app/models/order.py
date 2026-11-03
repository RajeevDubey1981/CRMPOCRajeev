from datetime import date, datetime

from sqlalchemy import Boolean, String, Date, DateTime, Integer, ForeignKey, Numeric, Text, true, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    order_no: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    oem_bill_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # Which line of oem_bill_no this order is, when one bill lists several item lines -- reference only.
    oem_bill_line_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Credits this amount to the vendor's ledger (AccountLedgerEntry, source_type="oem_bill") the moment
    # it's set or changed — see _sync_oem_bill_ledger_entry in routers/orders.py.
    oem_bill_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Qty this oem_bill_amount covers on this line -- divides down to a per-unit price, used to
    # auto-calculate the return credit in process_return (routers/account_ledger.py) for partial returns.
    oem_bill_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # How many physical boxes make up 1 unit of oem_bill_qty (e.g. 2 for a Split AC -- indoor + outdoor).
    # Data only for now: a later return-side feature will use this to tell a complete-unit return apart
    # from a partial one (only some boxes of a unit back).
    boxes_per_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_contact: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    # Credits this amount to the courier's ledger (AccountLedgerEntry, source_type="freight") the moment
    # it's set or changed — see _sync_freight_ledger_entry in routers/orders.py.
    freight_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lrn_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # The RTO leg has its own waybill and its own cost, separate from the outbound freight_amount above
    # -- credits the courier's ledger as its own entry (source_type="return_freight") the moment it's
    # set or changed, same pattern as _sync_freight_ledger_entry. See _sync_return_freight_ledger_entry.
    return_lrn_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    return_freight_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    vendor_bill_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_bill_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Sales/Service tick this once the returned goods are physically back in hand, before Accounts can
    # debit the vendor for the return (see routers/account_ledger.py's process_return).
    material_receipt_confirmed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    material_receipt_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accounts_return_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrderConsigneeAddress(Base, TimestampMixin):
    """Additional ship-to / consignee locations for one order."""

    __tablename__ = "order_consignee_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consignee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_auto_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    consignee_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_consignee_addresses.id"), nullable=True, index=True,
    )
    item_id: Mapped[int | None] = mapped_column(ForeignKey("item_masters.id"), nullable=True)
    item_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    serial_no_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pcb_warranty_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    component_warranty_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    machine_warranty_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_service_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dry_free_service_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wet_free_service_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    service_consume_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    installation_status: Mapped[str] = mapped_column(String(50), default="Not Requested", nullable=False)
