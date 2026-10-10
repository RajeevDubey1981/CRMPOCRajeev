from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.place import PlaceIn
from app.services import coverage as coverage_service
from app.services.geo import clean_pincode_list


class _Place(PlaceIn):
    """The place of a user, and the other pin codes an engineer also works in."""

    extra_pincodes: list[str] | None = None
    coverage: dict | None = None
    skills: list[str] | None = None

    @field_validator("extra_pincodes", mode="before")
    @classmethod
    def _extra(cls, value):
        return None if value is None else clean_pincode_list(value)

    @field_validator("coverage", mode="before")
    @classmethod
    def _coverage(cls, value):
        return None if value is None else coverage_service.clean(value)

    @field_validator("skills", mode="before")
    @classmethod
    def _skills(cls, value):
        if value is None:
            return None
        out = list(dict.fromkeys(str(v).strip() for v in value if str(v).strip()))
        if len(out) > 60 or any(len(v) > 80 for v in out):
            raise ValueError("Too many skill categories")
        return out


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
    extra_pincodes: list[str] = []
    coverage: dict | None = None
    skills: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    vendor_id: int | None = None
    vendor_code: str | None = None

    class Config:
        from_attributes = True
