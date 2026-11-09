"""One-time tag: past orders in the CSD and GeM markets have no csd_tier set at all. This scans each
order's customer name for keyword matches and fills csd_tier in where the name makes it obvious --
CSD orders become "retailer" (depot/URC/canteen) or are left unset; GeM orders become "govt" (an
actual government buyer) or are left unset. Every other market is never touched. Safe to run more
than once -- it never overwrites a tier already set (by this script or by hand).

Usage:
    venv/bin/python scripts/backfill_csd_tier.py          # apply the changes
    venv/bin/python scripts/backfill_csd_tier.py --dry-run # show what would change, change nothing
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

from app.database import SessionLocal
from app.models.order import Order

DRY_RUN = "--dry-run" in sys.argv[1:]

# Keyword rules -- same shape as the "Order Tag Scanner" preview. Edit these two lists, not the logic.
CSD_RETAILER_KEYWORDS = ["depot", "canteen", "urc", "unit run", "csd store", "csd canteen"]
GEM_GOVT_KEYWORDS = ["gemc-", "gem/", "ministry", "govt", "dept of", "directorate", "cantonment board"]

db = SessionLocal()

orders = (
    db.query(Order)
    .filter(Order.market.in_(["csd", "gem"]))
    .filter(Order.csd_tier.is_(None))
    .filter(Order.deleted_at.is_(None))
    .order_by(Order.id)
    .all()
)

tagged = 0
left_unset = 0
for order in orders:
    name = (order.customer_name or "").lower()
    if order.market == "csd":
        hit = any(k in name for k in CSD_RETAILER_KEYWORDS)
        tier = "retailer" if hit else None
    else:
        hit = any(k in name for k in GEM_GOVT_KEYWORDS)
        tier = "govt" if hit else None

    if tier is None:
        left_unset += 1
        continue

    print(f"Order #{order.id} ({order.order_no or 'no number'}) {order.customer_name!r}: tagged {tier}")
    if not DRY_RUN:
        order.csd_tier = tier
    tagged += 1

if DRY_RUN:
    print(f"\nDry run. Would tag {tagged} order(s); {left_unset} would stay Unset for manual tagging.")
else:
    db.commit()
    print(f"\nDone. {tagged} order(s) tagged. {left_unset} left Unset -- filter Orders by market + tier 'Unset' to find and tag them by hand.")

db.close()
