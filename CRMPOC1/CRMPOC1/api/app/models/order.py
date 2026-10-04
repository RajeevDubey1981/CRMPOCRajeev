from datetime import date

from sqlalchemy import String, Date, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    oem_bill_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_contact: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    lrn_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_bill_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_bill_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


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
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
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
