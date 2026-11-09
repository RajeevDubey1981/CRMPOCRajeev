"""One-time flip: GeM's buyer tier default changes from "customer" to "vendor" -- the vendor who
punches a GeM order is, by definition, our own registered GeM reseller (that's what market="gem"
on their own profile already means), so that's the tier every GeM order gets by default. "customer"
stays available for the rare direct-to-government order with no reseller involved, tagged by hand.

This renames every Order currently tagged csd_tier="customer" (market="gem") back to "vendor".
Covers Order (main DB) only -- SalesLead/MkAudience never had any "customer"-tagged rows yet.

Usage:
    venv/bin/python scripts/rename_customer_tier_to_vendor.py          # apply
    venv/bin/python scripts/rename_customer_tier_to_vendor.py --dry-run
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

from app.database import SessionLocal
from app.models.order import Order

db = SessionLocal()
orders = db.query(Order).filter(Order.market == "gem", Order.csd_tier == "customer").all()
print(f"Order: {len(orders)} GeM row(s) tagged 'customer' -> 'vendor'")
if not DRY_RUN:
    for o in orders:
        o.csd_tier = "vendor"
    db.commit()
    print("Done.")
else:
    print("Dry run, nothing changed.")
db.close()
