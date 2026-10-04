from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.store import CONDITIONS, GRN_SOURCES, STOCK_TYPES

SourceType = Literal[GRN_SOURCES]  # type: ignore[valid-type]
StockType = Literal[STOCK_TYPES]  # type: ignore[valid-type]
Condition = Literal[CONDITIONS]  # type: ignore[valid-type]


class GrnLineIn(BaseModel):
    item_id: int
    stock_type: StockType = "Fresh"
    serial_no: str | None = Field(default=None, max_length=100)
    serial_no_2: str | None = Field(default=None, max_length=100)
    qty: int = Field(default=1, ge=1, le=100000)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    condition: Condition = "OK"
    bin_location: str | None = Field(default=None, max_length=50)


class GrnIn(BaseModel):
    source_type: SourceType = "Purchase"
    po_id: int | None = None
    supplier_name: str | None = Field(default=None, max_length=255)
    reference_no: str | None = Field(default=None, max_length=100)
    remarks: str | None = None
    lines: list[GrnLineIn] = Field(default_factory=list)


class GrnLineOut(BaseModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    serial_count: int = 1
    stock_type: str
    serial_no: str | None = None
    serial_no_2: str | None = None
    qty: int
    unit_cost: Decimal | None = None
    condition: str
    bin_location: str | None = None


class GrnOut(BaseModel):
    id: int
    grn_no: str
    source_type: str
    po_id: int | None = None
    po_no: str | None = None
    supplier_name: str | None = None
    reference_no: str | None = None
    status: str
    remarks: str | None = None
    reject_reason: str | None = None
    created_by: int | None = None
    created_by_name: str | None = None
    approved_by: int | None = None
    approved_by_name: str | None = None
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    total_units: int = 0
    lines: list[GrnLineOut] = Field(default_factory=list)
    can_approve: bool = False


class GrnListItem(BaseModel):
    id: int
    grn_no: str
    source_type: str
    supplier_name: str | None = None
    reference_no: str | None = None
    status: str
    created_by_name: str | None = None
    created_at: datetime | None = None
    total_units: int = 0


class GrnListResponse(BaseModel):
    items: list[GrnListItem]
    total: int


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SerialCheckIn(BaseModel):
    serial: str = Field(min_length=1, max_length=100)
    grn_id: int | None = None


class SerialCheckOut(BaseModel):
    serial: str
    ok: bool
    reason: str | None = None


class StockSummaryItem(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    serial_count: int
    available: int
    quarantine: int
    total: int
    oldest_received: datetime | None = None


class StockUnit(BaseModel):
    id: int
    item_id: int
    item_code: str
    item_name: str
    serial_no: str | None = None
    serial_no_2: str | None = None
    stock_type: str
    condition: str
    status: str
    qty: int
    unit_cost: Decimal | None = None
    bin_location: str | None = None
    grn_no: str | None = None
    received_at: datetime
    age_days: int


class StockUnitsResponse(BaseModel):
    items: list[StockUnit]
    total: int


class LedgerRow(BaseModel):
    id: int
    created_at: datetime
    doc_type: str
    doc_no: str
    item_code: str
    item_name: str
    serial_no: str | None = None
    qty_in: int
    qty_out: int
    stock_type: str | None = None
    by_user_name: str | None = None
    note: str | None = None


class LedgerResponse(BaseModel):
    items: list[LedgerRow]
    total: int


class StoreItemLookup(BaseModel):
    id: int
    item_code: str
    item_name: str
    serial_count: int


class DispatchIn(BaseModel):
    scans: list[str] = Field(default_factory=list)
    courier_id: int | None = None
    lrn_no: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


class CourierLookup(BaseModel):
    id: int
    courier_name: str


class ShortLine(BaseModel):
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    missing: int


class ReserveOut(BaseModel):
    reserved: int
    short: list[ShortLine] = Field(default_factory=list)
    order: "StoreOrderOut"


class OrderUnitOut(BaseModel):
    order_item_id: int
    item_id: int | None = None
    item_code: str | None = None
    item_name: str | None = None
    serial_count: int = 1
    stock_id: int | None = None
    serial_no: str | None = None
    serial_no_2: str | None = None
    unit_status: str | None = None
    received_at: datetime | None = None


class FreeStock(BaseModel):
    item_id: int
    item_name: str | None = None
    needed: int
    available: int


class StoreOrderListItem(BaseModel):
    id: int
    order_no: str | None = None
    order_date: date | None = None
    customer_name: str | None = None
    customer_city: str | None = None
    oem_bill_no: str | None = None
    status: str
    stage: str
    units: int
    held: int


class StoreOrderListResponse(BaseModel):
    items: list[StoreOrderListItem]
    total: int
    counts: dict[str, int]


class StoreOrderOut(BaseModel):
    id: int
    order_no: str | None = None
    order_date: date | None = None
    customer_name: str | None = None
    customer_city: str | None = None
    customer_address: str | None = None
    oem_bill_no: str | None = None
    status: str
    stage: str
    courier_name: str | None = None
    lrn_no: str | None = None
    dispatch_no: str | None = None
    dispatched_at: datetime | None = None
    lines: list[OrderUnitOut]
    stock_check: list[FreeStock]
    can_reserve: bool = False
    can_release: bool = False
    can_dispatch: bool = False


ReserveOut.model_rebuild()
