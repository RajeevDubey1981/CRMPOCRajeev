"""List order counts grouped by vendor_id for vendors matching a firm name (production)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

NAME_PATTERN = sys.argv[1] if len(sys.argv) > 1 else "PRIMATEL FIBCOM LIMITED"

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

pattern = {repr(NAME_PATTERN)}
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

with engine.connect() as conn:
    print("=== VENDORS matching name (LIKE %pattern%) ===")
    vendors = conn.execute(text("""
        SELECT id, vendor_code, name_of_firm, email, is_active, deleted_at
        FROM vendors
        WHERE LOWER(name_of_firm) LIKE LOWER(:pat)
        ORDER BY id
    """), {{"pat": f"%{{pattern}}%"}}).mappings().all()
    for v in vendors:
        print(dict(v))
    if not vendors:
        print("(no vendor rows)")

    print("\\n=== ORDERS by vendor_id (join vendors.name_of_firm LIKE pattern) ===")
    rows = conn.execute(text("""
        SELECT o.vendor_id,
               v.vendor_code,
               v.name_of_firm,
               v.email AS vendor_email,
               COUNT(*) AS order_cnt,
               SUM(CASE WHEN o.deleted_at IS NULL THEN 1 ELSE 0 END) AS active_cnt,
               SUM(CASE WHEN o.deleted_at IS NOT NULL THEN 1 ELSE 0 END) AS deleted_cnt
        FROM orders o
        INNER JOIN vendors v ON v.id = o.vendor_id
        WHERE LOWER(v.name_of_firm) LIKE LOWER(:pat)
        GROUP BY o.vendor_id, v.vendor_code, v.name_of_firm, v.email
        ORDER BY order_cnt DESC
    """), {{"pat": f"%{{pattern}}%"}}).mappings().all()
    for r in rows:
        print(dict(r))
    if not rows:
        print("(no orders linked via vendor_id to matching vendor names)")

    print("\\n=== ORDERS with NULL vendor_id but customer_name LIKE pattern? ===")
    null_v = conn.execute(text("""
        SELECT COUNT(*) FROM orders
        WHERE vendor_id IS NULL AND deleted_at IS NULL
          AND LOWER(COALESCE(customer_name,'')) LIKE LOWER(:pat)
    """), {{"pat": f"%{{pattern}}%"}}).scalar()
    print("null_vendor_customer_name_match", null_v)

    print("\\n=== Sample orders (up to 5 per vendor_id) ===")
    for v in vendors:
        vid = v["id"]
        samples = conn.execute(text("""
            SELECT o.id, o.order_no, o.status, o.vendor_id, o.customer_name, o.deleted_at
            FROM orders o
            WHERE o.vendor_id = :vid
            ORDER BY o.id DESC LIMIT 5
        """), {{"vid": vid}}).mappings().all()
        print(f"-- vendor_id={{vid}} sample count={{len(samples)}} --")
        for s in samples:
            print(dict(s))
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
    path = "/tmp/prod_orders_by_vendor_name.py"
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
