from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ----- suppliers ------------------------------------------------------------
class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    gstin: str | None = Field(default=None, max_length=15)
    state: str | None = Field(default=None, max_length=100)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    is_msme: bool = False
    msme_no: str | None = Field(default=None, max_length=50)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account: str | None = Field(default=None, max_length=40)
    bank_ifsc: str | None = Field(default=None, max_length=11)
    is_active: bool = True


class SupplierOut(BaseModel):
    id: int
    name: str
    gstin: str | None = None
    pan: str | None = None
    state: str | None = None
    state_code: str | None = None
    address: str | None = None
    city: str | None = None
    pincode: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_msme: bool = False
    msme_no: str | None = None
    payment_terms_days: int = 30
    bank_name: str | None = None
    bank_account: str | None = None
    bank_ifsc: str | None = None
    is_active: bool = True
    registered: bool = True


class SupplierListResponse(BaseModel):
    items: list[SupplierOut]
    total: int


# ----- items for the pickers ------------------------------------------------
class AccItemLookup(BaseModel):
    id: int
    item_code: str
    item_name: str
    serial_count: int
    source: str = "Buy"
    item_type: str | None = None
    gst_rate: float | None = None
    hsn_code: str | None = None


# ----- BOM ------------------------------------------------------------------
class BomLineIn(BaseModel):
    component_item_id: int
    qty: Decimal = Field(gt=0, le=100000)
    scrap_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    note: str | None = Field(default=None, max_length=255)


class BomIn(BaseModel):
    item_id: int | None = None
    notes: str | None = None
    labour_cost: Decimal = Field(default=Decimal("0"), ge=0)
    overhead_cost: Decimal = Field(default=Decimal("0"), ge=0)
    lines: list[BomLineIn] = Field(default_factory=list)


class BomLineOut(BaseModel):
    id: int
    component_item_id: int
    item_code: str | None = None
    item_name: str | None = None
    serial_count: int = 0
    qty: Decimal
    scrap_pct: Decimal
    note: str | None = None
    unit_cost: Decimal | None = None
    line_cost: Decimal | None = None
    in_store: int = 0
    can_build: int = 0


class BomOut(BaseModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    version: int
    status: str
    notes: str | None = None
    labour_cost: Decimal
    overhead_cost: Decimal
    material_cost: Decimal | None = None
    unit_cost: Decimal | None = None
    cost_complete: bool = True
    can_build: int = 0
    buy_price_hint: Decimal | None = None
    created_by_name: str | None = None
    activated_by_name: str | None = None
    activated_at: datetime | None = None
    lines: list[BomLineOut] = Field(default_factory=list)
    can_edit: bool = False
    can_activate: bool = False


class BomListItem(BaseModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    version: int
    status: str
    lines: int
    unit_cost: Decimal | None = None
    activated_at: datetime | None = None


class BomListResponse(BaseModel):
    items: list[BomListItem]
    total: int


# ----- assembly -------------------------------------------------------------
class AssemblyIn(BaseModel):
    item_id: int
    qty: int = Field(ge=1, le=10000)
    remarks: str | None = None


class AssemblyUnitIn(BaseModel):
    serial_no: str | None = Field(default=None, max_length=100)
    serial_no_2: str | None = Field(default=None, max_length=100)


class AssemblyCompleteIn(BaseModel):
    units: list[AssemblyUnitIn] = Field(default_factory=list)


class AssemblyNeedOut(BaseModel):
    component_item_id: int
    item_code: str | None = None
    item_name: str | None = None
    needed: int
    in_store: int
    short: int


class AssemblyPartOut(BaseModel):
    finished_serial: str | None = None
    component_item_id: int
    item_code: str | None = None
    item_name: str | None = None
    component_serial: str | None = None
    qty: int
    unit_cost: Decimal | None = None


class AssemblyOut(BaseModel):
    id: int
    asm_no: str
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    serial_count: int = 1
    bom_id: int
    bom_version: int | None = None
    qty: int
    status: str
    remarks: str | None = None
    created_by_name: str | None = None
    completed_by_name: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    needs: list[AssemblyNeedOut] = Field(default_factory=list)
    parts: list[AssemblyPartOut] = Field(default_factory=list)
    unit_cost: Decimal | None = None
    can_complete: bool = False
    can_cancel: bool = False


class AssemblyListItem(BaseModel):
    id: int
    asm_no: str
    item_code: str | None = None
    item_name: str | None = None
    qty: int
    status: str
    created_at: datetime | None = None


class AssemblyListResponse(BaseModel):
    items: list[AssemblyListItem]
    total: int


class PassportOut(BaseModel):
    serial: str
    asm_no: str | None = None
    item_name: str | None = None
    built_at: datetime | None = None
    parts: list[AssemblyPartOut] = Field(default_factory=list)


# ----- purchase orders ------------------------------------------------------
class PoLineIn(BaseModel):
    item_id: int
    qty: int = Field(ge=1, le=1000000)
    rate: Decimal = Field(ge=0)
    gst_rate: Decimal | None = Field(default=None, ge=0, le=40)


class PoIn(BaseModel):
    supplier_id: int
    po_date: date | None = None
    expected_date: date | None = None
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    terms: str | None = None
    remarks: str | None = None
    lines: list[PoLineIn] = Field(default_factory=list)


class PoLineOut(BaseModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    hsn_code: str | None = None
    qty: int
    rate: Decimal
    gst_rate: Decimal
    taxable: Decimal
    tax: Decimal
    received_qty: int
    outstanding: int


class PoOut(BaseModel):
    id: int
    po_no: str
    po_date: date
    supplier_id: int
    supplier_name: str | None = None
    supplier_gstin: str | None = None
    supplier_is_msme: bool = False
    expected_date: date | None = None
    status: str
    place_of_supply: str | None = None
    intra_state: bool = True
    payment_terms_days: int = 30
    terms: str | None = None
    remarks: str | None = None
    taxable_value: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total: Decimal
    reject_reason: str | None = None
    created_by_name: str | None = None
    approved_by_name: str | None = None
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    lines: list[PoLineOut] = Field(default_factory=list)
    can_edit: bool = False
    can_submit: bool = False
    can_approve: bool = False
    can_cancel: bool = False


class PoListItem(BaseModel):
    id: int
    po_no: str
    po_date: date
    supplier_name: str | None = None
    status: str
    total: Decimal
    created_by_name: str | None = None


class PoListResponse(BaseModel):
    items: list[PoListItem]
    total: int


class PoReasonIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OpenPoLine(BaseModel):
    item_id: int
    item_code: str | None = None
    item_name: str | None = None
    outstanding: int


class OpenPo(BaseModel):
    id: int
    po_no: str
    supplier_name: str | None = None
    status: str
    lines: list[OpenPoLine]
