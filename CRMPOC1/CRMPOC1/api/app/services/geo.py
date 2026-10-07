"""Places in India: the states, finding a 6 digit pin code in an address, and how near an engineer is to a customer."""

from __future__ import annotations

import re

INDIAN_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh", "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]
_BY_KEY = {re.sub(r"[^a-z]", "", s.lower()): s for s in INDIAN_STATES}
_ALIASES = {"orissa": "Odisha", "pondicherry": "Puducherry", "nctofdelhi": "Delhi", "newdelhi": "Delhi", "uttaranchal": "Uttarakhand"}

PIN_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")


def clean_pincode(value: str | None) -> str | None:
    """The 6 digits of a pin code, or None when empty. Raises ValueError when it is not 6 digits."""
    text = re.sub(r"\s+", "", value or "")
    if not text:
        return None
    if not re.fullmatch(r"[1-9]\d{5}", text):
        raise ValueError("Pin code must be 6 digits")
    return text


def canonical_state(value: str | None) -> str | None:
    """The state spelled the way the list spells it, or None when empty. Raises ValueError when it is not a state."""
    text = (value or "").strip()
    if not text:
        return None
    key = re.sub(r"[^a-z]", "", text.lower())
    found = _BY_KEY.get(key) or _ALIASES.get(key)
    if not found:
        raise ValueError("Choose the state from the list")
    return found


def pincode_in(text: str | None) -> str | None:
    """The last 6 digit pin code written in an address."""
    found = PIN_RE.findall(text or "")
    return found[-1] if found else None


def state_in(text: str | None) -> str | None:
    low = re.sub(r"[^a-z ]", " ", (text or "").lower())
    low = " " + re.sub(r"\s+", " ", low) + " "
    for state in sorted(INDIAN_STATES, key=len, reverse=True):
        if f" {state.lower()} " in low:
            return state
    for alias, state in (("orissa", "Odisha"), ("pondicherry", "Puducherry"), ("new delhi", "Delhi"), ("uttaranchal", "Uttarakhand")):
        if f" {alias} " in low:
            return state
    return None


# how near an engineer is to the customer, nearest first
MATCH_PINCODE, MATCH_AREA, MATCH_DISTRICT, MATCH_STATE, MATCH_NONE = "pincode", "area", "district", "state", ""
_RANK = {MATCH_PINCODE: 0, MATCH_AREA: 1, MATCH_DISTRICT: 2, MATCH_STATE: 3, MATCH_NONE: 4}


def match_rank(match: str) -> int:
    return _RANK.get(match, 4)


def match_engineer(address: str | None, pincode: str | None, state: str | None, district: str | None) -> str:
    """How an engineer's place fits the customer's address: same pin code, same area (first 3 digits), district or state."""
    customer_pin = pincode_in(address)
    low = " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (address or "").lower())) + " "
    if pincode and customer_pin:
        if pincode == customer_pin:
            return MATCH_PINCODE
        if pincode[:3] == customer_pin[:3]:
            return MATCH_AREA
    if district:
        d = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", district.lower())).strip()
        if d and f" {d} " in low:
            return MATCH_DISTRICT
    if state:
        customer_state = state_in(address)
        if customer_state and customer_state == state:
            return MATCH_STATE
    return MATCH_NONE
