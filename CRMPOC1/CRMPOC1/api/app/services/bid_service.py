"""Bid management rules: category detection, forgiving search, allocation, locks, auto release, reminders, emails.

One bid has one bidder at a time. Allocating locks the bid. The bidder must confirm by `confirm_by` and submit on the
portal by `submit_by`, otherwise the bid goes back to Open for allocation. Past the end date an unsubmitted bid is
Closed. Admin / sub admin may override a locked bid with a written reason.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from html import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bid import Bid, BidEvent, BidReminder, BidRequest
from app.models.user import User
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
SELF_NAME = "INDcool (Self)"
LIVE_STATUSES = ("Open", "Allocated", "Confirmed", "Submitted")
HELD_STATUSES = ("Allocated", "Confirmed", "Submitted")
BID_TYPES = ("GeM", "State govt")

# Categories and product types copied from the INDcool website. The item words pick both.
TYPES: dict[str, list[str]] = {
    "Residential Air Conditioners": ["Split AC", "Window AC", "Cassette AC", "Tower AC"],
    "Commercial Air Conditioners": ["VRF AC", "Ductable AC"],
    "Solar Air Conditioners": ["Split AC", "Window AC", "Cassette AC", "Tower AC"],
    "Refrigerator": ["Single Door", "Double Door"],
    "Deep Freezer": ["Glass Top", "Hard Top"],
    "Washing Machines": ["Top Load", "Front Load"],
    "Water Cooler": ["All in one with RO (UV)", "Hot & Cold", "Cold Only", "Inbuilt RO"],
    "Fans": ["Ceiling Fan", "Exhaust Fan"],
    "Geysers": ["Vertical", "Horizontal"],
    "Other Appliances": ["Air Cooler", "Other"],
}


class BidError(Exception):
    """A rule was broken. `status` is the HTTP status the router should answer with."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def today_ist() -> date:
    return datetime.now(IST).date()


def now_ist_hour() -> int:
    return datetime.now(IST).hour


# --------------------------------------------------------------------------- category detection

def _pick(text: str, rules: list[tuple[str, str]]) -> str:
    for name, pattern in rules:
        if re.search(pattern, text):
            return name
    return ""


def detect_category(text: str | None) -> dict:
    """Pick the product category and type from the words of the bid title. No tonnage, only what the website lists."""
    t = (text or "").lower()
    ac_type = _pick(t, [("Split AC", r"split"), ("Window AC", r"window"), ("Cassette AC", r"cassette"), ("Tower AC", r"tower")])
    if re.search(r"\bvrf\b|\bvrv\b", t):
        return {"name": "Commercial Air Conditioners", "type": "VRF AC", "hit": True}
    if re.search(r"ductable|ducted|duct ac", t):
        return {"name": "Commercial Air Conditioners", "type": "Ductable AC", "hit": True}
    if "solar" in t:
        return {"name": "Solar Air Conditioners", "type": ac_type, "hit": True}
    if ac_type or re.search(r"\bac\b|air.?condition", t):
        return {"name": "Residential Air Conditioners", "type": ac_type, "hit": True}
    if re.search(r"deep ?freezer|chest freezer|freezer", t):
        return {"name": "Deep Freezer", "type": _pick(t, [("Glass Top", r"glass"), ("Hard Top", r"hard")]), "hit": True}
    if re.search(r"refrigerator|fridge|single door|double door|frost free|direct cool", t):
        return {"name": "Refrigerator", "type": _pick(t, [("Double Door", r"double"), ("Single Door", r"single")]), "hit": True}
    if re.search(r"washing machine|top load|front load", t):
        return {"name": "Washing Machines", "type": _pick(t, [("Top Load", r"top"), ("Front Load", r"front")]), "hit": True}
    if re.search(r"water cooler|water dispenser|bottle cooler", t):
        return {
            "name": "Water Cooler",
            "type": _pick(t, [("All in one with RO (UV)", r"all.?in.?one|uv"), ("Inbuilt RO", r"in.?built"), ("Hot & Cold", r"hot"), ("Cold Only", r"cold")]),
            "hit": True,
        }
    if re.search(r"geyser|water heater", t):
        return {"name": "Geysers", "type": _pick(t, [("Vertical", r"vertic"), ("Horizontal", r"horizon")]), "hit": True}
    if re.search(r"\bfans?\b|exhaust", t):
        return {"name": "Fans", "type": _pick(t, [("Exhaust Fan", r"exhaust"), ("Ceiling Fan", r"ceiling")]), "hit": True}
    if re.search(r"air cooler|desert cooler", t):
        return {"name": "Other Appliances", "type": "Air Cooler", "hit": True}
    return {"name": "Other Appliances", "type": "Other", "hit": False}


