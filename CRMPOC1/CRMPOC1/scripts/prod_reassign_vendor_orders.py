"""Reassign orders from one vendor_id to another on production.

Usage:
  py prod_reassign_vendor_orders.py              # dry-run (counts only)
  py prod_reassign_vendor_orders.py --apply      # run UPDATE in a transaction
"""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

FROM_ID = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "--apply" else 12
TO_ID = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "--apply" else 86
APPLY = "--apply" in sys.argv

if "--apply" in sys.argv:
    # py script.py --apply  OR  py script.py 12 86 --apply
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if len(args) >= 2:
        FROM_ID, TO_ID = int(args[0]), int(args[1])
    elif len(args) == 1 and args[0].isdigit():
        FROM_ID = int(args[0])

REMOTE = f'''
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

apply = {repr(APPLY)}
from_id = {FROM_ID}
to_id = {TO_ID}
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

checks = [
    ("orders", "vendor_id"),
    ("service_requests", "assigned_vendor_id"),
    ("service_assignments", "assignee_vendor_id"),
    ("service_completions", "performed_by_vendor_id"),
    ("service_payment_requests", "requested_by_vendor_id"),
    ("service_notifications", "recipient_vendor_id"),
    ("user_pending_actions", "recipient_vendor_id"),
]

with engine.connect() as conn:
    for vid in (from_id, to_id):
        v = conn.execute(text(
            "SELECT id, vendor_code, name_of_firm, email, deleted_at FROM vendors WHERE id = :id"
        ), {{"id": vid}}).mappings().first()
        print(f"vendor_{{vid}}", dict(v) if v else "NOT_FOUND")

    print("\\n=== REFERENCE COUNTS (from_id=%d) ===" % from_id)
    for table, col in checks:
        try:
            n = conn.execute(text(
                f"SELECT COUNT(*) FROM {{table}} WHERE {{col}} = :id"
            ), {{"id": from_id}}).scalar()
            print(f"{{table}}.{{col}}", n)
        except Exception as e:
            print(f"{{table}}.{{col}}", "SKIP", str(e)[:80])

    print("\\n=== TARGET orders count before ===")
    print("orders_vendor", to_id, conn.execute(text(
        "SELECT COUNT(*) FROM orders WHERE vendor_id = :id"
    ), {{"id": to_id}}).scalar())

    if not apply:
        print("\\nDRY_RUN: no changes (pass --apply on local script to update)")
        sys.exit(0)

with engine.begin() as conn:
    result = conn.execute(text(
        "UPDATE orders SET vendor_id = :to_id WHERE vendor_id = :from_id"
    ), {{"to_id": to_id, "from_id": from_id}})
    print("\\nUPDATED orders rows:", result.rowcount)

with engine.connect() as conn:
    print("\\n=== AFTER ===")
    print("orders still on from_id", conn.execute(text(
        "SELECT COUNT(*) FROM orders WHERE vendor_id = :id"
    ), {{"id": from_id}}).scalar())
    print("orders on to_id", conn.execute(text(
        "SELECT COUNT(*) FROM orders WHERE vendor_id = :id AND deleted_at IS NULL"
    ), {{"id": to_id}}).scalar())
    print("DONE")
'''


def main() -> int:
    mode = "APPLY" if APPLY else "DRY_RUN"
    print(f"prod_reassign_vendor_orders {mode}: vendor_id {FROM_ID} -> {TO_ID}")
    config = load_config()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        config["INDCOOL_DEPLOY_HOST"],
        username=config["INDCOOL_DEPLOY_USER"],
        password=config["INDCOOL_DEPLOY_PASSWORD"],
        timeout=60,
    )
    sftp = client.open_sftp()
    path = "/tmp/prod_reassign_vendor_orders.py"
    with sftp.open(path, "w") as f:
        f.write(REMOTE)
    sftp.close()
    print(ssh_run(
        client,
        f"sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {path}",
    ))
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
