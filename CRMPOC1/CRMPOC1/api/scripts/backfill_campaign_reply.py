"""One-time fix: leads that replied to a campaign link BEFORE the highlight feature existed
never got campaign_reply_at/campaign_reply_text set, so they don't show the "Replied to
campaign" badge even though the activity note is already on the lead. This scans existing
activity notes for that note's own wording and fills the highlight fields in, without
touching anything else on the lead. Safe to run more than once -- it skips a lead that
already has campaign_reply_at set.

Usage:
    venv/bin/python scripts/backfill_campaign_reply.py
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

from app.sales.db import new_sales_session, sales_enabled
from app.sales.models import SalesLead, SalesLeadActivity

if not sales_enabled():
    print("Sales database not configured.")
    raise SystemExit(1)

sdb = new_sales_session()

candidates = (
    sdb.query(SalesLeadActivity)
    .filter(SalesLeadActivity.kind == "note")
    .filter(SalesLeadActivity.text.like('Replied to the "%" campaign link.%'))
    .order_by(SalesLeadActivity.lead_id, SalesLeadActivity.id.desc())
    .all()
)

seen_leads = set()
fixed = 0
for act in candidates:
    if act.lead_id in seen_leads:
        continue  # keep only the latest matching activity per lead
    seen_leads.add(act.lead_id)

    lead = sdb.get(SalesLead, act.lead_id)
    if lead is None or lead.campaign_reply_at is not None:
        continue

    first_line, _, rest = act.text.partition("\n")
    offer_name = first_line.split('"')[1] if '"' in first_line else "campaign"
    interest_line = next((ln for ln in rest.splitlines() if ln.startswith("Interest:")), "Interest: Yes, interested")
    interest_label = interest_line.split(":", 1)[1].strip() if ":" in interest_line else "Yes, interested"

    lead.campaign_reply_at = act.at
    lead.campaign_reply_text = f"{offer_name} -- {interest_label}"[:255]
    fixed += 1
    print(f"Lead #{lead.id} {lead.name!r}: highlighted, reply at {act.at}")

sdb.commit()
sdb.close()
print(f"\nDone. {fixed} lead(s) backfilled.")
