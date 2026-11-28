"""Orders placed on the public website (www.indcool.in), kept in the CRM and synced from the website.

The website is the source of truth: every sync overwrites the order with what the site holds, and records an event
whenever the status or the payment status changes, so the CRM shows the whole history (placed, paid, confirmed,
cancelled, delivered ...). The status words are stored exactly as the website writes them.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WebOrder(Base):
    __tablename__ = "web_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_order_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)  # orders.id on the website
    order_number: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    site_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    mobile10: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)  # last 10 digits, for matching complaints and chats
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    subtotal: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    shipping: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    payment_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stock_deducted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    site_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)  # any other column the site adds later
    first_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class WebOrderItem(Base):
    __tablename__ = "web_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    web_order_id: Mapped[int] = mapped_column(ForeignKey("web_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    site_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON text kept as the site sends it
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_slot: Mapped[str | None] = mapped_column(String(100), nullable=True)


class WebOrderAddress(Base):
    __tablename__ = "web_order_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    web_order_id: Mapped[int] = mapped_column(ForeignKey("web_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str | None] = mapped_column(String(20), nullable=True)  # shipping | billing
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)


class WebOrderPayment(Base):
    """One payment attempt (the website's payment_logs)."""

    __tablename__ = "web_order_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    web_order_id: Mapped[int] = mapped_column(ForeignKey("web_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    site_payment_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)  # the gateway's answer, trimmed


class WebOrderEvent(Base):
    """The timeline: placed, status changed, payment status changed."""

    __tablename__ = "web_order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    web_order_id: Mapped[int] = mapped_column(ForeignKey("web_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # placed | status | payment_status
    old_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)  # the website's own time when it gave one
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # when the CRM noticed