# --------------------------------------------------------------------------- forgiving search

def norm(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def approx_has(q: str, t: str, max_err: int) -> bool:
    """True when q occurs inside t with at most max_err single-character mistakes (Sellers' approximate substring)."""
    m, n = len(q), len(t)
    prev = list(range(m + 1))
    best = prev[m]
    for j in range(1, n + 1):
        cur = [0] * (m + 1)
        for i in range(1, m + 1):
            cost = 0 if q[i - 1] == t[j - 1] else 1
            cur[i] = min(prev[i] + 1, cur[i - 1] + 1, prev[i - 1] + cost)
        best = min(best, cur[m])
        prev = cur
    return best <= max_err


def _token_ok(token: str, text_norm: str) -> bool:
    q = norm(token)
    if not q:
        return True
    if q in text_norm:
        return True
    errors = 2 if len(q) >= 6 else 1 if len(q) >= 4 else 0
    return errors > 0 and approx_has(q, text_norm, errors)


def fuzzy_match(query: str | None, text: str | None) -> bool:
    """Spaces, slashes and case are ignored, words can come in any order, a character or two may be wrong."""
    whole = norm(query)
    if not whole:
        return True
    text_norm = norm(text)
    if whole in text_norm:
        return True
    tokens = [x for x in re.split(r"\s+", query or "") if x]
    if len(tokens) > 1 and all(_token_ok(tok, text_norm) for tok in tokens):
        return True
    return _token_ok(query or "", text_norm)


def search_rank(query: str | None, bid_number: str) -> int:
    q = norm(query)
    return 0 if q and q in norm(bid_number) else 1


# --------------------------------------------------------------------------- helpers

def vendor_label(bid: Bid, vendor: Vendor | None) -> str | None:
    if bid.is_self:
        return SELF_NAME
    return vendor.name_of_firm if vendor else None


def add_event(
    db: Session,
    bid: Bid,
    actor: User | None,
    action: str,
    text: str,
    *,
    vendor_id: int | None = None,
    actor_name: str | None = None,
) -> BidEvent:
    event = BidEvent(
        bid_id=bid.id,
        actor_name=actor_name or (actor.name if actor else "System"),
        actor_user_id=actor.id if actor else None,
        action=action,
        text=text,
        vendor_id=vendor_id,
    )
    db.add(event)
    return event


def fmt_date(value: date | None) -> str:
    return f"{value.day} {value.strftime('%b %Y')}" if value else "-"


def find_bid_by_number(db: Session, number: str) -> Bid | None:
    n = norm(number)
    if not n:
        return None
    exact = db.scalar(select(Bid).where(func.upper(Bid.bid_number) == (number or "").strip().upper()))
    if exact is not None:
        return exact
    for bid in db.scalars(select(Bid)).all():
        if norm(bid.bid_number) == n:
            return bid
    return None


def similar_bids(db: Session, number: str, exclude_id: int | None = None, limit: int = 3) -> list[Bid]:
    """Bids that share the long number part of this bid number (7960553 in GEM/2026/B/7960553) but are not the same text.
    Catches a bid typed without its prefix, or with a different prefix."""
    n = norm(number)
    runs = re.findall(r"\d{5,}", number or "")
    if not runs:
        return []
    found: list[Bid] = []
    for bid in db.scalars(select(Bid).order_by(Bid.id.desc())).all():
        if exclude_id is not None and bid.id == exclude_id:
            continue
        other = norm(bid.bid_number)
        if other == n:
            continue
        if any(run in other for run in runs):
            found.append(bid)
            if len(found) >= limit:
                break
    return found


# --------------------------------------------------------------------------- emails

_outbox = threading.local()


def _queue() -> list:
    if not hasattr(_outbox, "items"):
        _outbox.items = []
    return _outbox.items


def discard_outbox() -> None:
    _queue().clear()


def flush_outbox() -> None:
    """Send the mails queued by this request. Called after the database commit, so a mail is never sent for an
    action that was rolled back, and a slow mail server never holds a database transaction open."""
    items = list(_queue())
    _queue().clear()
    for to, subject, lines in items:
        _deliver(to, subject, lines)


def _send(to: str | None, subject: str, lines: list[str]) -> bool:
    """Queue a plain notification mail for after the commit. True when there is somebody to send it to."""
    if not (to or "").strip():
        return False
    _queue().append((to, subject, lines))
    return True


def _deliver(to: str | None, subject: str, lines: list[str]) -> bool:
    """Send one mail now. A mail problem never breaks the bid action that caused it."""
    if not (to or "").strip():
        return False
    try:
        from app.services.email_service import send_email

        body = "".join(f"<p style=\"margin:0 0 10px\">{escape(line)}</p>" for line in lines)
        html = f"<div style=\"font-family:Arial,sans-serif;font-size:14px;color:#222\">{body}<p>TEAM INDcool</p></div>"
        text = "\n\n".join(lines) + "\n\nTEAM INDcool"
        return bool(send_email(to.strip(), subject, html, text))
    except Exception:
        logger.exception("bid email failed: %s", subject)
        return False


def team_emails(db: Session) -> list[str]:
    configured = [x.strip() for x in (settings.bid_team_email or "").split(",") if x.strip()]
    if configured:
        return configured
    rows = db.scalars(
        select(User.email).where(
            User.can_manage_bids.is_(True), User.is_active.is_(True), User.deleted_at.is_(None), User.role != "vendor"
        )
    ).all()
    return [e for e in rows if e]


def _mail_team(db: Session, subject: str, lines: list[str]) -> None:
    for to in team_emails(db):
        _send(to, subject, lines)


def _mail_vendor(vendor: Vendor | None, subject: str, lines: list[str]) -> bool:
    return _send(vendor.email if vendor else None, subject, lines)


def _bid_lines(bid: Bid) -> list[str]:
    return [
        f"Bid number: {bid.bid_number}",
        f"Item: {bid.title}",
        f"Closing date: {fmt_date(bid.end_date)}",
    ]


# --------------------------------------------------------------------------- entering and editing

def apply_category(bid: Bid) -> None:
    """Fill category and type from the title when the entry form left them empty."""
    if bid.product_category and bid.product_category in TYPES:
        if bid.product_type and bid.product_type not in TYPES[bid.product_category]:
            bid.product_type = None
        return
    hit = detect_category(" ".join(x for x in (bid.title, bid.department) if x))
    bid.product_category = hit["name"]
    bid.product_type = hit["type"] or None


def link_requests_to_bid(db: Session, bid: Bid) -> int:
    n = norm(bid.bid_number)
    linked = 0
    for req in db.scalars(select(BidRequest).where(BidRequest.bid_id.is_(None), BidRequest.status == "Requested")).all():
        if norm(req.bid_number) == n:
            req.bid_id = bid.id
            linked += 1
    return linked


# --------------------------------------------------------------------------- allocation and workflow

def dates_for_allocation(bid: Bid, today: date) -> tuple[date, date]:
    confirm_by = today + timedelta(days=max(0, settings.bid_confirm_days))
    submit_by = bid.end_date - timedelta(days=max(0, settings.bid_submit_buffer_days))
    if submit_by <= today:
        nxt = today + timedelta(days=1)
        submit_by = bid.end_date if nxt > bid.end_date else nxt
    return confirm_by, submit_by


def refresh_bid(db: Session, bid: Bid, today: date | None = None) -> str | None:
    """Apply the time rules to one bid. Returns 'released', 'closed' or None."""
    today = today or today_ist()
    if bid.status == "Allocated" and bid.confirm_by and today > bid.confirm_by and not bid.is_self:
        who = _vendor_name(db, bid)
        release_bid(db, bid, f"{who} did not confirm by {fmt_date(bid.confirm_by)}", None, automatic=True)
        return "released"
    if (
        bid.status == "Confirmed" and not bid.is_self and bid.submit_by
        and today > bid.submit_by and today <= bid.end_date
    ):
        who = _vendor_name(db, bid)
        release_bid(db, bid, f"{who} did not submit by {fmt_date(bid.submit_by)}", None, automatic=True)
        return "released"
    if today > bid.end_date and bid.status in ("Open", "Allocated", "Confirmed"):
        who = _vendor_name(db, bid) if bid.vendor_id or bid.is_self else None
        bid.status = "Closed"
        add_event(db, bid, None, "closed", "Bid end date passed without a submission. The bid is closed", vendor_id=bid.vendor_id)
        _mail_team(db, f"Bid closed without a submission: {bid.bid_number}", _bid_lines(bid) + ["The end date passed and nothing was submitted."])
        if bid.vendor_id:
            _mail_vendor(db.get(Vendor, bid.vendor_id), f"Bid closed: {bid.bid_number}", _bid_lines(bid) + ["This bid closed without a submission."])
        return "closed"
    return None


def _vendor_name(db: Session, bid: Bid) -> str:
    if bid.is_self:
        return SELF_NAME
    vendor = db.get(Vendor, bid.vendor_id) if bid.vendor_id else None
    return vendor.name_of_firm if vendor else "The bidder"


def allocate_bid(
    db: Session,
    bid: Bid,
    *,
    vendor: Vendor | None,
    self_bid: bool,
    actor: User,
    can_override: bool,
    reason: str | None = None,
    today: date | None = None,
) -> Bid:
    today = today or today_ist()
    refresh_bid(db, bid, today)
    if not self_bid and vendor is None:
        raise BidError("Choose a vendor, or INDcool (Self)")
    if bid.status in ("Won", "Lost"):
        raise BidError("This bid already has a result", 409)
    if bid.status == "Closed" or today > bid.end_date:
        raise BidError("This bid has ended and can no longer be allocated", 409)
    holder = _vendor_name(db, bid) if bid.status in HELD_STATUSES else None
    override = holder is not None
    if override:
        if not can_override:
            raise BidError(f"Already allocated to {holder}. Only an admin or sub admin can override it", 409)
        if not (reason or "").strip():
            raise BidError("Give a reason to override a locked bid")
    prev_vendor = db.get(Vendor, bid.vendor_id) if bid.vendor_id else None
    bid.vendor_id = None if self_bid else vendor.id
    bid.is_self = bool(self_bid)
    bid.allocated_at = datetime.now(timezone.utc)
    bid.confirm_by, bid.submit_by = dates_for_allocation(bid, today)
    bid.confirmed_at = None
    bid.submitted_at = None
    bid.submission_ref = None
    new_name = SELF_NAME if self_bid else vendor.name_of_firm
    if self_bid:
        bid.status = "Confirmed"
        bid.confirmed_at = datetime.now(timezone.utc)
        tail = ". INDcool bids itself, so it is confirmed at once"
    else:
        bid.status = "Allocated"
        tail = f". Confirm by {fmt_date(bid.confirm_by)}, submit by {fmt_date(bid.submit_by)}"
    if override:
        text = f"ADMIN OVERRIDE: reassigned from {holder} to {new_name}. Reason: {reason.strip()}{tail}"
        add_event(db, bid, actor, "override", text, vendor_id=bid.vendor_id)
    else:
        add_event(db, bid, actor, "allocated", f"Allocated to {new_name}{tail}", vendor_id=bid.vendor_id)
    db.flush()
    if not self_bid:
        _mail_vendor(
            vendor,
            f"Bid allocated to you: {bid.bid_number}",
            ["A bid has been allocated to you by INDcool."] + _bid_lines(bid) + [
                f"Please confirm in the CRM by {fmt_date(bid.confirm_by)}. After that the bid goes back to INDcool.",
                f"Submit on the portal by {fmt_date(bid.submit_by)}.",
            ],
        )
    if override and prev_vendor is not None and (self_bid or prev_vendor.id != vendor.id):
        _mail_vendor(
            prev_vendor,
            f"Bid taken back by INDcool: {bid.bid_number}",
            ["INDcool has taken this bid back."] + _bid_lines(bid) + [f"Reason: {reason.strip()}"],
        )
        add_event(db, bid, actor, "taken_back", f"Taken back from {prev_vendor.name_of_firm}", vendor_id=prev_vendor.id)
    if override:
        _mail_team(db, f"Admin override on bid {bid.bid_number}", _bid_lines(bid) + [f"Now with {new_name}.", f"Reason: {reason.strip()}"])
    return bid


def release_bid(
    db: Session,
    bid: Bid,
    why: str,
    actor: User | None,
    *,
    automatic: bool = False,
    notify_vendor: bool = True,
) -> Bid:
    prev_vendor = db.get(Vendor, bid.vendor_id) if bid.vendor_id else None
    prev_name = SELF_NAME if bid.is_self else (prev_vendor.name_of_firm if prev_vendor else None)
    bid.vendor_id = None
    bid.is_self = False
    bid.status = "Open"
    bid.confirm_by = None
    bid.submit_by = None
    bid.allocated_at = None
    bid.confirmed_at = None
    add_event(
        db, bid, actor, "released" if not automatic else "auto_released",
        f"Released: {why}. The bid is free for allocation again",
        vendor_id=prev_vendor.id if prev_vendor else None,
        actor_name=None if actor else "System",
    )
    db.flush()
    _mail_team(db, f"Bid is free again: {bid.bid_number}", _bid_lines(bid) + [why])
    if prev_vendor is not None and notify_vendor:
        _mail_vendor(prev_vendor, f"Bid released from you: {bid.bid_number}", _bid_lines(bid) + [why])
    return bid


def confirm_bid(db: Session, bid: Bid, actor: User, *, on_behalf: bool = False, today: date | None = None) -> Bid:
    today = today or today_ist()
    refresh_bid(db, bid, today)
    if bid.status != "Allocated":
        if bid.status == "Open":
            raise BidError("The confirmation time is over, so the bid went back to INDcool", 409)
        raise BidError("This bid is not waiting for confirmation", 409)
    bid.status = "Confirmed"
    bid.confirmed_at = datetime.now(timezone.utc)
    who = _vendor_name(db, bid)
    suffix = f" (confirmed by {actor.name} for them)" if on_behalf else ""
    add_event(db, bid, actor, "confirmed", f"{who} confirmed bidding{suffix}", vendor_id=bid.vendor_id)
    _mail_team(db, f"{who} confirmed bid {bid.bid_number}", _bid_lines(bid) + [f"Submit on the portal by {fmt_date(bid.submit_by)}."])
    return bid


def decline_bid(db: Session, bid: Bid, actor: User, reason: str | None = None) -> Bid:
    if bid.status != "Allocated":
        raise BidError("Only a bid that is waiting for your confirmation can be declined", 409)
    who = _vendor_name(db, bid)
    why = f"{who} declined" + (f": {reason.strip()}" if (reason or "").strip() else "")
    release_bid(db, bid, why, actor, notify_vendor=False)
    return bid


def submit_bid(db: Session, bid: Bid, actor: User, reference: str | None = None, *, today: date | None = None) -> Bid:
    today = today or today_ist()
    refresh_bid(db, bid, today)
    if bid.status != "Confirmed":
        if bid.status == "Open":
            raise BidError("This bid went back to INDcool because it was not submitted in time", 409)
        if bid.status == "Closed":
            raise BidError("This bid has closed", 409)
        raise BidError("Confirm the bid before marking it submitted", 409)
    if today > bid.end_date:
        raise BidError("The bid end date has passed", 409)
    bid.status = "Submitted"
    bid.submitted_at = datetime.now(timezone.utc)
    bid.submission_ref = (reference or "").strip() or None
    who = _vendor_name(db, bid)
    add_event(
        db, bid, actor, "submitted",
        f"{who} marked it submitted" + (f". Acknowledgement {bid.submission_ref}" if bid.submission_ref else ""),
        vendor_id=bid.vendor_id,
    )
    _mail_team(db, f"Bid submitted: {bid.bid_number}", _bid_lines(bid) + [f"Submitted by {who}." + (f" Acknowledgement {bid.submission_ref}." if bid.submission_ref else "")])
    return bid


def set_result(db: Session, bid: Bid, actor: User, result: str, note: str | None = None) -> Bid:
    if result not in ("Won", "Lost"):
        raise BidError("Result must be Won or Lost")
    if bid.status != "Submitted":
        raise BidError("Only a submitted bid can get a result", 409)
    bid.status = result
    bid.result_note = (note or "").strip() or None
    add_event(db, bid, actor, "result", f"Result: {result}" + (f". {bid.result_note}" if bid.result_note else ""), vendor_id=bid.vendor_id)
    if bid.vendor_id:
        _mail_vendor(db.get(Vendor, bid.vendor_id), f"Bid result: {bid.bid_number} {result}", _bid_lines(bid) + [f"Result: {result}."] + ([bid.result_note] if bid.result_note else []))
    return bid


# --------------------------------------------------------------------------- vendor requests

def availability_for(db: Session, bid: Bid | None, vendor: Vendor) -> str:
    """What a vendor may be told about a bid: available | mine | allocated | closed | unknown. Never who holds it."""
    if bid is None:
        return "unknown"
    if bid.status == "Open":
        return "available"
    if bid.vendor_id == vendor.id and not bid.is_self:
        return "mine"
    if bid.status in HELD_STATUSES:
        return "allocated"
    return "closed"


def create_request(db: Session, vendor: Vendor, user: User, bid_number: str, note: str | None) -> BidRequest:
    number = (bid_number or "").strip()
    if len(norm(number)) < 3:
        raise BidError("Type the bid number")
    bid = find_bid_by_number(db, number)
    if bid is not None:
        refresh_bid(db, bid)
        state = availability_for(db, bid, vendor)
        if state == "allocated":
            raise BidError("Already allocated", 409)
        if state == "mine":
            raise BidError("This bid is already allocated to you", 409)
        if state == "closed":
            raise BidError("This bid is closed", 409)
    for req in db.scalars(select(BidRequest).where(BidRequest.vendor_id == vendor.id, BidRequest.status == "Requested")).all():
        if norm(req.bid_number) == norm(number):
            raise BidError("You have already asked for this bid", 409)
    request = BidRequest(
        bid_id=bid.id if bid else None,
        bid_number=bid.bid_number if bid else number,
        vendor_id=vendor.id,
        note=(note or "").strip() or None,
        status="Requested",
        requested_by_id=user.id,
    )
    db.add(request)
    db.flush()
    if bid is not None:
        add_event(db, bid, user, "requested", f"{vendor.name_of_firm} asked for this bid", vendor_id=vendor.id)
    _mail_team(
        db,
        f"Bid request from {vendor.name_of_firm}: {request.bid_number}",
        [f"{vendor.name_of_firm} has asked for bid {request.bid_number}."]
        + ([f"Note: {request.note}"] if request.note else [])
        + (["This bid is not entered in the CRM yet. Please enter it."] if bid is None else ["It is free for allocation."]),
    )
    return request


def decline_request(db: Session, request: BidRequest, actor: User, note: str | None = None) -> BidRequest:
    if request.status != "Requested":
        raise BidError("This request was already answered", 409)
    request.status = "Declined"
    request.decision_note = (note or "").strip() or None
    request.decided_by_id = actor.id
    request.decided_at = datetime.now(timezone.utc)
    vendor = db.get(Vendor, request.vendor_id)
    _mail_vendor(
        vendor, f"Your bid request was declined: {request.bid_number}",
        [f"INDcool could not give you bid {request.bid_number}."] + ([request.decision_note] if request.decision_note else []),
    )
    return request


def allocate_from_request(db: Session, request: BidRequest, actor: User, *, can_override: bool, reason: str | None = None) -> Bid:
    if request.status != "Requested":
        raise BidError("This request was already answered", 409)
    bid = db.get(Bid, request.bid_id) if request.bid_id else None
    if bid is None:
        raise BidError("Enter this bid first, then allocate it", 409)
    vendor = db.get(Vendor, request.vendor_id)
    allocate_bid(db, bid, vendor=vendor, self_bid=False, actor=actor, can_override=can_override, reason=reason)
    request.status = "Allocated"
    request.decided_by_id = actor.id
    request.decided_at = datetime.now(timezone.utc)
    for other in db.scalars(
        select(BidRequest).where(BidRequest.bid_id == bid.id, BidRequest.status == "Requested", BidRequest.id != request.id)
    ).all():
        other.status = "Not available"
        other.decision_note = "Already allocated"
        other.decided_by_id = actor.id
        other.decided_at = datetime.now(timezone.utc)
        _mail_vendor(
            db.get(Vendor, other.vendor_id), f"Bid not available: {bid.bid_number}",
            [f"Bid {bid.bid_number} has been allocated already, so INDcool cannot give it to you."],
        )
    return bid


# --------------------------------------------------------------------------- scheduled rules and reminders

def run_rules(db: Session, today: date | None = None, *, send_reminders: bool = True) -> dict:
    """Release late bids, close ended bids and send the daily reminders. Safe to run many times a day."""
    today = today or today_ist()
    summary = {"released": 0, "closed": 0, "reminders": 0}
    for bid in db.scalars(select(Bid).where(Bid.status.in_(("Open", "Allocated", "Confirmed")))).all():
        outcome = refresh_bid(db, bid, today)
        if outcome:
            summary[outcome] += 1
    db.flush()
    if send_reminders:
        summary["reminders"] = send_due_reminders(db, today)
    db.commit()
    flush_outbox()
    return summary


def send_due_reminders(db: Session, today: date) -> int:
    """Daily from 3 days before closing until closing day, to the allocated vendor only, never after submission."""
    sent = 0
    held = db.scalars(select(Bid).where(Bid.status.in_(("Allocated", "Confirmed")), Bid.is_self.is_(False), Bid.vendor_id.isnot(None))).all()
    for bid in held:
        days = (bid.end_date - today).days
        if days < 0 or days > 3:
            continue
        if db.scalar(select(BidReminder.id).where(BidReminder.bid_id == bid.id, BidReminder.sent_on == today)):
            continue
        vendor = db.get(Vendor, bid.vendor_id)
        when = "TODAY" if days == 0 else f"in {days} day{'s' if days > 1 else ''}"
        ok = _mail_vendor(
            vendor,
            f"Reminder: bid {bid.bid_number} closes on {fmt_date(bid.end_date)}" + (" (TODAY)" if days == 0 else ""),
            [f"This is a reminder that bid {bid.bid_number} closes on {fmt_date(bid.end_date)} ({when})."]
            + _bid_lines(bid)[1:2]
            + ([f"Please confirm bidding in the CRM by {fmt_date(bid.confirm_by)}."] if bid.status == "Allocated" else [])
            + [f"Submit on the portal by {fmt_date(bid.submit_by)}."],
        )
        db.add(BidReminder(bid_id=bid.id, vendor_id=bid.vendor_id, sent_on=today, sent_to=(vendor.email if vendor else None), ok=ok))
        add_event(
            db, bid, None, "reminder",
            f"Reminder emailed to {vendor.name_of_firm if vendor else 'the vendor'} (closes {when})" if ok else
            f"Reminder could not be emailed to {vendor.name_of_firm if vendor else 'the vendor'} (no valid email or mail is off)",
            vendor_id=bid.vendor_id,
        )
        sent += 1
    return sent


# --------------------------------------------------------------------------- background runner

_started = False


def _loop() -> None:
    time.sleep(45)
    from app.database import SessionLocal

    while True:
        try:
            discard_outbox()
            with SessionLocal() as db:
                reminders_due = settings.bid_reminders_enabled and now_ist_hour() >= settings.bid_reminder_hour_ist
                result = run_rules(db, send_reminders=reminders_due)
                if any(result.values()):
                    logger.warning("bid rules ran: %s", result)
        except Exception:
            logger.exception("bid rules runner failed (will retry)")
        time.sleep(600)


def start_bid_runner() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, name="bid-rules", daemon=True).start()
