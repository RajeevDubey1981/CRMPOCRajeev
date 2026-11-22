"""Sync the Sarvam call export (a CSV of the Google Sheet) into the CRM call log.

For every row it finds the CRM call (same Sarvam Attempt ID first; failing that the same phone number at the
same time) and stores the Google Drive recording link on it. A row with no CRM call gets a new Inbound call-log
row. A complaint number in the sheet is linked when it matches a CRM complaint. No audio is copied: only the
Drive link is kept. Safe to run again: rows already synced are skipped.

Times: the sheet's "Date & Time (IST)" column runs 5 hours 30 minutes behind UTC (it is not real IST). Each
time is checked against the time inside the Attempt ID, which is UTC, and the ID's time is used when they differ.

Usage (on the server, from the api folder):
    sudo venv/bin/python scripts/sync_sarvam_sheet.py export.csv            # dry run: counts and examples
    sudo venv/bin/python scripts/sync_sarvam_sheet.py export.csv --apply    # write the changes
    add --skip-short=15 to leave out calls under 15 seconds that have no reason for calling
"""
from __future__ import annotations

import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
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

SHEET_OFFSET = timedelta(hours=5, minutes=30)


def parse_row(row: list[str]) -> dict | None:
    """One sheet row as plain values, or None when it has no usable time or Attempt ID."""
    row = (row + [""] * 16)[:16]
    attempt = row[5].strip()
    if not re.fullmatch(r"\d{8}/[A-Za-z0-9_:\-]{6,100}", attempt):
        return None
    try:
        shown = datetime.strptime(row[0].strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    start = (shown + SHEET_OFFSET).replace(tzinfo=timezone.utc)
    m = re.search(r"-(\d\d):(\d\d):(\d\d)-", attempt)
    if m:
        day = datetime.strptime(attempt[:8], "%Y%m%d")
        from_id = day.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=int(m.group(3)), tzinfo=timezone.utc)
        if abs((from_id - start).total_seconds()) > 300:
            start = from_id
    try:
        parts = [int(x) for x in row[2].strip().split(":")]
        duration = 0
        for part in parts:  # m:ss or h:mm:ss
            duration = duration * 60 + part
    except ValueError:
        duration = None
    return {
        "attempt": attempt,
        "start": start,
        "duration": duration,
        "phone_raw": row[1].strip(),
        "url": row[4].strip() or None,
        "name": row[6].strip() or None,
        "email": row[9].strip() or None,
        "reason": row[11].strip(),
        "disposition": row[12].strip(),
        "escalation": row[13].strip(),
        "complaint_no": row[15].strip(),
    }


def main(argv: list[str]) -> int:
    from app.database import SessionLocal
    from app.models.call import Call
    from app.models.complaint import Complaint
    from app.routers.calls import _generate_ref_no
    from app.services.call_purpose import infer_purpose
    from app.services.sarvam_recordings import match_call, mobile10

    args = [a for a in argv if not a.startswith("--")]
    apply = "--apply" in argv
    skip_short = 0  # --skip-short=15: do not add new rows for calls under 15 seconds that have no reason for calling
    for a in argv:
        if a.startswith("--skip-short="):
            skip_short = int(a.split("=", 1)[1])
    if not args:
        print(__doc__)
        return 2
    with open(args[0], encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))[1:]

    db = SessionLocal()
    stats = {"rows": 0, "skipped_bad_row": 0, "already_synced": 0, "linked_by_id": 0, "linked_by_phone_time": 0,
             "new_calls": 0, "no_drive_link": 0, "complaint_linked": 0, "complaint_not_found": 0}
    taken: set[int] = set()

    def squash(v: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", v or "").upper()

    # The sheet writes IDC20260801081859B4C4A7 where the CRM has IDC_20260801_081859_B4C4A7: compare without punctuation.
    comp_by_key = {squash(c.comp_no): c for c in db.query(Complaint).all()}
    missing_complaints: list[str] = []
    examples: list[str] = []
    try:
        for raw in rows:
            item = parse_row(raw)
            if item is None:
                stats["skipped_bad_row"] += 1
                continue
            stats["rows"] += 1
            if not item["url"]:
                stats["no_drive_link"] += 1
            mobile = mobile10(item["phone_raw"])
            end = item["start"] + timedelta(seconds=item["duration"] or 0)

            call = db.query(Call).filter(Call.sarvam_interaction_id == item["attempt"]).first()
            how = "id"
            if call is None:
                call = match_call(db, mobile, item["start"], end, taken, allow_time_only=False)
                how = "phone_time"
            if call is not None:
                taken.add(call.id)
                if call.sarvam_interaction_id == item["attempt"] and call.recording_url == item["url"]:
                    stats["already_synced"] += 1
                else:
                    stats["linked_by_id" if how == "id" else "linked_by_phone_time"] += 1
                    if apply:
                        call.sarvam_interaction_id = item["attempt"]
                        if item["url"]:
                            call.recording_url = item["url"]
                        if call.duration_secs is None:
                            call.duration_secs = item["duration"]
            elif skip_short and (item["duration"] or 0) < skip_short and not item["reason"]:
                stats["short_not_added"] = stats.get("short_not_added", 0) + 1
            else:
                stats["new_calls"] += 1
                if len(examples) < 5:
                    examples.append(f"{item['start']:%Y-%m-%d %H:%M} UTC  {item['phone_raw']}  {item['disposition'] or '-'}")
                if apply:
                    notes = "Sarvam voice agent call (from the daily export)."
                    if item["disposition"]:
                        notes += f" Disposition: {item['disposition']}."
                    if item["reason"]:
                        notes += f" {item['reason']}"
                    if item["escalation"]:
                        notes += f" Escalation: {item['escalation']}"
                    call = Call(
                        ref_no=_generate_ref_no(db),
                        customer_name=item["name"] or "Unknown caller",
                        customer_email=item["email"],
                        phone=mobile or (item["phone_raw"] or None),
                        call_type="Inbound",
                        status="Completed",
                        priority="Medium",
                        call_datetime=item["start"],
                        duration_secs=item["duration"],
                        notes=notes[:4000],
                        purpose=infer_purpose(item["reason"], item["disposition"]),
                        sarvam_interaction_id=item["attempt"],
                        recording_url=item["url"],
                    )
                    db.add(call)
                    db.flush()
                    taken.add(call.id)

            if item["complaint_no"]:
                key = squash(item["complaint_no"])
                comp = comp_by_key.get(key) or (comp_by_key.get("IDC" + key) if key.isdigit() else None)
                if comp is None:
                    stats["complaint_not_found"] += 1
                    if item["complaint_no"] not in missing_complaints:
                        missing_complaints.append(item["complaint_no"])
                elif call is not None and call.complaint_id is None:
                    stats["complaint_linked"] += 1
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
    if examples:
        print("  examples of calls that would be added:")
        for e in examples:
            print("   ", e)
    if missing_complaints:
        print(f"  complaint numbers in the sheet with no CRM complaint ({len(missing_complaints)}): {', '.join(missing_complaints[:15])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
