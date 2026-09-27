from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

ORDER_STATUSES = ("Pending", "Shipped", "In Transit", "Delivered", "Returned", "Cancelled")


class OrderConsigneeAddressCreate(BaseModel):
    consignee_name: str | None = None
    contact: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None


class OrderConsigneeAddressOut(BaseModel):
    id: int
    consignee_name: str | None
    contact: str | None
    email: str | None
    city: str | None
    state: str | None
    address: str | None
    sort_order: int

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    item_id: int | None = None
    item_code: str | None = None
    serial_no: str | None = None
    serial_no_2: str | None = None
    item_qty: int = 1
    pcb_warranty_years: int | None = None
    component_warranty_years: int | None = None
    machine_warranty_years: int | None = None
    free_service_count: int = Field(default=0, ge=0, le=4)
    dry_free_service_count: int | None = Field(default=None, ge=0, le=4)
    wet_free_service_count: int | None = Field(default=None, ge=0, le=4)


class OrderItemOut(BaseModel):
    id: int
    item_id: int | None
    item_code: str | None = None
    item_name: str | None = None  # resolved from item_masters
    serial_count: int = 1  # from item_masters — how many serials per unit (0, 1, or 2)
    serial_no: str | None
    serial_no_2: str | None
    item_qty: int
    pcb_warranty_years: int | None
    component_warranty_years: int | None
    machine_warranty_years: int | None
    free_service_count: int
    dry_free_service_count: int = 0
    wet_free_service_count: int = 0
    service_consume_count: int
    installation_status: str

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    order_no: str | None = None  # optional GEM/Order number
    order_date: date | None = None  # defaults to date.today() in router
    oem_bill_no: str | None = None
    vendor_id: int | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    customer_email: EmailStr | None = None
    customer_city: str | None = None
    customer_state: str | None = None
    customer_address: str | None = None
    courier_id: int | None = None
    lrn_no: str | None = None
    vendor_bill_no: str | None = None
    vendor_bill_date: date | None = None
    status: Literal[ORDER_STATUSES] = "Pending"  # type: ignore[valid-type]
    expected_delivery_date: date | None = None
    items: list[OrderItemCreate] = []
    consignee_addresses: list[OrderConsigneeAddressCreate] = []


class OrderItemUpdate(BaseModel):
    id: int
    item_code: str | None = None
    item_id: int | None = None
    serial_no: str | None = None
    serial_no_2: str | None = None
    pcb_warranty_years: int | None = None
    component_warranty_years: int | None = None
    machine_warranty_years: int | None = None
    free_service_count: int | None = Field(default=None, ge=0, le=4)
    dry_free_service_count: int | None = Field(default=None, ge=0, le=4)
    wet_free_service_count: int | None = Field(default=None, ge=0, le=4)
    installation_status: str | None = None


class OrderVendorLineItemsReplace(BaseModel):
    items: list[OrderItemCreate]


class OrderUpdate(BaseModel):
    order_no: str | None = None
    order_date: date | None = None
    oem_bill_no: str | None = None
    vendor_id: int | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    customer_email: EmailStr | None = None
    customer_city: str | None = None
    customer_state: str | None = None
    customer_address: str | None = None
    courier_id: int | None = None
    lrn_no: str | None = None
    vendor_bill_no: str | None = None
    vendor_bill_date: date | None = None
    status: Literal[ORDER_STATUSES] | None = None  # type: ignore[valid-type]
    expected_delivery_date: date | None = None
    actual_delivery_date: date | None = None
    items: list[OrderItemUpdate] | None = None
    consignee_addresses: list[OrderConsigneeAddressCreate] | None = None


class OrderOut(BaseModel):
    id: int
    order_no: str | None
    order_date: date
    oem_bill_no: str | None
    vendor_id: int | None
    vendor_name: str | None = None  # resolved
    customer_name: str | None
    customer_contact: str | None
    customer_email: str | None
    customer_city: str | None
    customer_state: str | None = None
    customer_address: str | None = None
    courier_id: int | None
    courier_name: str | None = None  # resolved
    lrn_no: str | None
    vendor_bill_no: str | None
    vendor_bill_date: date | None
    status: str
    expected_delivery_date: date | None
    actual_delivery_date: date | None
    order_file_path: str | None = None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []
    consignee_addresses: list[OrderConsigneeAddressOut] = []

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: int
    order_no: str | None
    order_date: date
    oem_bill_no: str | None
    status: str
    order_file_path: str | None = None
    item_code: str | None = None
    vendor_name: str | None = None
    courier_name: str | None = None
    customer_name: str | None
    customer_city: str | None
    expected_delivery_date: date | None
    created_at: datetime


class OrderItemQuantitySummary(BaseModel):
    label: str
    quantity: int


class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    per_page: int
    total_item_quantity: int = 0
    item_quantity_summary: list[OrderItemQuantitySummary] = []


class OrderAutocompleteSuggestion(BaseModel):
    order_id: int
    order_no: str | None = None
    oem_bill_no: str | None = None
    vendor_id: int | None = None
    vendor_code: str | None = None
    vendor_name: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    match_field: str
    display_label: str
