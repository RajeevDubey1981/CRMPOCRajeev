"""Count orders and related work linked to a user id (vendor login) on production."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1123

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

uid = {USER_ID}
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])

with engine.connect() as conn:
    user = conn.execute(text(
        "SELECT id, name, email, role FROM users WHERE id = :uid"
    ), {{"uid": uid}}).mappings().first()
    print("=== USER ===", dict(user) if user else "NOT FOUND")

    vendor = None
    if user:
        vendor = conn.execute(text("""
            SELECT id, vendor_code, name_of_firm, email, is_active, deleted_at
            FROM vendors
            WHERE LOWER(email) = LOWER(:email) AND deleted_at IS NULL
            ORDER BY id DESC LIMIT 1
        """), {{"email": user["email"]}}).mappings().first()
    print("=== VENDOR (by user email) ===", dict(vendor) if vendor else "NOT FOUND")

    vid = vendor["id"] if vendor else None
    print("=== ORDER COUNTS ===")
    print("orders_vendor_id_eq_user_id", conn.execute(text(
        "SELECT COUNT(*) FROM orders WHERE vendor_id = :uid AND deleted_at IS NULL"
    ), {{"uid": uid}}).scalar())
    if vid:
        print("orders_vendor_id_eq_vendor_master_id", conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id = :vid AND deleted_at IS NULL"
        ), {{"vid": vid}}).scalar())
        print("orders_vendor_id_eq_vendor_including_deleted", conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id = :vid"
        ), {{"vid": vid}}).scalar())

    print("=== SERVICE / INSTALLATION (vendor id) ===")
    if vid:
        print("service_requests_assigned_vendor", conn.execute(text(
            "SELECT COUNT(*) FROM service_requests WHERE assigned_vendor_id = :vid AND deleted_at IS NULL"
        ), {{"vid": vid}}).scalar())
        print("service_assignments_active_vendor", conn.execute(text(
            "SELECT COUNT(*) FROM service_assignments WHERE assignee_vendor_id = :vid AND is_active = 1"
        ), {{"vid": vid}}).scalar())
    if vid:
        print("all_vendors_same_email", list(conn.execute(text(
            "SELECT id, vendor_code, name_of_firm, deleted_at FROM vendors WHERE LOWER(email) = LOWER(:em)"
        ), {{"em": user["email"]}}).mappings()))
        print("vendor_master_id_1123_exists", conn.execute(text(
            "SELECT id, vendor_code, email FROM vendors WHERE id = 1123"
        )).mappings().first())
        print("orders_vendor_id_1123_any", conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id = 1123"
        )).scalar())
        print("orders_customer_primatel", conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE deleted_at IS NULL AND LOWER(COALESCE(customer_name,'')) LIKE '%primatel%'"
        )).scalar())
        print("total_orders_in_system", conn.execute(text("SELECT COUNT(*) FROM orders WHERE deleted_at IS NULL")).scalar())
        print("orders_with_any_vendor", conn.execute(text(
            "SELECT COUNT(*) FROM orders WHERE vendor_id IS NOT NULL AND deleted_at IS NULL"
        )).scalar())
        print("vendor_id_distribution_top", list(conn.execute(text("""
            SELECT vendor_id, COUNT(*) AS cnt FROM orders WHERE deleted_at IS NULL AND vendor_id IS NOT NULL
            GROUP BY vendor_id ORDER BY cnt DESC LIMIT 10
        """)).mappings()))

    if vid:
        print("\\n=== RECENT ORDERS (vendor_id=%s, last 15) ===" % vid)
        rows = conn.execute(text("""
            SELECT id, order_no, status, customer_name, order_date, created_at, deleted_at
            FROM orders WHERE vendor_id = :vid
            ORDER BY COALESCE(order_date, created_at) DESC LIMIT 15
        """), {{"vid": vid}}).mappings().all()
        for r in rows:
            print(dict(r))
        if not rows:
            print("(none)")

    print("\\n=== ORDERS wrongly using user id 1123 as vendor_id? ===")
    wrong = conn.execute(text("""
        SELECT id, order_no, status, vendor_id FROM orders
        WHERE vendor_id = :uid AND deleted_at IS NULL LIMIT 10
    """), {{"uid": uid}}).mappings().all()
    for r in wrong:
        print(dict(r))
    if not wrong:
        print("(none)")
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
    path = "/tmp/prod_vendor_orders.py"
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
