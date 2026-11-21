"""One-time: link past Sarvam voice-agent calls to their CRM call-log rows so the recording can be played.

Reads Sarvam's call history for the last N days and, for each call, finds the CRM call-log row the agent made
while that call was on (same phone number and time; failing that, the only Sarvam call in that time window).
It only records the link: the audio is downloaded the first time someone presses Play. Safe to run again --
calls already linked are skipped, and nothing but the link (and a missing duration) is changed.

Usage (on the server, from the api folder):
    sudo venv/bin/python scripts/backfill_sarvam_recordings.py --dry-run   # show what would be linked
    sudo venv/bin/python scripts/backfill_sarvam_recordings.py             # link them
    sudo venv/bin/python scripts/backfill_sarvam_recordings.py --days 120  # look further back (default 90)
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


def main(argv: list[str]) -> int:
    from app.database import SessionLocal
    from app.models.call import Call
    from app.services.sarvam_recordings import link_interactions, list_interactions

    dry_run = "--dry-run" in argv
    days = 90
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])

    try:
        items = list_interactions(days)
    except RuntimeError as exc:
        print(f"Nothing was changed: {exc}")
        return 1
    inbound = [i for i in items if (i.get("channel_direction") or "inbound") == "inbound"]
    print(f"Sarvam call history, last {days} days: {len(items)} call(s), {len(inbound)} inbound.")

    db = SessionLocal()
    try:
        stats = link_interactions(db, inbound, dry_run=dry_run)
        for ref, iid in stats["pairs"]:
            print(f"  {ref}  <-  {iid}")
        left = db.query(Call).filter(Call.notes.like("Sarvam voice agent call%"), Call.sarvam_interaction_id.is_(None)).count()
        if dry_run:
            db.rollback()
        else:
            db.commit()
            left = db.query(Call).filter(Call.notes.like("Sarvam voice agent call%"), Call.sarvam_interaction_id.is_(None)).count()
    finally:
        db.close()

    if stats["time_only"]:
        print(f"
{len(stats['time_only'])} of these matched on time alone (the caller gave the agent a different number than they rang from) -- worth a spot check:")
        for ref, iid in stats["time_only"]:
            print(f"  {ref}  <-  {iid}")
    verb = "Would link" if dry_run else "Linked"
    print(f"\n{verb} {stats['matched']} call(s). {stats['already_linked']} were already linked. "
          f"{stats['no_crm_call']} Sarvam call(s) had no CRM call-log row (the caller did not register anything).")
    print(f"Sarvam call-log rows in the CRM still without a recording link: {left}"
          + (" (after this run)" if not dry_run else " (before this run)"))
    if dry_run:
        print("Dry run: nothing was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
