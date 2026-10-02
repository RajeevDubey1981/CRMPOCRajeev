"""Option B: vendor 86 email -> info@ptfl.in; soft-delete vendor 87 (production)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

APPLY = "--apply" in sys.argv
CANONICAL_VENDOR_ID = 86
DUPLICATE_VENDOR_ID = 87
TARGET_EMAIL = "info@ptfl.in"

REMOTE = f'''
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

apply = {repr(APPLY)}
canonical = {CANONICAL_VENDOR_ID}
duplicate = {DUPLICATE_VENDOR_ID}
email = {repr(TARGET_EMAIL)}
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

def snap(conn, label):
    print(f"\\n=== {{label}} ===")
    for vid in (canonical, duplicate):
        v = conn.execute(text(
            "SELECT id, vendor_code, email, is_active, deleted_at FROM vendors WHERE id = :id"
        ), {{"id": vid}}).mappings().first()
        if v:
            n = conn.execute(text(
                "SELECT COUNT(*) FROM orders WHERE vendor_id = :id AND deleted_at IS NULL"
            ), {{"id": vid}}).scalar()
            print(dict(v), "active_orders", n)
    u = conn.execute(text(
        "SELECT id, email, role FROM users WHERE id = 1123"
    )).mappings().first()
    print("user_1123", dict(u) if u else None)
    match = conn.execute(text("""
        SELECT id, vendor_code, email FROM vendors
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(:em)) AND deleted_at IS NULL AND is_active = 1
    """), {{"em": email}}).mappings().all()
    print("active_vendors_with_login_email", [dict(m) for m in match])
    visible = 0
    for m in match:
        visible += conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id = :id AND deleted_at IS NULL"
        ), {{"id": m["id"]}}).scalar()
    print("portal_visible_orders_sum", visible)

with engine.connect() as conn:
    snap(conn, "BEFORE")

if not apply:
    print("\\nDRY_RUN — pass --apply to execute")
    sys.exit(0)

now = datetime.now(timezone.utc)
with engine.begin() as conn:
    dup_orders = conn.execute(text(
        "SELECT COUNT(*) FROM orders WHERE vendor_id = :id"
    ), {{"id": duplicate}}).scalar()
    if dup_orders:
        raise SystemExit(f"Refusing: duplicate vendor {{duplicate}} still has {{dup_orders}} order(s)")

    conn.execute(text("""
        UPDATE vendors SET is_active = 0, deleted_at = :now, email = NULL
        WHERE id = :id AND deleted_at IS NULL
    """), {{"id": duplicate, "now": now}})

    conn.execute(text("""
        UPDATE vendors SET email = :email, is_active = 1, deleted_at = NULL
        WHERE id = :id
    """), {{"id": canonical, "email": email}})

with engine.connect() as conn:
    snap(conn, "AFTER")
    print("\\nDONE")
'''


def main() -> int:
    print(f"prod_fix_primatel_option_b {'APPLY' if APPLY else 'DRY_RUN'}")
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
    path = "/tmp/prod_fix_primatel_option_b.py"
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
