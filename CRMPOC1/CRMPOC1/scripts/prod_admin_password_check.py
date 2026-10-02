"""Check prod admin login: .env seed password vs DB hash (does not print .env password)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

REMOTE = r'''
import os
from pathlib import Path

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

sys_path = "/var/www/indcool/api"
import sys
sys.path.insert(0, sys_path)

from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User
from app.security import verify_password
from app.config import settings

email = (settings.seed_admin_email or "admin@indcool.com").strip()
seed_pwd = settings.seed_admin_password or ""

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        print(f"STATUS=no_user email={email}")
    elif not user.is_active:
        print(f"STATUS=inactive email={email}")
    elif seed_pwd and verify_password(seed_pwd, user.password_hash):
        print(f"STATUS=matches_seed email={email}")
        print(f"SEED_PASSWORD_LEN={len(seed_pwd)}")
    else:
        print(f"STATUS=password_not_seed email={email}")
        print("HINT=Password was changed in app; use reset script or User management after login as another admin.")
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

    print("=== SEED_ADMIN_* from prod .env (password shown only to operator running this script) ===")
    out = ssh_run(
        client,
        "sudo grep -E '^SEED_ADMIN_EMAIL=|^SEED_ADMIN_PASSWORD=' /var/www/indcool/api/.env",
    )
    print(out.strip())

    sftp = client.open_sftp()
    remote_py = "/tmp/prod_admin_pwd_check.py"
    with sftp.open(remote_py, "w") as f:
        f.write(REMOTE)
    sftp.close()

    print("\n=== Does DB admin hash match SEED_ADMIN_PASSWORD? ===")
    print(
        ssh_run(
            client,
            f"sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
            f"/var/www/indcool/api/venv/bin/python {remote_py}",
        ).strip()
    )
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
