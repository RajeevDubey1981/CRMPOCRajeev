from datetime import datetime
from pydantic import BaseModel


class CallCreate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    phone: str | None = None
    call_type: str | None = None
    status: str | None = None
    priority: str = "medium"
    call_datetime: datetime
    duration_secs: int | None = None
    followup_date: datetime | None = None
    notes: str | None = None
    follow_up_notes: str | None = None
    complaint_id: int | None = None
    purpose: str | None = None


class CallUpdate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    phone: str | None = None
    call_type: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: int | None = None
    duration_secs: int | None = None
    followup_date: datetime | None = None
    notes: str | None = None
    follow_up_notes: str | None = None
    follow_up_status: str | None = None
    purpose: str | None = None


class CallTransfer(BaseModel):
    transferred_to: int
    transfer_notes: str | None = None


class CallListItem(BaseModel):
    id: int
    ref_no: str
    customer_name: str | None
    phone: str | None
    call_type: str | None
    status: str | None
    priority: str
    assigned_to_name: str | None
    transferred_to_name: str | None
    is_transferred: bool
    call_datetime: datetime
    duration_secs: int | None
    followup_date: datetime | None
    follow_up_status: str | None
    complaint_id: int | None
    has_recording: bool = False
    purpose: str | None = None


class CallListResponse(BaseModel):
    items: list[CallListItem]
    total: int
    page: int
    per_page: int
    stats: dict | None = None


class CallOut(BaseModel):
    id: int
    ref_no: str
    customer_name: str | None
    customer_email: str | None
    phone: str | None
    call_type: str | None
    status: str | None
    priority: str
    assigned_to: int | None
    assigned_to_name: str | None
    transferred_to: int | None
    transferred_to_name: str | None
    is_transferred: bool
    duration_secs: int | None
    call_datetime: datetime
    followup_date: datetime | None
    follow_up_notes: str | None
    follow_up_status: str | None
    notes: str | None
    complaint_id: int | None
    created_at: datetime
    updated_at: datetime
    has_recording: bool = False
    purpose: str | None = None
