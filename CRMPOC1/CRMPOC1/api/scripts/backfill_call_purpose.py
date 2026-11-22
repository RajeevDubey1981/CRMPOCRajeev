"""One-time: give every call that has no purpose a best-guess one from its notes.

A call whose notes say "Sarvam voice agent call (Sales)" or "(Service)" or "(Installation)" takes that; the rest are
read for key words (see app/services/call_purpose.py). Calls that already have a purpose are not touched. The guess
can be changed on the call afterwards. Dry run by default.

    sudo venv/bin/python scripts/backfill_call_purpose.py            # counts only
    sudo venv/bin/python scripts/backfill_call_purpose.py --apply
"""
from __future__ import annotations

import collections
import os
import re
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

BY_TYPE = {"sales": "Sales enquiry", "installation": "Installation request", "service": "Service complaint"}


def main(argv: list[str]) -> int:
    from app.database import SessionLocal
    from app.models.call import Call
    from app.services.call_purpose import infer_purpose

    apply = "--apply" in argv
    db = SessionLocal()
    counts: collections.Counter = collections.Counter()
    try:
        for call in db.query(Call).filter(Call.purpose.is_(None)).all():
            m = re.match(r"Sarvam voice agent call \((\w+)\)", call.notes or "")
            purpose = BY_TYPE.get(m.group(1).lower()) if m else None
            purpose = purpose or infer_purpose(call.notes)
            counts[purpose] += 1
            if apply:
                call.purpose = purpose
        if apply:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    print("APPLIED" if apply else "DRY RUN (nothing written)")
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
