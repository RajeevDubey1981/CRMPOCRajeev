"""Total order count by vendor name pattern on production."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

PATTERN = sys.argv[1] if len(sys.argv) > 1 else "primatel"

REMOTE = f'''
import os
from pathlib import Path
from sqlalchemy import create_engine, text

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

pat = {repr(PATTERN)}
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

with engine.connect() as conn:
    like = f"%{{pat}}%"
    total_all = conn.execute(text("""
        SELECT COUNT(*) FROM orders o
        INNER JOIN vendors v ON v.id = o.vendor_id
        WHERE LOWER(v.name_of_firm) LIKE LOWER(:like)
    """), {{"like": like}}).scalar()
    total_active = conn.execute(text("""
        SELECT COUNT(*) FROM orders o
        INNER JOIN vendors v ON v.id = o.vendor_id
        WHERE LOWER(v.name_of_firm) LIKE LOWER(:like) AND o.deleted_at IS NULL
    """), {{"like": like}}).scalar()
    print("pattern", pat)
    print("total_orders_including_deleted", total_all)
    print("total_active_orders", total_active)
    print("by_vendor_id")
    for r in conn.execute(text("""
        SELECT o.vendor_id, v.vendor_code, v.name_of_firm, COUNT(*) AS cnt,
               SUM(CASE WHEN o.deleted_at IS NULL THEN 1 ELSE 0 END) AS active
        FROM orders o
        INNER JOIN vendors v ON v.id = o.vendor_id
        WHERE LOWER(v.name_of_firm) LIKE LOWER(:like)
        GROUP BY o.vendor_id, v.vendor_code, v.name_of_firm
        ORDER BY cnt DESC
    """), {{"like": like}}).mappings():
        print(dict(r))
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
    path = "/tmp/prod_order_count_vendor_pattern.py"
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
