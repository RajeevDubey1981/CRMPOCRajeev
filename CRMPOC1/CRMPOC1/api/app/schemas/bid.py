from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
    submit_by: date | None = None
    confirmed_at: datetime | None = None
    submitted_at: datetime | None = None
    submission_ref: str | None = None
    result_note: str | None = None
    days_left: int | None = None
    pending_requests: int = 0
    created_at: datetime | None = None
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


class VendorPick(BaseModel):
    id: int
    vendor_code: str
    name: str
    email: str | None = None
