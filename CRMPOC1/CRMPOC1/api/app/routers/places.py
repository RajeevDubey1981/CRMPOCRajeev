"""Small public lookups for forms that ask for an address."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.services.pincode_lookup import lookup

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("/pincode/{pin}")
def pincode(pin: str):
    """The state, district and place names of a pin code. Open to the public onboarding form, so it only answers about places."""
    if len(pin) != 6 or not pin.isdigit() or pin[0] == "0":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A pin code has 6 digits and does not start with 0")
    found = lookup(pin)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That pin code was not found")
    return found
