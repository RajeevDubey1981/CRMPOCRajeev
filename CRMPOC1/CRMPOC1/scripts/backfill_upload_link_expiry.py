"""One-off: the 48h-expiry feature only applies to links sent after it was deployed -- any
document-upload link sent in the 3 days before that has no expiry/reminder state at all. This finds
those, gives each a fresh 48h window starting now (not from the original send time, so nobody's link
is instantly expired by backfilling it), and immediately emails the customer with the new deadline --
marked as Reminder 1 sent so the hourly cron doesn't double-send to them.

Runs on the production server over the same SSH connection scripts/deploy.py uses, so it reads real
DB/SMTP credentials from the server's own .env -- nothing is read or typed locally.

Usage (from project root):
  py scripts/backfill_upload_link_expiry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

import paramiko  # noqa: E402

REMOTE_SCRIPT = r"""
import os, sys
from pathlib import Path

sys.path.insert(0, "/var/www/indcool/api")

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()
os.chdir("/var/www/indcool/api")

from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.database import SessionLocal
from app.models.installation import InstallationDocument, InstallationRequest
from app.services.email_service import send_document_upload_reminder_email
from app.services.installation_workflow import document_upload_url

now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=3)

db = SessionLocal()
updated = 0
try:
    candidates = db.scalars(
        select(InstallationRequest).where(
            InstallationRequest.document_access_token.is_not(None),
            InstallationRequest.document_access_token_expires_at.is_(None),
            InstallationRequest.document_request_sent_at.is_not(None),
            InstallationRequest.document_request_sent_at >= cutoff,
            InstallationRequest.customer_email.is_not(None),
        )
    ).all()

    for inst in candidates:
        has_upload = db.scalar(
            select(InstallationDocument.id).where(InstallationDocument.installation_request_id == inst.id).limit(1)
        )
        if has_upload:
            continue

        inst.document_access_token_expires_at = now + timedelta(hours=48)
        inst.document_reminder_1_sent_at = now
        inst.document_reminder_2_sent_at = None
        inst.document_expired_notified_at = None

        upload_url = document_upload_url(inst) or ""
        send_document_upload_reminder_email(
            inst.customer_email, inst.customer_name, f"INST-{inst.id}", upload_url, hours_remaining=48,
        )
        updated += 1
        print(f"Updated + emailed installation_request_id={inst.id} ({inst.customer_email})")

    db.commit()
finally:
    db.close()

print(f"Done. {updated} request(s) backfilled with a fresh 48h link and emailed.")
"""


def main() -> int:
    config = load_config()
    host = config["INDCOOL_DEPLOY_HOST"]
    user = config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD") or None
    key_filename = config.get("INDCOOL_DEPLOY_KEY_FILENAME") or None
    remote_api = config["REMOTE_API"]

    if not password and not key_filename:
        print("Production deploy SSH authentication is not configured in scripts/deploy.env.")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    ssh_options = {"username": user, "timeout": 30, "allow_agent": True, "look_for_keys": True}
    if password:
        ssh_options["password"] = password
    if key_filename:
        ssh_options["key_filename"] = key_filename
    client.connect(host, **ssh_options)
    try:
        remote = REMOTE_SCRIPT.replace("/var/www/indcool/api", remote_api)
        ssh_run(client, f"cat > /tmp/indcool_backfill_upload_links.py <<'PY'\n{remote}\nPY")
        print(ssh_run(client, f"sudo -u www-data {remote_api}/venv/bin/python /tmp/indcool_backfill_upload_links.py"))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
