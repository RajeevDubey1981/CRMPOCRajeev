"""Read-only: prints a Sales lead's current state and recent activity, by name (partial match).
Nothing is changed. Usage:
    venv/bin/python scripts/inspect_lead.py "S M Enterprise"
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

name = sys.argv[1] if len(sys.argv) > 1 else None
if not name:
    print('Usage: python scripts/inspect_lead.py "S M Enterprise"')
    raise SystemExit(1)

from app.database import SessionLocal
from app.models.user import User
from app.sales.db import new_sales_session, sales_enabled
from app.sales.models import SalesLead, SalesLeadActivity

if not sales_enabled():
    print("Sales database not configured.")
    raise SystemExit(1)

sdb = new_sales_session()
main_db = SessionLocal()

leads = sdb.query(SalesLead).filter(SalesLead.name.ilike(f"%{name}%")).order_by(SalesLead.id.desc()).all()
if not leads:
    print(f"No lead found matching {name!r}.")
    raise SystemExit(0)

for lead in leads:
    owner = main_db.get(User, lead.owner_user_id) if lead.owner_user_id else None
    print(f"\nLead #{lead.id}: {lead.name!r}  phone={lead.phone!r}  lead_type={lead.lead_type!r}  status={lead.status!r}")
    print(f"  heat={lead.heat!r}  heat_why={lead.heat_why!r}")
    print(f"  owner={owner.name if owner else 'none'} (user_id={lead.owner_user_id})")
    print(f"  last_action_at={lead.last_action_at}")
    acts = sdb.query(SalesLeadActivity).filter(SalesLeadActivity.lead_id == lead.id).order_by(SalesLeadActivity.id.desc()).limit(3).all()
    if not acts:
        print("  (no activity logged)")
    for a in acts:
        print(f"  [{a.at}] ({a.kind}) by {a.by_name}: {a.text[:200]}")

sdb.close()
main_db.close()
