"""Look up users/vendors by email on production."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

EMAIL = sys.argv[1] if len(sys.argv) > 1 else "rma@ptfl.in"

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

engine = create_engine(os.environ["MYSQL_DATABASE_URL"])
em = {repr(EMAIL)}

with engine.connect() as conn:
    print("=== users exact email (including soft-deleted) ===")
    rows = conn.execute(text("""
        SELECT id, name, email, role, phone, is_active, deleted_at, created_at
        FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM(:em))
        ORDER BY id
    """), {{"em": em}}).mappings().all()
    if not rows:
        print("(no user row)")
    for r in rows:
        print(dict(r))

    print("\\n=== users @ptfl.in domain ===")
    for r in conn.execute(text("""
        SELECT id, name, email, role, is_active, deleted_at
        FROM users WHERE LOWER(email) LIKE '%ptfl.in%'
        ORDER BY id
    """)).mappings():
        print(dict(r))

    print("\\n=== vendors with this email ===")
    for r in conn.execute(text("""
        SELECT id, vendor_code, name_of_firm, email, is_active, deleted_at
        FROM vendors WHERE LOWER(TRIM(email)) = LOWER(TRIM(:em))
        ORDER BY id
    """), {{"em": em}}).mappings():
        print(dict(r))

    print("\\n=== would appear in Admin user list? (deleted_at IS NULL) ===")
    active = conn.execute(text("""
        SELECT COUNT(*) FROM users
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(:em)) AND deleted_at IS NULL
    """), {{"em": em}}).scalar()
    print("active_user_count", active)
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
    path = "/tmp/prod_lookup_email.py"
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
