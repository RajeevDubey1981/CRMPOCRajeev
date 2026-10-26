"""Best-effort matching of a bank statement line's free-text description against vendors and
engineers: phone number first (strongest signal), then vendor/engineer code, then company/person name
(weakest). Returns a 0-1 confidence Accounts can use to decide whether to trust the suggestion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vendor import Vendor
from app.services.role_access import ENGINEER_ROLE_NAMES

PHONE_CONFIDENCE = 0.95
CODE_CONFIDENCE = 0.85
NAME_CONFIDENCE = 0.6


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _normalize(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


@dataclass
class _Candidate:
    party_type: str
    party_id: int
    label: str
    phone: str | None
    code: str | None


def _candidates(db: Session) -> list[_Candidate]:
    out: list[_Candidate] = []
    for v in db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None))):
        out.append(_Candidate("vendor", v.id, v.name_of_firm, v.contact_mobile, v.vendor_code))
    engineers = db.scalars(
        select(User).where(User.deleted_at.is_(None), func.lower(func.trim(User.role)).in_(ENGINEER_ROLE_NAMES))
    )
    for u in engineers:
        out.append(_Candidate("engineer", u.id, u.name, u.phone, f"ENG-{u.id:04d}"))
    return out


def match_description(db: Session, description: str) -> tuple[str | None, int | None, float, str]:
    """Returns (party_type, party_id, confidence, reason) for the single best match, or
    (None, None, 0.0, "") when nothing in the description points at a vendor or engineer."""
    norm_text = _normalize(description)
    digits_text = _digits(description)
    best: tuple[str | None, int | None, float, str] = (None, None, 0.0, "")

    for c in _candidates(db):
        phone_digits = _digits(c.phone)
        if phone_digits and len(phone_digits) >= 10 and phone_digits[-10:] in digits_text and PHONE_CONFIDENCE > best[2]:
            best = (c.party_type, c.party_id, PHONE_CONFIDENCE, f"phone {c.phone} found in statement line")
            continue
        code_norm = _normalize(c.code)
        if code_norm and len(code_norm) >= 4 and code_norm in norm_text and CODE_CONFIDENCE > best[2]:
            best = (c.party_type, c.party_id, CODE_CONFIDENCE, f"code {c.code} found in statement line")
            continue
        name_norm = _normalize(c.label)
        if name_norm and len(name_norm) >= 5 and name_norm in norm_text and NAME_CONFIDENCE > best[2]:
            best = (c.party_type, c.party_id, NAME_CONFIDENCE, f'name "{c.label}" found in statement line')

    return best
