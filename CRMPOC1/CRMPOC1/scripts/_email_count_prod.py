"""Count emails logged by indcool-api on production (journalctl)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402


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

    commands = [
        ("Journal retention / first lines", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | head -5"),
        ("Total 'email sent:' (all journal)", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email sent:' || echo 0"),
        ("Total 'email failed:' lines", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email failed:' || echo 0"),
        ("Any line containing 'email sent' (case)", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -ci 'email sent' || echo 0"),
        ("send_message / Message accepted", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -ci 'send_message' || echo 0"),
        ("Total 'email failed:' (all journal)", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email failed:' || echo 0"),
        ("Total 'email skipped' (all journal)", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email skipped' || echo 0"),
        ("Sent last 7 days", "sudo journalctl -u indcool-api --since '7 days ago' --no-pager 2>/dev/null | grep -c 'email sent:' || echo 0"),
        ("Sent last 30 days", "sudo journalctl -u indcool-api --since '30 days ago' --no-pager 2>/dev/null | grep -c 'email sent:' || echo 0"),
        ("Sent last 90 days", "sudo journalctl -u indcool-api --since '90 days ago' --no-pager 2>/dev/null | grep -c 'email sent:' || echo 0"),
        ("Last 5 successful sends", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email sent:' | tail -5"),
        ("First 3 successful sends", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email sent:' | head -3"),
        (
            "Top subjects (sent)",
            "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email sent:' | "
            "sed -n 's/.*subject=//p' | sort | uniq -c | sort -rn | head -20",
        ),
        (
            "Recent SMTP / email errors",
            "sudo journalctl -u indcool-api --no-pager 2>/dev/null | "
            "grep -iE 'email failed|SMTP|WebLogin|suspended|Authentication' | tail -25",
        ),
        (
            "EMAIL/SMTP config (no password)",
            "sudo grep -E '^EMAIL_ENABLED=|^SMTP_HOST=|^SMTP_PORT=|^SMTP_USER=|^SMTP_FROM=' "
            "/var/www/indcool/api/.env 2>/dev/null",
        ),
        ("Service uptime starts (last 10)", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'Started indcool-api' | tail -10"),
        ("Journal disk usage", "sudo journalctl --disk-usage"),
        ("indcool-api journal line count", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | wc -l"),
        (
            "All failed send attempts (by subject)",
            "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email failed:' | "
            "sed -n 's/.*subject=//p' | sort | uniq -c | sort -rn",
        ),
        ("WebLoginRequired occurrences", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c WebLoginRequired || echo 0"),
        ("First email failed line", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email failed:' | head -1"),
        ("Last email failed line", "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep 'email failed:' | tail -1"),
    ]

    # DB proxy counts (emails the app *tried* to trigger via workflow flags)
    db_py = r'''
import os
from pathlib import Path
for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()
from sqlalchemy import create_engine, text
url = os.environ.get("MYSQL_DATABASE_URL") or os.environ.get("DATABASE_URL")
engine = create_engine(url)
queries = {
    "service_requests_with_customer_email": "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND customer_email IS NOT NULL AND TRIM(customer_email) != ''",
    "service_document_request_sent_at_set": "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND document_request_sent_at IS NOT NULL",
    "complaints_with_customer_email": "SELECT COUNT(*) FROM complaints WHERE customer_email IS NOT NULL AND TRIM(customer_email) != ''",
    "partner_registration_invites": "SELECT COUNT(*) FROM partner_registrations",
}
with engine.connect() as conn:
    for label, q in queries.items():
        print(f"{label}={conn.execute(text(q)).scalar()}")
'''
    print("\n=== DB workflow proxies (not exact send count) ===")
    try:
        ssh_run(client, "cat > /tmp/email_db_count.py << 'PYEOF'\n" + db_py + "\nPYEOF")
        print(
            ssh_run(
                client,
                "sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
                "/var/www/indcool/api/venv/bin/python /tmp/email_db_count.py",
            ).strip()
        )
    except RuntimeError as exc:
        print(exc)

    for title, cmd in commands:
        print(f"\n=== {title} ===")
        try:
            out = ssh_run(client, cmd)
        except RuntimeError as exc:
            out = str(exc)
        print(out.strip() or "(empty)")

    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
