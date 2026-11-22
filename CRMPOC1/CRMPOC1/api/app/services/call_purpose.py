"""What a call was about, so enquiries and complaints can be told apart in the call log."""
from __future__ import annotations

import re

PURPOSES = [
    "Service complaint",
    "Sales enquiry",
    "Installation request",
    "Business or dealer enquiry",
    "Vendor or partner",
    "Job or HR",
    "Wrong number or spam",
    "Other",
]

# Checked in this order; the first that matches wins. A call that matches nothing is "Other".
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Wrong number or spam", re.compile(r"wrong number|spam|prank|robocall|telemarket", re.I)),
    ("Job or HR", re.compile(r"\bjob\b|vacanc|hiring|recruit|career|resume|\bcv\b|interview", re.I)),
    ("Vendor or partner", re.compile(r"\bvendor|supplier|service partner|partner registration|empanel", re.I)),
    ("Business or dealer enquiry", re.compile(r"dealership|distributor|franchis|wholesale|tender|business enquiry|business inquiry|partnership|b2b|bulk order", re.I)),
    ("Installation request", re.compile(r"install", re.I)),
    ("Service complaint", re.compile(r"complaint|not cooling|error|\be6\b|\bf2\b|repair|technician|not working|fault|compressor|gas leak|breakdown|service request", re.I)),
    ("Sales enquiry", re.compile(r"pric|purchase|\bbuy|quot|enquir|inquir|capacity|ton\b|model|available|stock", re.I)),
]


def infer_purpose(*texts: str | None) -> str:
    text = " ".join(t for t in texts if t)
    for purpose, pattern in _RULES:
        if pattern.search(text):
            return purpose
    return "Other"


def clean_purpose(value: str | None) -> str | None:
    """A purpose from the list, or None when it is blank or unknown."""
    v = (value or "").strip()
    return next((p for p in PURPOSES if p.lower() == v.lower()), None)
