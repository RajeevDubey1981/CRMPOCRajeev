from datetime import datetime

from pydantic import BaseModel, EmailStr


class ManufacturerCreate(BaseModel):
    name: str
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None


class ManufacturerUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None


class ManufacturerOut(BaseModel):
    id: int
    name: str
    contact_name: str | None
    contact_mobile: str | None
    email: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManufacturerListItem(BaseModel):
    id: int
    name: str
    contact_name: str | None
    contact_mobile: str | None
    email: str | None
    address: str | None
    created_at: datetime


class ManufacturerListResponse(BaseModel):
    items: list[ManufacturerListItem]
    total: int
    page: int
    per_page: int
