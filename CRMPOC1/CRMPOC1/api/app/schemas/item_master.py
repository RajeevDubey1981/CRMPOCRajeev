from datetime import datetime

from pydantic import BaseModel, Field

CATEGORIES = (
    "Split AC", "Window AC", "Cassette AC", "Duct AC",
    "Geyser", "Refrigerator", "Air Cooler",
    "PCB", "Spare Part", "Accessory", "Others",
)

UNITS = ("Pcs", "Set", "Nos", "Kit", "Kg", "Ltr")


class ItemMasterCreate(BaseModel):
    item_code: str = Field(min_length=1, max_length=100)
    item_name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    description: str | None = None
    brand: str | None = None
    unit: str | None = None
    hsn_code: str | None = None
    mrp: float | None = None
    serial_count: int = Field(default=1, ge=0, le=2)
    is_active: bool = True


class ItemMasterUpdate(BaseModel):
    item_code: str | None = Field(default=None, min_length=1, max_length=100)
    item_name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    description: str | None = None
    brand: str | None = None
    unit: str | None = None
    hsn_code: str | None = None
    mrp: float | None = None
    serial_count: int | None = Field(default=None, ge=0, le=2)
    is_active: bool | None = None


class ItemMasterOut(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: str | None
    description: str | None
    brand: str | None
    unit: str | None
    hsn_code: str | None
    mrp: float | None
    serial_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemMasterListItem(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: str | None
    brand: str | None
    unit: str | None
    hsn_code: str | None
    mrp: float | None
    serial_count: int
    is_active: bool
    created_at: datetime


class ItemMasterListResponse(BaseModel):
    items: list[ItemMasterListItem]
    total: int
    page: int
    per_page: int
