from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.place import PlaceIn

QUERY_TYPES = ("Service", "Installation", "Sales", "Others")
STATUSES = ("Pending", "Under Process", "In Process", "Resolved", "Rejected")
ACTIONS = ("Ask for Invoice", "Request Sent", "Documents Received")
PRIORITIES = ("Normal", "High")


class ComplaintCreate(PlaceIn):
    comp_date: date | None = None
    customer_name: str = Field(min_length=1, max_length=255)
    customer_mobile: str = Field(min_length=10, max_length=20)
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    model_details: str | None = Field(default=None, max_length=255)
    problem_description: str | None = None
    query_type: Literal[QUERY_TYPES] | None = None  # type: ignore[valid-type]
    remark: str | None = None
    send_sms: bool = True
    priority: Literal[PRIORITIES] = "Normal"  # type: ignore[valid-type]

    @field_validator("customer_mobile")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 10:
            raise ValueError("Customer mobile must contain at least 10 digits")
        return digits


class ComplaintUpdate(PlaceIn):
    customer_name: str | None = None
    customer_mobile: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    model_details: str | None = None
    problem_description: str | None = None
    query_type: Literal[QUERY_TYPES] | None = None  # type: ignore[valid-type]
    remark: str | None = None
    status: Literal[STATUSES] | None = None  # type: ignore[valid-type]
    assigned_engineer: int | None = None
    priority: Literal[PRIORITIES] | None = None  # type: ignore[valid-type]


class ComplaintPriorityIn(BaseModel):
    priority: Literal[PRIORITIES]  # type: ignore[valid-type]


class ComplaintLinkCustomer(BaseModel):
    order_id: int | None = None
    order_item_id: int | None = None
    customer_name: str | None = None
    customer_mobile: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    serial_no: str | None = None


class ComplaintStatusUpdate(BaseModel):
    new_status: Literal[STATUSES]  # type: ignore[valid-type]
    access_code: str | None = None
    serial_no: str | None = None
    assigned_engineer: int | None = None
    remark: str | None = None


class ComplaintActionRecord(BaseModel):
    action_taken: Literal[ACTIONS]  # type: ignore[valid-type]
    remark: str | None = None


class ComplaintOut(BaseModel):
    id: int
    comp_no: str
    comp_date: date
    customer_name: str
    customer_mobile: str
    customer_email: str | None
    customer_address: str | None
    pincode: str | None = None
    state: str | None = None
    district: str | None = None
    model_details: str | None
    problem_description: str | None
    query_type: str | None
    status: str
    status_date: datetime | None
    assigned_engineer: int | None
    assigned_engineer_name: str | None = None
    remark: str | None
    service_proof_path: str | None
    access_code: str | None
    send_sms: bool
    created_by: int | None
    order_item_id: int | None = None
    serial_no: str | None = None
    order_id: int | None = None
    order_no: str | None = None
    created_by_name: str | None = None
    source: str
    created_at: datetime
    updated_at: datetime
    email_bounced: bool = False
    email_bounce_reason: str | None = None
    priority: str = "Normal"
    priority_at: datetime | None = None
    priority_by_name: str | None = None

    class Config:
        from_attributes = True


class ComplaintListItem(BaseModel):
    id: int
    comp_no: str
    customer_name: str
    customer_mobile: str
    customer_email: str | None
    customer_address: str | None
    model_details: str | None
    problem_description: str | None
    query_type: str | None
    status: str
    status_date: datetime | None
    assigned_engineer_name: str | None = None
    remark: str | None
    created_by_name: str | None = None
    serial_no: str | None = None
    order_item_id: int | None = None
    created_at: datetime
    call_count: int = 0
    pending_followup_count: int = 0
    last_action_taken: str | None = None
    document_link_sent: bool = False
    customer_documents_received: bool = False
    service_request_id: int | None = None
    service_request_no: str | None = None
    service_request_status: str | None = None
    installation_request_id: int | None = None
    installation_request_status: str | None = None
    email_bounced: bool = False
    email_bounce_reason: str | None = None
    priority: str = "Normal"
    priority_at: datetime | None = None


class ComplaintListResponse(BaseModel):
    items: list[ComplaintListItem]
    total: int
    page: int
    per_page: int
    high_priority_total: int = 0


class ComplaintModelOption(BaseModel):
    id: int
    item_code: str
    item_name: str


class ComplaintHistoryEntry(BaseModel):
    id: int
    old_status: str | None
    new_status: str | None
    changed_by: int | None
    changed_by_name: str | None = None
    remark: str | None
    document_path: str | None
    action_taken: str | None
    changed_at: datetime
