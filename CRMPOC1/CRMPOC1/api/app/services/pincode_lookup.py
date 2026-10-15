"""What a 6 digit pin code tells: its state, district and place names.

The answer comes from India Post's public pin code service and is kept in memory for a day, so a pin code is asked for once.
When that service does not answer, the state is guessed from the first digits of the pin code where those digits point to
one state only (the districts are then chosen from the list by the person).
"""

from __future__ import annotations

import re
import threading
import time
from collections import Counter

import requests

from app.services.geo import canonical_state

URL = "https://api.postalpincode.in/pincode/{pin}"
TIMEOUT = 6
KEEP_SECONDS = 24 * 3600
MAX_KEPT = 5000

_ALIASES = {
    "dadraandnagarhaveli": "Dadra and Nagar Haveli and Daman and Diu",
    "damananddiu": "Dadra and Nagar Haveli and Daman and Diu",
    "andamannicobar": "Andaman and Nicobar Islands",
    "jammuandkashmir": "Jammu and Kashmir",
}

# the first digits that point to one state only; the longer digits win
_PREFIX = {
    "11": "Delhi", "12": "Haryana", "13": "Haryana", "14": "Punjab", "15": "Punjab", "17": "Himachal Pradesh", "18": "Jammu and Kashmir",
    "19": "Jammu and Kashmir", "30": "Rajasthan", "31": "Rajasthan", "32": "Rajasthan", "33": "Rajasthan", "34": "Rajasthan",
    "38": "Gujarat", "37": "Gujarat", "41": "Maharashtra", "42": "Maharashtra", "43": "Maharashtra", "44": "Maharashtra",
    "45": "Madhya Pradesh", "46": "Madhya Pradesh", "47": "Madhya Pradesh", "48": "Madhya Pradesh", "49": "Chhattisgarh",
    "51": "Andhra Pradesh", "52": "Andhra Pradesh", "53": "Andhra Pradesh", "56": "Karnataka", "57": "Karnataka", "58": "Karnataka",
    "59": "Karnataka", "60": "Tamil Nadu", "61": "Tamil Nadu", "62": "Tamil Nadu", "63": "Tamil Nadu", "64": "Tamil Nadu",
    "67": "Kerala", "68": "Kerala", "69": "Kerala", "70": "West Bengal", "71": "West Bengal", "72": "West Bengal", "73": "West Bengal",
    "75": "Odisha", "76": "Odisha", "77": "Odisha", "78": "Assam", "80": "Bihar",
    "160": "Chandigarh", "194": "Ladakh", "403": "Goa", "605": "Puducherry", "737": "Sikkim", "744": "Andaman and Nicobar Islands",
    "790": "Arunachal Pradesh", "791": "Arunachal Pradesh", "792": "Arunachal Pradesh", "793": "Meghalaya", "794": "Meghalaya",
    "795": "Manipur", "796": "Mizoram", "797": "Nagaland", "798": "Nagaland", "799": "Tripura",
}

_kept: dict[str, tuple[float, dict | None]] = {}
_lock = threading.Lock()


def state_from_digits(pin: str) -> str | None:
    return _PREFIX.get(pin[:3]) or _PREFIX.get(pin[:2])


def _state_name(raw: str | None) -> str | None:
    key = re.sub(r"[^a-z]", "", (raw or "").lower().replace("&", "and"))
    if key in _ALIASES:
        return _ALIASES[key]
    try:
        return canonical_state(raw.replace("&", "and")) if raw else None
    except ValueError:
        return None


def _ask(pin: str) -> dict | None:
    try:
        r = requests.get(URL.format(pin=pin), timeout=TIMEOUT, headers={"User-Agent": "INDcool-CRM"})
        data = r.json()
    except Exception:
        return None  # not answered: the caller may try again later
    block = data[0] if isinstance(data, list) and data else None
    offices = (block or {}).get("PostOffice") if isinstance(block, dict) else None
    if not offices:
        return {}  # answered: no such pin code
    states = Counter(_state_name(o.get("State")) for o in offices if o.get("State"))
    state = states.most_common(1)[0][0] if states else None
    districts = Counter((o.get("District") or "").strip() for o in offices if (o.get("District") or "").strip())
    district = districts.most_common(1)[0][0] if districts else ""
    blocks = Counter((o.get("Block") or o.get("Division") or "").strip() for o in offices if (o.get("Block") or o.get("Division") or "").strip())
    return {
        "pincode": pin, "state": state or state_from_digits(pin) or "", "district": district, "city": blocks.most_common(1)[0][0] if blocks else district,
        "places": [o.get("Name") for o in offices if o.get("Name")][:12], "source": "India Post",
    }


def lookup(pin: str) -> dict | None:
    """The state, district and place names of a pin code, or None when it cannot be told (no answer and no clear first digits)."""
    if not re.fullmatch(r"[1-9]\d{5}", pin or ""):
        return None
    now = time.time()
    with _lock:
        hit = _kept.get(pin)
        if hit and now - hit[0] < KEEP_SECONDS:
            return hit[1]
    answer = _ask(pin)
    if answer is None:  # India Post did not answer: the first digits are the best we have, and are not kept for long
        state = state_from_digits(pin)
        return {"pincode": pin, "state": state, "district": "", "city": "", "places": [], "source": "first digits"} if state else None
    result = answer or None
    with _lock:
        if len(_kept) >= MAX_KEPT:
            _kept.clear()
        _kept[pin] = (now, result)
    return result
