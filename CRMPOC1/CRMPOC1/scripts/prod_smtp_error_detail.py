"""Print full SMTP error from production (no secrets)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

REMOTE = r'''
import os
import smtplib
import sys
import traceback
from pathlib import Path

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

sys.path.insert(0, "/var/www/indcool/api")
from app.config import settings

user = (settings.smtp_user or "").strip()
password = (settings.smtp_password or "").strip()
print("smtp_user", user)
print("password_len", len(password))

try:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        code, msg = smtp.ehlo()
        print("ehlo", code, msg.decode(errors="replace")[:200])
        if settings.smtp_use_tls:
            code, msg = smtp.starttls()
            print("starttls", code, msg.decode(errors="replace")[:200])
            code, msg = smtp.ehlo()
            print("ehlo_after_tls", code, msg.decode(errors="replace")[:200])
        if settings.smtp_use_auth:
            smtp.login(user, password)
        print("RESULT", "SMTP_LOGIN_OK")
except Exception as exc:
    print("RESULT", "SMTP_LOGIN_FAILED")
    print("exception_type", type(exc).__name__)
    print("exception_repr", repr(exc))
    print("--- traceback ---")
    traceback.print_exc()
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
    p = "/tmp/prod_smtp_error_detail.py"
    with sftp.open(p, "w") as f:
        f.write(REMOTE)
    sftp.close()
    print(ssh_run(
        client,
        f"sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {p}",
    ))
    client.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
