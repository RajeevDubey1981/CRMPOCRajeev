"""Reset production admin password in the database (does not touch .env)."""
from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

REMOTE_PY = r'''
import os
from pathlib import Path

new_password = os.environ.get("NEW_ADMIN_PASSWORD", "")
if not new_password:
    raise SystemExit("NEW_ADMIN_PASSWORD not set")

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

import sys
sys.path.insert(0, "/var/www/indcool/api")
from sqlalchemy import create_engine, text
from app.security import hash_password

email = (os.environ.get("SEED_ADMIN_EMAIL") or "admin@indcool.com").strip()
engine = create_engine(os.environ["MYSQL_DATABASE_URL"])
with engine.begin() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash, is_active = 1 WHERE email = :email"),
        {"hash": hash_password(new_password), "email": email},
    )
    if result.rowcount == 0:
        raise SystemExit(f"No user updated for email={email}")

print(f"OK reset for {email}")
'''


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def main() -> int:
    new_password = sys.argv[1] if len(sys.argv) > 1 else generate_password()
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
    remote = "/tmp/prod_reset_admin_pw.py"
    with sftp.open(remote, "w") as f:
        f.write(REMOTE_PY)
    sftp.close()

    # Escape single quotes in password for shell
    escaped = new_password.replace("'", "'\"'\"'")
    cmd = (
        f"sudo -u www-data env NEW_ADMIN_PASSWORD='{escaped}' PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {remote}"
    )
    out = ssh_run(client, cmd)
    print(out.strip())
    client.close()

    print("\n--- Login credentials (production) ---")
    print("Email:    admin@indcool.com")
    print(f"Password: {new_password}")
    print("URL:      https://indcoolapplainces.com/login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
