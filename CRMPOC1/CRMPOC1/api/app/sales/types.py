"""The list of lead types, kept in the Sales database so that Admin can add and rename them."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.sales.models import SalesLeadType
from app.sales.rules import LEAD_TYPES

BUILTIN_COLORS = {
    "gem": "#1d4ed8", "csd": "#0e7490", "retail": "#047857", "spare": "#b45309", "dealer": "#7c3aed",
    "tender": "#be185d", "corp": "#475569", "export": "#0369a1",
}


def ensure_types(sdb: Session) -> None:
    """Puts the eight built-in types in place the first time (and after a type was never added)."""
    have = {t.key for t in sdb.scalars(select(SalesLeadType))}
    added = False
    for order, (key, label) in enumerate(LEAD_TYPES.items(), start=1):
        if key not in have:
            sdb.add(SalesLeadType(key=key, label=label, color=BUILTIN_COLORS.get(key, "#475569"), sort_order=order * 10, is_active=True, is_builtin=True))
            added = True
    if added:
        sdb.flush()
        sdb.info.pop("types_cache", None)


def type_map(sdb: Session) -> dict[str, dict]:
    """key -> {label, color, active, builtin}, read once per session."""
    cached = sdb.info.get("types_cache")
    if cached is not None:
        return cached
    ensure_types(sdb)
    rows = list(sdb.scalars(select(SalesLeadType).order_by(SalesLeadType.sort_order, SalesLeadType.label)))
    out = {r.key: {"key": r.key, "label": r.label, "color": r.color, "active": r.is_active, "builtin": r.is_builtin, "sort_order": r.sort_order} for r in rows}
    sdb.info["types_cache"] = out
    return out


def active_types(sdb: Session) -> list[dict]:
    return [t for t in type_map(sdb).values() if t["active"]]


def valid_type(sdb: Session, key: str | None, *, active_only: bool = True) -> bool:
    t = type_map(sdb).get(key or "")
    return bool(t and (t["active"] or not active_only))


def label_of(sdb: Session, key: str) -> str:
    t = type_map(sdb).get(key)
    return t["label"] if t else LEAD_TYPES.get(key, key)


def color_of(sdb: Session, key: str) -> str:
    t = type_map(sdb).get(key)
    return t["color"] if t else "#64748b"


def usable_type(sdb: Session, key: str | None) -> str:
    """The type to use: the one asked for if it is switched on, else Retail, else the first one that is on."""
    if valid_type(sdb, key):
        return key
    if valid_type(sdb, "retail"):
        return "retail"
    act = active_types(sdb)
    return act[0]["key"] if act else "retail"


def make_key(sdb: Session, label: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")[:24] or "type"
    key, n = base, 2
    while key in type_map(sdb):
        key = f"{base}_{n}"
        n += 1
    return key


def clean_color(color: str | None) -> str:
    c = (color or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The colour is written like #1d4ed8")
    return c.lower()
