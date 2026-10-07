from pydantic import BaseModel, Field, field_validator

from app.services.geo import canonical_state, clean_pincode


class PlaceIn(BaseModel):
    """Pin code, state and district: checked the same way wherever a place is typed in (users, complaints, installations, services)."""

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
