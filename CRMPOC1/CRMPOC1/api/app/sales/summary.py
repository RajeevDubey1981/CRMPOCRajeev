"""The numbers for the Sales dashboard and for the Sales block on the main CRM dashboard. A person gets only the
scope their ticks allow: the whole company, the team, or their own leads."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.sales.access import Ctx
from app.sales.leads import aware, now
from app.sales.models import SalesLead, SalesQuotation
from app.sales import types as T
from app.sales.rules import CLOSED_STATUSES


def scope_of(ctx: Ctx) -> str | None:
    if ctx.has("co_dash"):
        return "company"
    if ctx.has("team_dash"):
        return "team"
    if ctx.has("my_dash"):
        return "mine"
    return None


def _month_start() -> datetime:
    t = date.today().replace(day=1)
    return datetime.combine(t, time.min, tzinfo=timezone.utc)


def _day(d) -> date | None:
    if d is None:
        return None
    return aware(d).date() if isinstance(d, datetime) else d


def _trend(days: list, start: date, cumulative: bool = False) -> list[int]:
    """Seven numbers, one per day from `start`: how many of these dates fall on that day (or up to that day)."""
    out = []
    for i in range(7):
        day = start + timedelta(days=i)
        out.append(len([d for d in days if d and ((start <= d <= day) if cumulative else d == day)]))
    return out


def summary(sdb: Session, ctx: Ctx, names: dict[int, str] | None = None) -> dict | None:
    scope = scope_of(ctx)
    if scope is None:
        return None
    mine = scope == "mine"
    leads = list(sdb.scalars(select(SalesLead)))
    if mine:
        leads = [l for l in leads if l.owner_user_id == ctx.user.id]
    open_ = [l for l in leads if l.status not in CLOSED_STATUSES]
    today = date.today()
    month = _month_start()
    won_month = [l for l in leads if l.status == "won" and l.closed_at and aware(l.closed_at) >= month]
    won_value = sum(float(l.value_lakh or 0) for l in won_month)
    now_ = now()
    first_overdue = [l for l in open_ if l.status == "new" and l.first_call_due_at and aware(l.first_call_due_at) < now_]
    quotes = list(sdb.scalars(select(SalesQuotation).where(SalesQuotation.status.in_(("wait", "wadm")))))
    if mine:
        quotes = [q for q in quotes if q.created_by == ctx.user.id]
    wadm = [q for q in quotes if q.status == "wadm"]
    rev = [l for l in leads if l.status == "rev"]
    hot = [l for l in open_ if l.heat == "hot"]
    urgent = [l for l in open_ if l.priority in ("urgent", "high")]
    overdue = [l for l in open_ if l.follow_up_on and l.follow_up_on < today]
    due_today = [l for l in open_ if l.follow_up_on == today]
    unassigned = [l for l in open_ if l.owner_user_id is None]
    new_today = [l for l in leads if l.created_at and aware(l.created_at).date() == today]
    exp_open = [l for l in open_ if l.lead_type == "export"]

    tiles = {
        "company": [
            ("new_today", "New leads today", len(new_today), f"{len([l for l in new_today if l.owner_user_id is None])} not given to anyone yet"),
            ("hot", "Hot leads open", len(hot), ""),
            ("urgent", "Urgent and high priority", len(urgent), f"₹{sum(float(l.value_lakh or 0) for l in urgent):.1f} lakh at stake"),
            ("quotes", "Quotations waiting", len(quotes), f"{len(wadm)} need Admin: high discount"),
            ("won", "Won this month", len(won_month), f"₹{won_value:.1f} lakh"),
            ("first_overdue", "First calls overdue", len(first_overdue), "over 2 hours"),
        ],
        "team": [
            ("unassigned", "New, not given to anyone", len(unassigned), "give them now"),
            ("hot", "Hot leads open", len(hot), ""),
            ("overdue", "Overdue follow-ups", len(overdue), ""),
            ("quotes", "Quotations to approve", len([q for q in quotes if q.status == "wait"]), "your approval"),
            ("disposals", "Disposals to approve", len(rev), "your approval"),
            ("won", "Won this month", len(won_month), f"₹{won_value:.1f} lakh"),
        ],
        "mine": [
            ("open", "My open leads", len(open_), ""),
            ("due_today", "Follow-ups due today", len(due_today), ""),
            ("overdue", "Overdue", len(overdue), "call first"),
            ("hot", "Hot leads", len(hot), ""),
            ("quotes", "Quotation with the approver", len(quotes), "waiting"),
            ("won", "Won this month", len(won_month), f"₹{won_value:.1f} lakh"),
        ],
    }[scope]

    need: list[str] = []
    if scope == "company":
        if wadm:
            need.append(f"{len(wadm)} quotation{'s' if len(wadm) > 1 else ''} with a high discount wait{'s' if len(wadm) == 1 else ''} for you")
        if rev:
            need.append(f"{len(rev)} disposal{'s' if len(rev) > 1 else ''} waiting for the manager")
        for l in [x for x in hot if x.first_called_at is None][:2]:
            need.append(f"{l.name} ({T.label_of(sdb, l.lead_type)}) is Hot and has no call yet")
    elif scope == "team":
        q_wait = len([q for q in quotes if q.status == "wait"])
        if q_wait:
            need.append(f"{q_wait} quotation{'s' if q_wait > 1 else ''} waiting for you")
        if unassigned:
            need.append(f"{len(unassigned)} new lead{'s' if len(unassigned) > 1 else ''} not given to anyone")
        if rev:
            need.append(f"{len(rev)} disposal{'s' if len(rev) > 1 else ''} to approve")
        if overdue:
            need.append(f"{len(overdue)} overdue follow-up{'s' if len(overdue) > 1 else ''} across the team")
    else:
        for l in sorted([x for x in open_ if x.follow_up_on == today or x.status == "new"], key=lambda x: x.id)[:3]:
            need.append(f"{l.name}: " + ("first call due" if l.status == "new" else "follow-up today"))

    first = today - timedelta(days=6)
    created = lambda rows: [_day(getattr(r, "created_at", None)) for r in rows]
    follow = lambda rows: [r.follow_up_on for r in rows]
    window = today - timedelta(days=3)
    trends = {
        "open": _trend(created(open_), first), "new_today": _trend(created(leads), first), "hot": _trend(created(hot), first),
        "urgent": _trend(created(urgent), first), "unassigned": _trend(created(unassigned), first), "quotes": _trend(created(quotes), first),
        "disposals": _trend(created(rev), first), "first_overdue": _trend(created(first_overdue), first),
        "overdue": _trend(follow(overdue), first),
        "due_today": _trend(follow([l for l in open_ if l.follow_up_on]), window),
        "won": _trend([_day(l.closed_at) for l in won_month], first, cumulative=True),
    }
    # the month target: the target set on the profile of each sales person in this scope
    from app.sales.models import SalesProfile
    profiles = list(sdb.scalars(select(SalesProfile).where(SalesProfile.is_active.is_(True))))
    if mine:
        profiles = [p for p in profiles if p.crm_user_id == ctx.user.id]
    target_lakh = sum(float(p.target_lakh or 0) for p in profiles if (p.role_cache or "").strip().lower() == "sales" or mine)
    nxt = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    target = {"won_lakh": round(won_value, 1), "target_lakh": round(target_lakh, 1), "days_left": (nxt - today).days} if target_lakh > 0 else None

    out = {
        "scope": scope,
        "target": target,
        "title": {"company": "Sales: the whole company", "team": "Sales: my team", "mine": "Sales: my day"}[scope],
        "tiles": [{"key": k, "label": lb, "value": v, "sub": sub, "trend": trends.get(k, [])} for k, lb, v, sub in tiles],
        "need": need,
        "open_leads": len(open_),
        "export_open": len(exp_open) if scope != "mine" else None,
    }
    if scope != "mine":
        by_type: dict[str, dict] = {}
        for l in leads:
            row = by_type.setdefault(l.lead_type, {"type": l.lead_type, "label": T.label_of(sdb, l.lead_type), "color": T.color_of(sdb, l.lead_type), "leads": 0, "won": 0})
            row["leads"] += 1
            row["won"] += 1 if l.status == "won" else 0
        by_source: dict[str, dict] = {}
        for l in leads:
            row = by_source.setdefault(l.source, {"source": l.source, "leads": 0, "won": 0})
            row["leads"] += 1
            row["won"] += 1 if l.status == "won" else 0
        board: dict[int, dict] = {}
        for l in leads:
            if not l.owner_user_id:
                continue
            row = board.setdefault(l.owner_user_id, {"user_id": l.owner_user_id, "name": (names or {}).get(l.owner_user_id, str(l.owner_user_id)), "given": 0, "contacted": 0, "won": 0, "won_lakh": 0.0, "overdue": 0})
            row["given"] += 1
            row["contacted"] += 1 if l.first_called_at else 0
            row["won"] += 1 if l.status == "won" else 0
            row["won_lakh"] += float(l.value_lakh or 0) if l.status == "won" else 0
            row["overdue"] += 1 if (l.follow_up_on and l.follow_up_on < today and l.status not in CLOSED_STATUSES) else 0
        out["by_type"] = sorted(by_type.values(), key=lambda r: -r["leads"])
        out["by_source"] = sorted(by_source.values(), key=lambda r: -r["leads"])
        out["leaderboard"] = sorted(board.values(), key=lambda r: (-r["won_lakh"], -r["won"]))
        out["by_heat"] = {h: len([l for l in open_ if l.heat == h]) for h in ("hot", "warm", "cold")}
    return out
