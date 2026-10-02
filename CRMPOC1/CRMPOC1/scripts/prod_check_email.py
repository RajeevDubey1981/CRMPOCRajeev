"""Check SMTP config and send a probe on production (no password printed)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

# Optional: py prod_check_email.py someone@example.com
TEST_TO = sys.argv[1] if len(sys.argv) > 1 else ""

REMOTE = f'''
import os
import sys
from pathlib import Path

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

sys.path.insert(0, "/var/www/indcool/api")
from app.config import settings

print("EMAIL_ENABLED", settings.email_enabled)
print("SMTP_HOST", settings.smtp_host)
print("SMTP_PORT", settings.smtp_port)
print("SMTP_USER", settings.smtp_user)
print("SMTP_PASSWORD_SET", bool((settings.smtp_password or "").strip()))
print("SMTP_FROM", settings.smtp_from)
print("SMTP_USE_TLS", settings.smtp_use_tls)
print("SMTP_USE_AUTH", settings.smtp_use_auth)

test_to = {repr(TEST_TO)}
if test_to:
    from app.services.email_service import send_email
    ok = send_email(
        test_to,
        "Indcool production SMTP test",
        "<p>This is an automated SMTP test from production.</p>",
        text_body="This is an automated SMTP test from production.",
        template="smtp_probe",
    )
    print("PROBE_SEND", "ok" if ok else "failed")
else:
    import smtplib
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_use_auth:
                smtp.login(
                    (settings.smtp_user or "").strip(),
                    (settings.smtp_password or "").strip(),
                )
        print("SMTP_LOGIN", "ok")
    except Exception as e:
        print("SMTP_LOGIN", "failed")
        print("ERROR", type(e).__name__, str(e)[:200])
'''

REMOTE_LOGS = r'''
sudo journalctl -u indcool-api -n 200 --no-pager 2>/dev/null | grep -iE 'email (sent|failed|skipped)' | tail -15 || true
'''

REMOTE_DB = r'''
import os
import sys
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
    try:
        rows = conn.execute(text("""
            SELECT status, COUNT(*) AS cnt FROM email_send_logs
            GROUP BY status ORDER BY status
        """)).mappings().all()
        print("email_send_logs_summary", [dict(r) for r in rows])
        recent = conn.execute(text("""
            SELECT id, to_email, subject, status, error_message, created_at
            FROM email_send_logs ORDER BY id DESC LIMIT 5
        """)).mappings().all()
        print("email_send_logs_recent")
        for r in recent:
            d = dict(r)
            if d.get("error_message"):
                d["error_message"] = str(d["error_message"])[:120]
            print(d)
    except Exception as e:
        print("email_send_logs", "unavailable", str(e)[:100])
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
    py_path = "/tmp/prod_check_email.py"
    db_path = "/tmp/prod_check_email_db.py"
    with sftp.open(py_path, "w") as f:
        f.write(REMOTE)
    with sftp.open(db_path, "w") as f:
        f.write(REMOTE_DB)
    sftp.close()

    print("=== SMTP config + login test ===")
    print(ssh_run(
        client,
        f"sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {py_path}",
    ))
    print("\n=== Recent API email log lines ===")
    print(ssh_run(client, REMOTE_LOGS))
    print("\n=== email_send_logs (if migrated) ===")
    print(ssh_run(
        client,
        f"sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {db_path}",
    ))
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
