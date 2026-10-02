"""Snapshot PRIMATEL vendors, user, and order counts on production."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

REMOTE = '''
import os
from pathlib import Path
from sqlalchemy import create_engine, text

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

with engine.connect() as conn:
    print("=== vendors PRIMATEL ===")
    for r in conn.execute(text("""
        SELECT id, vendor_code, name_of_firm, email, updated_at
        FROM vendors WHERE LOWER(name_of_firm) LIKE '%primatel%' ORDER BY id
    """)).mappings():
        oid = conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id = :id AND deleted_at IS NULL"
        ), {"id": r["id"]}).scalar()
        print(dict(r), "active_orders", oid)

    print("\\n=== users PRIMATEL / ptfl ===")
    for r in conn.execute(text("""
        SELECT id, name, email, role, updated_at FROM users
        WHERE LOWER(name) LIKE '%primatel%' OR LOWER(email) LIKE '%ptfl%'
        ORDER BY id
    """)).mappings():
        print(dict(r))

    print("\\n=== email -> vendor match (vendor portal logic) ===")
    for r in conn.execute(text("""
        SELECT id, email FROM users WHERE role = 'vendor' AND deleted_at IS NULL
        AND (LOWER(name) LIKE '%primatel%' OR LOWER(email) LIKE '%ptfl%')
    """)).mappings():
        vids = conn.execute(text("""
            SELECT id, vendor_code, email FROM vendors
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(:em)) AND deleted_at IS NULL
        """), {"em": r["email"]}).mappings().all()
        oc = 0
        for v in vids:
            oc += conn.execute(text(
                "SELECT COUNT(*) FROM orders WHERE vendor_id = :vid AND deleted_at IS NULL"
            ), {"vid": v["id"]}).scalar()
        print("user", dict(r), "matched_vendors", [dict(x) for x in vids], "visible_orders", oc)
'''

def main() -> int:
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
    path = "/tmp/prod_primatel_state.py"
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
