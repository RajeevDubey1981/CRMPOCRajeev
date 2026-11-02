from datetime import datetime

from pydantic import BaseModel, EmailStr


class InsuranceCreate(BaseModel):
    name: str
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None


class InsuranceUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None


class InsuranceOut(BaseModel):
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


class InsuranceListItem(BaseModel):
    id: int
    name: str
    contact_name: str | None
    contact_mobile: str | None
    email: str | None
    address: str | None
    created_at: datetime


class InsuranceListResponse(BaseModel):
    items: list[InsuranceListItem]
    total: int
    page: int
    per_page: int
