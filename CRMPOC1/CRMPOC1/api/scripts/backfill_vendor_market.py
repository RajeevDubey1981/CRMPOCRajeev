"""One-time backfill: for every vendor login with exactly one market in their own profile
(vendor_types -- GeM/CSD/Retail), set market on every one of that vendor's orders to match,
including ones still unmarked and ones a previous guess (or a since-changed profile) got wrong.

This uses the exact same rule as order creation and the live "retag on profile change" hook in
app/routers/users.py -- app/services/vendor_market.py is the single place that rule lives. A
vendor with zero or more than one mapped market (SSD-only, or both GeM and CSD) is left alone,
same as at order creation, since there's nothing to pick automatically.

Safe to run again any time -- e.g. right after you update a vendor's profile tag, to catch up
orders from before this hook existed, or if you ever need to re-sweep everything at once.

Usage:
    venv/bin/python scripts/backfill_vendor_market.py          # apply
    venv/bin/python scripts/backfill_vendor_market.py --dry-run
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
os.chdir(API_DIR)
sys.path.insert(0, str(API_DIR))

_env_file = API_DIR / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _value.strip())

DRY_RUN = "--dry-run" in sys.argv[1:]

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.order import Order
from app.models.user import User
from app.models.vendor import Vendor
from app.services.csd_tier import valid_csd_tier
from app.services.vendor_market import vendor_profile_markets

db = SessionLocal()

vendors_users = db.scalars(
    select(User).where(func.lower(func.trim(User.role)) == "vendor", User.deleted_at.is_(None))
).all()

total_changed = 0
skipped_no_market = 0
skipped_multi_market = 0

for user in vendors_users:
    markets = vendor_profile_markets(user)
    if not markets:
        skipped_no_market += 1
        continue
    if len(markets) > 1:
        skipped_multi_market += 1
        continue
    market = markets[0]

    vendor_ids = db.scalars(
        select(Vendor.id).where(
            func.lower(func.trim(Vendor.email)) == (user.email or "").strip().lower(),
            Vendor.deleted_at.is_(None),
        )
    ).all()
    if not vendor_ids:
        continue

    orders = db.scalars(
        select(Order).where(Order.vendor_id.in_(vendor_ids), Order.deleted_at.is_(None))
    ).all()
    for order in orders:
        if order.market == market:
            continue
        print(f"Order #{order.id} ({order.order_no or 'no number'}): {user.name} ({user.email}) is {market} -- market {order.market!r} -> {market!r}")
        if not DRY_RUN:
            order.market = market
            if not valid_csd_tier(order.market, order.csd_tier):
                order.csd_tier = None
        total_changed += 1

if DRY_RUN:
    db.rollback()
    print(f"\nDry run. Would change {total_changed} order(s).")
else:
    db.commit()
    print(f"\nDone. {total_changed} order(s) changed.")
print(f"{skipped_no_market} vendor(s) have no mapped market on their profile, {skipped_multi_market} have more than one (left alone).")

db.close()
