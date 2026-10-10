"""Tables of the Sales database. Columns named crm_* hold a number or a reference that points into the CRM
database; there is no foreign key to it."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.sales.db import SalesBase


class Stamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SalesProfile(SalesBase, Stamped):
    """A sales person: where they work, which lead types they handle, their target. crm_user_id points at users.id."""

    __tablename__ = "sales_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    crm_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name_cache: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role_cache: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_pincodes: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma separated
    areas: Mapped[str | None] = mapped_column(Text, nullable=True)  # states or countries covered, comma separated
    types_handled: Mapped[str | None] = mapped_column(Text, nullable=True)  # lead type keys, comma separated
    target_lakh: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SalesRoleTick(SalesBase):
    """Admin's choice for a whole role (team or mgr): one row per tick that differs from the built-in default."""

    __tablename__ = "sales_role_tick"
    __table_args__ = (UniqueConstraint("role_key", "tick_key", name="uq_sales_role_tick"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str] = mapped_column(String(20), nullable=False)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SalesUserTick(SalesBase):
    """Admin's choice for one person, when it differs from their role."""

    __tablename__ = "sales_user_tick"
    __table_args__ = (UniqueConstraint("crm_user_id", "tick_key", name="uq_sales_user_tick"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crm_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SalesTickHistory(SalesBase):
    __tablename__ = "sales_tick_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    crm_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # null = back to the default
    by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    by_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SalesSetting(SalesBase):
    __tablename__ = "sales_setting"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")


class SalesLead(SalesBase, Stamped):
    __tablename__ = "sales_lead"
    __table_args__ = (UniqueConstraint("crm_kind", "crm_ref", name="uq_sales_lead_crm"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_no: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="Typed in")
    channel: Mapped[str] = mapped_column(String(40), nullable=False, default="hand")
    lead_type: Mapped[str] = mapped_column(String(20), nullable=False, default="retail", index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)  # the customer's own words, copied
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="new", index=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    follow_up_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    heat: Mapped[str] = mapped_column(String(10), nullable=False, default="cold")
    heat_why: Mapped[str | None] = mapped_column(Text, nullable=True)  # json list
    heat_by: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating_answers: Mapped[str | None] = mapped_column(Text, nullable=True)  # json of the ticked answers
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="normal", index=True)
    priority_why: Mapped[str | None] = mapped_column(Text, nullable=True)  # json list
    priority_by: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value_lakh: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    value_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_basis: Mapped[str | None] = mapped_column(String(80), nullable=True)
    closes_on: Mapped[date | None] = mapped_column(Date, nullable=True)  # bid or tender last date
    is_prospect: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_call_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asked_again_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # the workflow mark: the person who has the lead did something about it (a call, a stage, a note ...)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_action_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # link into the CRM: reference only
    crm_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)  # complaint | partner
    crm_ref: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    crm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crm_close_pending: Mapped[str | None] = mapped_column(String(30), nullable=True)  # a close the CRM has not taken yet
    # disposal
    disposal_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    disposal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposal_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disposal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SalesLeadActivity(SalesBase):
    __tablename__ = "sales_lead_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("sales_lead.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="note")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    by_name: Mapped[str] = mapped_column(String(255), nullable=False, default="automatic")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SalesQuotation(SalesBase, Stamped):
    __tablename__ = "sales_quotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("sales_lead.id"), nullable=True, index=True)
    party: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(60), nullable=True)
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    lead_type: Mapped[str] = mapped_column(String(20), nullable=False, default="retail")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)  # rupees per dollar, export only
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft", index=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    warranty_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    gross: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    taxable: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    high_discount: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalesQuotationLine(SalesBase):
    """A copy of the item as it was on the day: code, name, HSN, rate and GST are not read again later."""

    __tablename__ = "sales_quotation_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("sales_quotation.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hsn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    gst_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=18)


class SalesQuotationHistory(SalesBase):
    __tablename__ = "sales_quotation_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("sales_quotation.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    by_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SalesInboxLog(SalesBase):
    """The 'registered first, then lead' log: what came in from the CRM and what Sales did with it."""

    __tablename__ = "sales_inbox_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    crm_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(Text, nullable=False, default="")


class SalesLeadType(SalesBase):
    """The list of lead types. The eight built-in ones are seeded; Admin can add more, rename, recolour or switch off."""

    __tablename__ = "sales_lead_type"

    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#475569")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SalesSource(SalesBase, Stamped):
    """A connection that brings enquiries in: IndiaMART, Meta lead forms, a web address, an API, a sheet, a mailbox.
    config holds what is not secret; secret holds keys and passwords, encrypted."""

    __tablename__ = "sales_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_lead_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    default_owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SalesInbound(SalesBase):
    """What a source has already brought in, so the same enquiry is never made twice."""

    __tablename__ = "sales_inbound"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_sales_inbound"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sales_source.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crm_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SalesProspect(SalesBase):
    """A company found in a directory or an import-record list (Kompass, TradeInt ...) that has not asked us for anything."""

    __tablename__ = "sales_prospect"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    products: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
