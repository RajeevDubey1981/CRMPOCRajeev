"""Vendor-wise bid figures, worked out from the history lines of every bid.

For each vendor and each bid a step counts once, however many times it happened:
  allocated  the bid was given to the vendor
  confirmed  the vendor said yes
  submitted  the vendor put the bid in on the portal
  won, lost  the result INDcool entered
  declined   the vendor said no when asked to confirm
  expired    the vendor let the confirm-by or submit-by date pass and the bid went back
"holding" is not history: the bids the vendor has right now (allocated, confirmed or waiting for a result).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bid import Bid, BidEvent
from app.models.vendor import Vendor
from app.schemas.bid import BidStatMonth, BidStatRow, BidStatsOut

IST = timezone(timedelta(hours=5, minutes=30))
METRICS = ("allocated", "confirmed", "submitted", "won", "lost", "declined", "expired")
HOLDING_STATUSES = ("Allocated", "Confirmed", "Submitted")
_ACTIONS = ("allocated", "confirmed", "submitted", "result", "released", "auto_released")
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day(moment: datetime | None) -> date | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)  # the database keeps UTC
    return moment.astimezone(IST).date()


def _metric(event: BidEvent) -> str | None:
    action = event.action
    if action in ("allocated", "confirmed", "submitted"):
        return action
    if action == "auto_released":
        return "expired"
    text = (event.text or "").strip().lower()
    if action == "result":
        if text.startswith("result: won"):
            return "won"
        if text.startswith("result: lost"):
            return "lost"
    if action == "released" and text.startswith("released:") and " declined" in text:
        return "declined"
    return None


def _rate(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _fill_rates(row: BidStatRow) -> BidStatRow:
    row.confirm_rate = _rate(row.confirmed, row.allocated)
    row.submit_rate = _rate(row.submitted, row.confirmed)
    row.win_rate = _rate(row.won, row.won + row.lost)
    return row


def _month_starts(today: date, count: int) -> list[date]:
    year, month = today.year, today.month
    out = []
    for _ in range(count):
        out.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(out))


def vendor_stats(
    db: Session,
    *,
    vendor_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    today: date,
    months: int = 6,
) -> BidStatsOut:
    stmt = select(BidEvent).where(BidEvent.vendor_id.is_not(None), BidEvent.action.in_(_ACTIONS))
    if vendor_id is not None:
        stmt = stmt.where(BidEvent.vendor_id == vendor_id)
    events = db.scalars(stmt.order_by(BidEvent.id)).all()  # oldest first, so a step counts on the day it first happened

    starts = _month_starts(today, months)
    first_month = starts[0]
    counted: dict[tuple[int, int, str], date] = {}  # (vendor, bid, step) -> day, inside the chosen dates
    monthly: dict[str, dict[str, int]] = {f"{s.year}-{s.month:02d}": {"allocated": 0, "confirmed": 0, "submitted": 0, "won": 0} for s in starts}
    month_keys: set[tuple[int, int, str]] = set()
    for event in events:
        metric = _metric(event)
        day = _day(event.at)
        if metric is None or day is None:
            continue
        if (date_from is None or day >= date_from) and (date_to is None or day <= date_to):
            counted.setdefault((event.vendor_id, event.bid_id, metric), day)
        key = (event.vendor_id, event.bid_id, metric)
        label = f"{day.year}-{day.month:02d}"
        if day >= first_month and metric in ("allocated", "confirmed", "submitted", "won") and key not in month_keys:
            month_keys.add(key)
            if label in monthly:
                monthly[label][metric] += 1

    by_vendor: dict[int, BidStatRow] = {}

    def row_for(vid: int) -> BidStatRow:
        if vid not in by_vendor:
            by_vendor[vid] = BidStatRow(vendor_id=vid, vendor_name="")
        return by_vendor[vid]

    for (vid, _bid, metric) in counted:
        setattr(row_for(vid), metric, getattr(row_for(vid), metric) + 1)

    held = select(Bid.vendor_id, func.count(Bid.id)).where(
        Bid.vendor_id.is_not(None), Bid.is_self.is_(False), Bid.status.in_(HOLDING_STATUSES)
    )
    if vendor_id is not None:
        held = held.where(Bid.vendor_id == vendor_id)
    for vid, n in db.execute(held.group_by(Bid.vendor_id)).all():
        row_for(vid).holding = int(n)

    if vendor_id is not None:
        row_for(vendor_id)  # a vendor with no history still gets its (empty) row
    names = {v.id: v.name_of_firm for v in db.scalars(select(Vendor).where(Vendor.id.in_(list(by_vendor) or [0]))).all()}
    rows = []
    for vid, row in by_vendor.items():
        row.vendor_name = names.get(vid) or f"Vendor {vid}"
        rows.append(_fill_rates(row))
    rows.sort(key=lambda r: (-r.allocated, -r.holding, r.vendor_name.lower()))

    totals = BidStatRow(vendor_id=None, vendor_name="All vendors" if vendor_id is None else (rows[0].vendor_name if rows else ""))
    for r in rows:
        for metric in (*METRICS, "holding"):
            setattr(totals, metric, getattr(totals, metric) + getattr(r, metric))
    _fill_rates(totals)

    return BidStatsOut(
        date_from=date_from,
        date_to=date_to,
        totals=totals,
        vendors=rows,
        monthly=[
            BidStatMonth(month=key, label=f"{MONTH_NAMES[int(key[5:]) - 1]} {key[2:4]}", **values)
            for key, values in monthly.items()
        ],
    )
