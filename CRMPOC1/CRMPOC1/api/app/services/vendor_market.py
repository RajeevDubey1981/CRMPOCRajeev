"""A vendor login is the only one who punches orders, so their own profile (vendor_types --
GeM/CSD/Retail/SSD, set on the vendor's User account) is the single source of truth for which
market their orders belong to -- not picked by hand, and not guessed per order.

Used in two places: new-order creation (orders.py auto-fills/validates against this), and here,
to retroactively re-tag every one of a vendor's EXISTING orders the moment their profile tag
changes (called right after a vendor-role user is edited, and by the one-time backfill script)."""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.user import User
from app.models.vendor import Vendor
from app.services.csd_tier import valid_csd_tier

# "SSD" (Sales Service Distributor) has no single market of its own -- a vendor who is only SSD
# still has their market set by hand, same as at order creation.
VENDOR_TYPE_TO_MARKET = {"gem": "gem", "csd": "csd", "retail": "retail"}


def vendor_profile_markets(user: User) -> list[str]:
    try:
        labels = [str(s) for s in json.loads(user.vendor_types)] if user.vendor_types else []
    except ValueError:
        return []
    out: list[str] = []
    for label in labels:
        key = VENDOR_TYPE_TO_MARKET.get(label.strip().lower())
        if key and key not in out:
            out.append(key)
    return out


def retag_vendor_orders(db: Session, user: User) -> int:
    """Set market on every order belonging to this vendor login to match their profile -- only
    when the profile names exactly one market (an SSD-only or multi-market vendor is left alone,
    same as order creation requires that vendor to pick by hand). Returns how many orders changed."""
    if (user.role or "").strip().lower() != "vendor":
        return 0
    markets = vendor_profile_markets(user)
    if len(markets) != 1:
        return 0
    market = markets[0]

    vendor_ids = db.scalars(
        select(Vendor.id).where(
            func.lower(func.trim(Vendor.email)) == (user.email or "").strip().lower(),
            Vendor.deleted_at.is_(None),
        )
    ).all()
    if not vendor_ids:
        return 0

    orders = db.scalars(
        select(Order).where(Order.vendor_id.in_(vendor_ids), Order.deleted_at.is_(None))
    ).all()
    changed = 0
    for order in orders:
        if order.market == market:
            continue
        order.market = market
        if not valid_csd_tier(order.market, order.csd_tier):
            order.csd_tier = None  # the old tier no longer applies to the new market
        changed += 1
    return changed
