#!/usr/bin/env python3
"""Send the backup failure alert. Runs ON the production server as root (installed at
/usr/local/sbin/indcool-backup-alert.py, called by indcool-backup.sh when a backup fails).

Usage: indcool-backup-alert.py <to-address> <subject> <log-file>

Uses the same SMTP settings as the CRM (SMTP_* in /var/www/indcool/api/.env), so there is no second password
to keep. The mail carries the last lines of the backup log; the log holds no passwords or tokens.
"""
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

ENV_FILE = Path("/var/www/indcool/api/.env")


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    to, subject, log_file = sys.argv[1:4]
    env = load_env(ENV_FILE)
    try:
        lines = Path(log_file).read_text(encoding="utf-8", errors="replace").splitlines()[-60:]
    except OSError:
        lines = ["(no log available)"]

    msg = EmailMessage()
    msg["From"] = f"{env.get('SMTP_FROM_NAME', 'INDcool')} <{env['SMTP_FROM']}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(
        "The INDcool nightly backup did not finish correctly.\n\n"
        "Last lines of the run:\n" + "\n".join(lines) +
        "\n\nFull log on the server: /var/log/indcool-backup.log\n"
        "Run it again by hand:      sudo /usr/local/sbin/indcool-backup.sh\n"
    )

    with smtplib.SMTP(env["SMTP_HOST"], int(env.get("SMTP_PORT", "587")), timeout=30) as smtp:
        if env.get("SMTP_USE_TLS", "true").lower() == "true":
            smtp.starttls()
        if env.get("SMTP_USE_AUTH", "true").lower() == "true":
            smtp.login(env["SMTP_USER"], env["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print(f"alert mail sent to {to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
