"""One way to filter a list by the day a record was registered. Days are Indian days; stored times are UTC."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def utc_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """The first moment of date_from and the first moment after date_to, as UTC times with no zone (how the database keeps them)."""
    start = end = None
    if date_from:
        start = datetime.combine(date_from, time.min, IST).astimezone(timezone.utc).replace(tzinfo=None)
    if date_to:
        end = datetime.combine(date_to + timedelta(days=1), time.min, IST).astimezone(timezone.utc).replace(tzinfo=None)
    return start, end


def registered_between(stmt, column, date_from: date | None, date_to: date | None):
    """Add the date conditions to a select on a created_at style column."""
    start, end = utc_bounds(date_from, date_to)
    if start is not None:
        stmt = stmt.where(column >= start)
    if end is not None:
        stmt = stmt.where(column < end)
    return stmt


def day_in_range(moment: datetime | None, date_from: date | None, date_to: date | None) -> bool:
    """The same test for a list that is filtered in Python: is the Indian day of this time inside the range?"""
    if moment is None:
        return not (date_from or date_to)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    day = moment.astimezone(IST).date()
    return (not date_from or day >= date_from) and (not date_to or day <= date_to)
