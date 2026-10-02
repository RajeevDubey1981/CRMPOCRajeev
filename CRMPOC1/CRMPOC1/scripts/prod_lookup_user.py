"""Look up a user by id on production."""
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

queries = [
    ("user", """
        SELECT id, name, email, role, phone, is_active, deleted_at, created_at, updated_at
        FROM users WHERE id = :uid
    """),
    ("complaints_created", "SELECT COUNT(*) FROM complaints WHERE created_by = :uid AND deleted_at IS NULL"),
    ("complaints_assigned_engineer", "SELECT COUNT(*) FROM complaints WHERE assigned_engineer = :uid AND deleted_at IS NULL"),
    ("service_requests_created", "SELECT COUNT(*) FROM service_requests WHERE created_by = :uid AND deleted_at IS NULL"),
    ("recent_complaints_created", """
        SELECT id, comp_no, customer_name, status, query_type, created_at
        FROM complaints WHERE created_by = :uid AND deleted_at IS NULL
        ORDER BY created_at DESC LIMIT 5
    """),
    ("service_units_assigned", "SELECT COUNT(*) FROM service_request_units WHERE assigned_engineer_id = :uid"),
    ("services_head_engineer", "SELECT COUNT(*) FROM service_requests WHERE assigned_engineer_id = :uid AND deleted_at IS NULL"),
    ("vendor_row", """
        SELECT v.id, v.vendor_code, v.name_of_firm, v.email, v.contact_mobile, v.vendor_type, v.is_active
        FROM vendors v
        INNER JOIN users u ON LOWER(v.email) = LOWER(u.email)
        WHERE u.id = :uid AND v.deleted_at IS NULL
        LIMIT 1
    """),
    ("complaints_assigned_list", """
        SELECT id, comp_no, customer_name, status, query_type, status_date
        FROM complaints WHERE assigned_engineer = :uid AND deleted_at IS NULL
        ORDER BY status_date DESC LIMIT 10
    """),
]

LIST_LABELS = {"recent_complaints_created", "complaints_assigned_list", "vendor_row"}

with engine.connect() as conn:
    row = conn.execute(text(queries[0][1]), {{"uid": uid}}).mappings().first()
    if not row:
        print(f"NO_USER id={{uid}}")
    else:
        print("=== USER ===")
        for k, v in row.items():
            print(f"{{k}}={{v}}")
        for label, q in queries[1:]:
            if label in LIST_LABELS:
                print(f"\\n=== {{label.upper()}} ===")
                rows = conn.execute(text(q), {{"uid": uid}}).mappings().all()
                if not rows:
                    print("(none)")
                for r in rows:
                    print(dict(r))
            else:
                print(f"{{label}}={{conn.execute(text(q), {{'uid': uid}}).scalar()}}")
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
    path = "/tmp/prod_lookup_user.py"
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
