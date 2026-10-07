from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.geo import canonical_state, clean_pincode


class _Place(BaseModel):
    """Pin code, state and district: checked the same way when a user is created or changed."""

    pincode: str | None = None
    state: str | None = None
    district: str | None = Field(None, max_length=100)

    @field_validator("pincode")
    @classmethod
    def _pin(cls, value):
        return clean_pincode(value)

    @field_validator("state")
    @classmethod
    def _state(cls, value):
        return canonical_state(value)

    @field_validator("district")
    @classmethod
    def _district(cls, value):
        text = " ".join((value or "").split())
        return text or None


class UserCreate(_Place):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = "callcenter"
    phone: str | None = None
    is_active: bool = True
    can_manage_bids: bool = False


class UserUpdate(_Place):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    can_manage_bids: bool | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    phone: str | None = None
    is_active: bool
    can_manage_bids: bool = False
    pincode: str | None = None
    state: str | None = None
    district: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    vendor_id: int | None = None
    vendor_code: str | None = None

    class Config:
        from_attributes = True
