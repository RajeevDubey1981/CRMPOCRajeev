"""One-time rename: csd_tier="govt" -> "customer", now that GeM's buyer tier is split into
"vendor" (a dealer/reseller registered to sell via GeM) and "customer" (the actual government
buyer) -- same shape as CSD's Retailer/End customer. Every order already tagged "govt" by the
earlier backfill was a real government buyer (Directorate of Purchase, Education Department,
NTPC, etc.), so they all become "customer" here; nothing becomes "vendor" automatically.

Covers Order (main DB), SalesLead (Sales DB) and MkAudience (Marketing DB).

Usage:
    venv/bin/python scripts/rename_govt_tier_to_customer.py          # apply
    venv/bin/python scripts/rename_govt_tier_to_customer.py --dry-run
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
orders = db.query(Order).filter(Order.csd_tier == "govt").all()
print(f"Order: {len(orders)} row(s) tagged 'govt'")
if not DRY_RUN:
    for o in orders:
        o.csd_tier = "customer"
    db.commit()
db.close()

from app.sales.db import new_sales_session, sales_enabled

if sales_enabled():
    from app.sales.models import SalesLead

    sdb = new_sales_session()
    leads = sdb.query(SalesLead).filter(SalesLead.csd_tier == "govt").all()
    print(f"SalesLead: {len(leads)} row(s) tagged 'govt'")
    if not DRY_RUN:
        for lead in leads:
            lead.csd_tier = "customer"
        sdb.commit()
    sdb.close()
else:
    print("SalesLead: Sales database not configured, skipped")

from app.marketing.db import marketing_enabled, new_marketing_session

if marketing_enabled():
    from app.marketing.models import MkAudience

    mdb = new_marketing_session()
    auds = mdb.query(MkAudience).filter(MkAudience.csd_tier == "govt").all()
    print(f"MkAudience: {len(auds)} row(s) tagged 'govt'")
    if not DRY_RUN:
        for a in auds:
            a.csd_tier = "customer"
        mdb.commit()
    mdb.close()
else:
    print("MkAudience: Marketing database not configured, skipped")

print("\nDry run, nothing changed." if DRY_RUN else "\nDone.")
