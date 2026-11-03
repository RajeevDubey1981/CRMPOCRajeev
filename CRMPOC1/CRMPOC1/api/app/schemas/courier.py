from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

COURIER_TYPES = ("parcel", "truck")


class CourierCreate(BaseModel):
    courier_name: str
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    courier_type: Literal[COURIER_TYPES] = "parcel"  # type: ignore[valid-type]
    gst_number: str | None = None
    pan_number: str | None = None
    cin: str | None = None
    registered_state: str | None = None
    bank_account_holder: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_branch: str | None = None


class CourierUpdate(BaseModel):
    courier_name: str | None = None
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    courier_type: Literal[COURIER_TYPES] | None = None  # type: ignore[valid-type]
    gst_number: str | None = None
    pan_number: str | None = None
    cin: str | None = None
    registered_state: str | None = None
    bank_account_holder: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_branch: str | None = None


class CourierOut(BaseModel):
    id: int
    courier_name: str
    contact_name: str | None
    contact_mobile: str | None
    email: str | None
    address: str | None
    courier_type: str = "parcel"
    gst_number: str | None = None
    pan_number: str | None = None
    cin: str | None = None
    registered_state: str | None = None
    bank_account_holder: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_branch: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourierListItem(BaseModel):
    id: int
    courier_name: str
    contact_name: str | None
    contact_mobile: str | None
    email: str | None
    address: str | None
    courier_type: str = "parcel"
    created_at: datetime


class CourierListResponse(BaseModel):
    items: list[CourierListItem]
    total: int
    page: int
    per_page: int
