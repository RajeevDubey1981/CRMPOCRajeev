"""One-time tag, in two passes:

Pass 1 -- market was only ever set on NEW orders going forward, so most old orders have market=NULL
even when the order number makes the market obvious. Any order number containing "GEMC-" (the GeM
contract-number pattern) is an unambiguous GeM order, so those get market="gem" filled in first.

Pass 2 -- csd_tier. A GeM order is, by definition, sold through the Government e-Marketplace to a
government buyer, so every market="gem" order is tagged "govt" directly -- no keyword guessing
needed. CSD orders still need their customer name scanned for depot/URC/canteen wording, since CSD
genuinely mixes two kinds of recipient (retailers and end customers). Every other market is never
touched, and nothing already tagged (by this script or by hand) is ever overwritten.

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

# Keyword rule for CSD -- same shape as the "Order Tag Scanner" preview. Edit this list, not the logic.
CSD_RETAILER_KEYWORDS = ["depot", "canteen", "urc", "unit run", "csd store", "csd canteen"]

db = SessionLocal()

# --- Pass 1: market, from the GeM contract-number pattern in order_no, for orders left unclassified ---
unmarketed = (
    db.query(Order)
    .filter(Order.market.is_(None))
    .filter(Order.order_no.isnot(None))
    .filter(Order.order_no.ilike("%GEMC-%"))
    .filter(Order.deleted_at.is_(None))
    .order_by(Order.id)
    .all()
)
market_tagged = 0
for order in unmarketed:
    print(f"Order #{order.id} ({order.order_no}): market set to gem")
    if not DRY_RUN:
        order.market = "gem"
    market_tagged += 1

db.flush()  # so pass 2's query below sees pass 1's market="gem" updates in this same run

# --- Pass 2: csd_tier. Every gem order is a government buyer by definition; CSD still needs scanning. ---
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
    if order.market == "gem":
        tier = "govt"
    else:
        name = (order.customer_name or "").lower()
        tier = "retailer" if any(k in name for k in CSD_RETAILER_KEYWORDS) else None

    if tier is None:
        left_unset += 1
        continue

    print(f"Order #{order.id} ({order.order_no or 'no number'}) {order.customer_name!r}: tagged {tier}")
    if not DRY_RUN:
        order.csd_tier = tier
    tagged += 1

if DRY_RUN:
    print(f"\nDry run. Would set market on {market_tagged} order(s) from their order number.")
    print(f"Would tag {tagged} order(s) with a tier; {left_unset} would stay Unset for manual tagging.")
else:
    db.commit()
    print(f"\nDone. Market set on {market_tagged} order(s) from their order number.")
    print(f"{tagged} order(s) tagged with a tier. {left_unset} left Unset -- filter Orders by market + tier 'Unset' to find and tag them by hand.")

db.close()
