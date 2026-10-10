from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class BidLineIn(BaseModel):
    item: str = Field(min_length=1, max_length=255)
    quantity: int | None = Field(None, ge=0)

    @field_validator("item")
    @classmethod
    def _trim(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Item cannot be empty")
        return value


class BidLineOut(BaseModel):
    item: str
    quantity: int | None = None


class BidMini(BaseModel):
    id: int
    bid_number: str
    title: str
    status: str
    end_date: date


class BidNumberCheck(BaseModel):
    exact: BidMini | None = None  # the same number is already entered: saving is refused
    similar: list[BidMini] = Field(default_factory=list)  # shares the long number part: check it is not the same bid


class BidIn(BaseModel):
    bid_number: str = Field(min_length=3, max_length=120)
    bid_type: str = "GeM"
    portal: str | None = Field(None, max_length=120)
    title: str = Field(min_length=2, max_length=255)
    department: str | None = Field(None, max_length=255)
    product_category: str | None = None
    product_type: str | None = None
    quantity: int | None = Field(None, ge=0)
    estimated_value: Decimal | None = Field(None, ge=0)
    publish_date: date | None = None
    end_date: date
    opening_date: date | None = None
    emd_amount: Decimal | None = Field(None, ge=0)
    emd_mode: str | None = Field(None, max_length=60)
    emd_exempt: bool = False
    epbg_details: str | None = Field(None, max_length=255)
    tender_fee: Decimal | None = Field(None, ge=0)
    notes: str | None = None
    lines: list[BidLineIn] = Field(default_factory=list, max_length=30)


class BidUpdate(BaseModel):
    bid_number: str | None = Field(None, min_length=3, max_length=120)
    bid_type: str | None = None
    portal: str | None = None
    title: str | None = Field(None, min_length=2, max_length=255)
    department: str | None = None
    product_category: str | None = None
    product_type: str | None = None
    quantity: int | None = Field(None, ge=0)
    estimated_value: Decimal | None = Field(None, ge=0)
    publish_date: date | None = None
    end_date: date | None = None
    opening_date: date | None = None
    emd_amount: Decimal | None = Field(None, ge=0)
    emd_mode: str | None = None
    emd_exempt: bool | None = None
    epbg_details: str | None = None
    tender_fee: Decimal | None = Field(None, ge=0)
    notes: str | None = None
    lines: list[BidLineIn] | None = Field(None, max_length=30)  # None = leave as is, a list replaces them


class BidEventOut(BaseModel):
    id: int
    at: datetime | None = None
    actor_name: str
    action: str
    text: str


class BidOut(BaseModel):
    id: int
    bid_number: str
    bid_type: str
    portal: str | None = None
    title: str
    department: str | None = None
    product_category: str | None = None
    product_type: str | None = None
    quantity: int | None = None
    estimated_value: Decimal | None = None
    publish_date: date | None = None
    end_date: date
    opening_date: date | None = None
    emd_amount: Decimal | None = None
    emd_mode: str | None = None
    emd_exempt: bool = False
    epbg_details: str | None = None
    tender_fee: Decimal | None = None
    notes: str | None = None
    status: str
    vendor_id: int | None = None
    vendor_name: str | None = None
    is_self: bool = False
    confirm_by: date | None = None
    confirm_due_at: datetime | None = None
    submit_by: date | None = None
    confirmed_at: datetime | None = None
    submitted_at: datetime | None = None
    submission_ref: str | None = None
    result_note: str | None = None
    days_left: int | None = None
    pending_requests: int = 0
    created_at: datetime | None = None
    lines: list[BidLineOut] = Field(default_factory=list)
    events: list[BidEventOut] = Field(default_factory=list)


class AllocateIn(BaseModel):
    vendor_id: int | None = None
    self_bid: bool = False
    reason: str | None = None


class ReasonIn(BaseModel):
    reason: str | None = None


class SubmitIn(BaseModel):
    reference: str | None = Field(None, max_length=160)


class ResultIn(BaseModel):
    result: str
    note: str | None = None


class RequestIn(BaseModel):
    bid_number: str = Field(min_length=1, max_length=120)
    note: str | None = None


class RequestDecisionIn(BaseModel):
    note: str | None = None
    reason: str | None = None


class BidRequestOut(BaseModel):
    id: int
    bid_id: int | None = None
    bid_number: str
    bid_title: str | None = None
    bid_status: str | None = None
    holder: str | None = None  # managers only
    vendor_id: int
    vendor_name: str | None = None
    note: str | None = None
    status: str
    decision_note: str | None = None
    created_at: datetime | None = None
    decided_at: datetime | None = None
    asked_by_others: int = 0  # other vendors asking for the same bid (managers only)


class VendorLookupOut(BaseModel):
    bid_number: str
    title: str
    bid_type: str
    product_category: str | None = None
    product_type: str | None = None
    end_date: date
    availability: str  # available | mine | allocated | closed
    already_requested: bool = False
    bid_id: int | None = None  # only set for the vendor's own bid


class BidStatRow(BaseModel):
    """One vendor's bid figures (or the totals row): see services/bid_stats.py for what each number means."""

    vendor_id: int | None = None
    vendor_name: str = ""
    allocated: int = 0
    confirmed: int = 0
    submitted: int = 0
    won: int = 0
    lost: int = 0
    declined: int = 0
    expired: int = 0
    holding: int = 0
    confirm_rate: float | None = None  # confirmed out of allocated, per cent
    submit_rate: float | None = None  # submitted out of confirmed
    win_rate: float | None = None  # won out of won + lost


class BidStatMonth(BaseModel):
    month: str  # 2026-10
    label: str  # Oct 26
    allocated: int = 0
    confirmed: int = 0
    submitted: int = 0
    won: int = 0


class BidStatsOut(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    totals: BidStatRow
    vendors: list[BidStatRow] = Field(default_factory=list)
    monthly: list[BidStatMonth] = Field(default_factory=list)


class VendorPick(BaseModel):
    id: int
    vendor_code: str
    name: str
    email: str | None = None
    vendor_types: list[str] = []  # GeM, CSD, Retail, SSD ...: what the vendor works as, set on the vendor login
    categories: list[str] = []  # item categories the vendor supplies; empty = any
