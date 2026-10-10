"""Coverage of a person (a sales person or an engineer): All India, or selected states where each state is the whole
state or some districts, plus extra pin codes. Stored as JSON text:
{"mode": "all" | "states", "states": {"Uttar Pradesh": {"all": false, "districts": ["Ghaziabad"], "pins": ["201301"]}}}"""

from __future__ import annotations

import json
import re

ALL, STATES = "all", "states"
# how well a place fits a coverage: 0 = outside, 1 = the person covers all India, 2 = named (state, district or pin code)
OUTSIDE, ANYWHERE, NAMED = 0, 1, 2


def plain(text) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def clean(raw) -> dict:
    """The coverage as it is stored. Raises ValueError with a sentence the person can read."""
    if not isinstance(raw, dict) or raw.get("mode") not in (ALL, STATES):
        raise ValueError("Choose All India or Selected states")
    if raw["mode"] == ALL:
        return {"mode": ALL, "states": {}}
    states = raw.get("states") or {}
    if not isinstance(states, dict) or len(states) > 40:
        raise ValueError("The states are not valid")
    out: dict = {}
    for name, row in states.items():
        name = str(name).strip()
        if not name or not isinstance(row, dict):
            raise ValueError("The states are not valid")
        districts = [str(d).strip() for d in (row.get("districts") or []) if str(d).strip()]
        pins = [str(p).strip() for p in (row.get("pins") or []) if str(p).strip()]
        if len(districts) > 100 or len(pins) > 500:
            raise ValueError(f"Too many districts or pin codes for {name}")
        bad = [p for p in pins if not re.fullmatch(r"[1-9]\d{5}", p)]
        if bad:
            raise ValueError(f"Pin codes have 6 digits: {', '.join(bad[:5])}")
        whole = bool(row.get("all"))
        if not whole and not districts and not pins:
            raise ValueError(f"{name}: choose the whole state, some districts, or add pin codes")
        out[name] = {"all": whole, "districts": [] if whole else list(dict.fromkeys(districts)), "pins": list(dict.fromkeys(pins))}
    return {"mode": STATES, "states": out}


def load(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def fit(cov: dict | None, *, state: str | None = None, district: str | None = None, pin: str | None = None, text: str = "") -> tuple[int, str]:
    """How a place fits a coverage. Returns (level, kind) where kind is "pin", "district", "state" or "" (all India / outside).
    `text` is an address: a covered district written in it counts when no district was typed."""
    if not cov:
        return OUTSIDE, ""
    if cov.get("mode") == ALL:
        return ANYWHERE, ""
    pin = (pin or "").strip()
    low = " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())) + " "
    best: tuple[int, str] = (OUTSIDE, "")
    for name, row in (cov.get("states") or {}).items():
        if pin and pin in (row.get("pins") or []):
            return NAMED, "pin"
        if state and plain(state) == plain(name):
            if row.get("all"):
                best = (NAMED, "state")
                continue
            for d in row.get("districts") or []:
                if (district and plain(district) == plain(d)) or (not district and plain(d) and f" {re.sub(r'[^a-z0-9 ]', ' ', d.lower()).strip()} " in low):
                    return NAMED, "district"
    return best
