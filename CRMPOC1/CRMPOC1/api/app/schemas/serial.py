from datetime import date

from pydantic import BaseModel


class SerialLookup(BaseModel):
    order_item_id: int
    serial_no: str
    serial_no_2: str | None
    item_name: str | None
    item_code: str | None
    order_no: str | None
    customer_name: str | None
    customer_contact: str | None
    pcb_warranty_date: date | None
    component_warranty_date: date | None
    machine_warranty_date: date | None
    installation_status: str
    free_service_count: int
    service_consume_count: int


class SerialHistoryHeader(BaseModel):
    order_item_id: int
    serial_no: str
    serial_no_2: str | None = None
    item_name: str | None = None
    item_code: str | None = None
    order_no: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    vendor_name: str | None = None
    installation_status: str
    free_service_count: int
    service_consume_count: int
    pcb_warranty_years: int | None = None
    component_warranty_years: int | None = None
    machine_warranty_years: int | None = None
    pcb_warranty_date: date | None = None
    component_warranty_date: date | None = None
    machine_warranty_date: date | None = None


class SerialHistoryEventOut(BaseModel):
    id: int
    event_at: str
    event_type: str
    event_subtype: str | None = None
    performed_by: str | None = None
    title: str
    description: str
    remarks: str | None = None
    metadata: dict | None = None


class SerialEngineerWorked(BaseModel):
    user_id: int
    name: str
    contact: str | None = None
    visits: int


class SerialExpenditureSummary(BaseModel):
    total_paid: float
    parts_cost: float
    service_visits: int
    claims_count: int
    engineers: list[SerialEngineerWorked]


class SerialHistoryResponse(BaseModel):
    header: SerialHistoryHeader
    expenditure: SerialExpenditureSummary
    events: list[SerialHistoryEventOut]
