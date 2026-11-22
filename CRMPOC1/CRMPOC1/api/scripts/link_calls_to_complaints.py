"""Link Sarvam call-log rows (synced from the sheet) to the complaint the agent registered during the call.

The sheet's complaint numbers are not CRM numbers, so this matches on what the CRM does know. A complaint is a
match for a call when it was registered while the call was on (from 5 minutes before the call to 60 minutes after
its end) AND either the complaint's mobile number is the caller's number, or the customer's name from the complaint
appears in the call's summary (the "reason for calling"). Only one candidate may remain, or nothing is linked.
Calls already linked to a complaint are left alone. The complaint's remark is shown beside each match so it can be
read. Dry run by default.

Usage (on the server, from the api folder):
    sudo venv/bin/python scripts/link_calls_to_complaints.py            # show matches
    sudo venv/bin/python scripts/link_calls_to_complaints.py --apply    # link them
"""
from __future__ import annotations

import os
import re
import sys
from datetime import timedelta, timezone
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


def name_in_text(name: str | None, text: str | None) -> bool:
    """Every word of the customer's name (3+ letters) appears in the text; a one-word name must be 4+ letters."""
    words = [w for w in re.findall(r"[a-z]+", (name or "").lower()) if len(w) >= 3]
    if not words or (len(words) == 1 and len(words[0]) < 4):
        return False
    low = (text or "").lower()
    return all(w in low for w in words)


def main(argv: list[str]) -> int:
    from app.database import SessionLocal
    from app.models.call import Call
    from app.models.complaint import Complaint
    from app.services.sarvam_recordings import mobile10

    apply = "--apply" in argv
    db = SessionLocal()
    stats = {"calls_checked": 0, "linked_phone_and_time": 0, "linked_name_and_time": 0, "ambiguous": 0, "no_candidate": 0}
    shown: list[str] = []
    try:
        calls = db.query(Call).filter(
            Call.sarvam_interaction_id.is_not(None), Call.complaint_id.is_(None)
        ).all()
        for call in calls:
            at = call.call_datetime if call.call_datetime.tzinfo else call.call_datetime.replace(tzinfo=timezone.utc)
            end = at + timedelta(seconds=call.duration_secs or 0)
            stats["calls_checked"] += 1
            window = db.query(Complaint).filter(
                Complaint.created_at >= (at - timedelta(minutes=5)).replace(tzinfo=None),
                Complaint.created_at <= (end + timedelta(minutes=60)).replace(tzinfo=None),
            ).all()
            mobile = mobile10(call.phone)
            by_phone = [c for c in window if mobile and mobile10(c.customer_mobile) == mobile]
            by_name = [c for c in window if name_in_text(c.customer_name, call.notes)]
            pool, kind = (by_phone, "phone_and_time") if by_phone else (by_name, "name_and_time")
            if not pool:
                stats["no_candidate"] += 1
                continue
            if len(pool) > 1:
                stats["ambiguous"] += 1
                continue
            comp = pool[0]
            stats["linked_" + kind] += 1
            if len(shown) < 12:
                shown.append(f"{call.ref_no} -> {comp.comp_no} ({kind}) {comp.customer_name} | remark: {(comp.remark or '-')[:60]}")
            if apply:
                call.complaint_id = comp.id
        if apply:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    print("APPLIED" if apply else "DRY RUN (nothing written)")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    for line in shown:
        print("   ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
