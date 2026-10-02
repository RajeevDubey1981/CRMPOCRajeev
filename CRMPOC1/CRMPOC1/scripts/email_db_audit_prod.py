"""Estimate max possible CRM-triggered emails from production DB (no send log in DB)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

RUNNER = r'''
import os
from pathlib import Path
from sqlalchemy import create_engine, text

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

url = os.environ.get("MYSQL_DATABASE_URL") or os.environ.get("DATABASE_URL")
engine = create_engine(url)

QUERIES = [
    ("complaints_total", "SELECT COUNT(*) FROM complaints WHERE deleted_at IS NULL"),
    ("complaints_with_email", "SELECT COUNT(*) FROM complaints WHERE deleted_at IS NULL AND customer_email IS NOT NULL AND TRIM(customer_email) <> ''"),
    ("complaints_api_created_log", "SELECT COUNT(DISTINCT complaint_id) FROM complaint_status_logs WHERE remark = 'Complaint created'"),
    ("complaint_status_request_sent", "SELECT COUNT(*) FROM complaint_status_logs WHERE action_taken = 'Request Sent'"),
    ("complaints_service_type_with_email", "SELECT COUNT(*) FROM complaints WHERE deleted_at IS NULL AND LOWER(query_type) = 'service' AND customer_email IS NOT NULL AND TRIM(customer_email) <> ''"),
    ("service_requests_total", "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL"),
    ("service_requests_with_email", "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND customer_email IS NOT NULL AND TRIM(customer_email) <> ''"),
    ("service_linked_to_complaint", "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND complaint_id IS NOT NULL"),
    ("service_document_link_flag", "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND document_request_sent_at IS NOT NULL"),
    ("installation_document_link_flag", "SELECT COUNT(*) FROM installation_requests WHERE document_request_sent_at IS NOT NULL"),
    ("partner_registrations", "SELECT COUNT(*) FROM partner_registrations"),
    ("partner_email_resend_used", "SELECT COUNT(*) FROM partner_registrations WHERE email_resend_used = 1"),
    ("partner_agreements_otp_sent", "SELECT COUNT(*) FROM partner_agreements WHERE otp_sent_at IS NOT NULL"),
]

# Complaints by source (import vs callcenter vs public)
BY_SOURCE = """
SELECT COALESCE(source, '(null)') AS source, COUNT(*) AS cnt
FROM complaints WHERE deleted_at IS NULL
GROUP BY COALESCE(source, '(null)')
ORDER BY cnt DESC
"""

# Monthly complaint creates with API log (proxy for confirmation email on create)
MONTHLY_CREATED = """
SELECT DATE_FORMAT(c.created_at, '%Y-%m') AS month, COUNT(DISTINCT c.id) AS complaints
FROM complaints c
INNER JOIN complaint_status_logs l ON l.complaint_id = c.id AND l.remark = 'Complaint created'
WHERE c.deleted_at IS NULL
GROUP BY DATE_FORMAT(c.created_at, '%Y-%m')
ORDER BY month
"""

print("=== COUNTS (each line is one DB metric) ===")
with engine.connect() as conn:
    for label, q in QUERIES:
        print(f"{label}={conn.execute(text(q)).scalar()}")

    print("\n=== COMPLAINTS BY SOURCE ===")
    for row in conn.execute(text(BY_SOURCE)):
        print(f"  {row.source}: {row.cnt}")

    print("\n=== MONTHLY COMPLAINTS WITH 'Complaint created' LOG (API create proxy) ===")
    total_api = 0
    for row in conn.execute(text(MONTHLY_CREATED)):
        total_api += row.complaints
        print(f"  {row.month}: {row.complaints}")
    print(f"  TOTAL_api_create_proxy={total_api}")

# Rough upper bound if every trigger sent exactly one email
print("\n=== THEORETICAL UPPER BOUNDS (if every action sent 1 email) ===")
with engine.connect() as conn:
    api_creates = conn.execute(text(
        "SELECT COUNT(DISTINCT complaint_id) FROM complaint_status_logs WHERE remark = 'Complaint created'"
    )).scalar()
    svc = conn.execute(text("SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL")).scalar()
    doc_svc = conn.execute(text(
        "SELECT COUNT(*) FROM service_requests WHERE deleted_at IS NULL AND document_request_sent_at IS NOT NULL"
    )).scalar()
    doc_inst = conn.execute(text(
        "SELECT COUNT(*) FROM installation_requests WHERE document_request_sent_at IS NOT NULL"
    )).scalar()
    req_sent = conn.execute(text(
        "SELECT COUNT(*) FROM complaint_status_logs WHERE action_taken = 'Request Sent'"
    )).scalar()
    partners = conn.execute(text("SELECT COUNT(*) FROM partner_registrations")).scalar()
    # create complaint email: ~1 per api create (service may send ack not complaint email)
    # document link: at most req_sent or doc flags
    loose_max = api_creates + svc + doc_svc + doc_inst + partners + req_sent
    print(f"  api_complaint_creates={api_creates}")
    print(f"  service_requests={svc}")
    print(f"  service_document_request_sent_at={doc_svc}")
    print(f"  installation_document_request_sent_at={doc_inst}")
    print(f"  complaint_action_request_sent_logs={req_sent}")
    print(f"  partner_registrations={partners}")
    print(f"  LOOSE_SUM (overcounts; not actual sends)={loose_max}")
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
    remote = "/tmp/indcool_email_db_audit.py"
    with sftp.open(remote, "w") as f:
        f.write(RUNNER)
    sftp.close()
    print(ssh_run(
        client,
        "sudo -u www-data env PYTHONPATH=/var/www/indcool/api "
        f"/var/www/indcool/api/venv/bin/python {remote}",
    ))
    print("\n=== JOURNAL: email sent / failed (all time) ===")
    for cmd in [
        "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email sent:' || echo 0",
        "sudo journalctl -u indcool-api --no-pager 2>/dev/null | grep -c 'email failed:' || echo 0",
    ]:
        try:
            print(ssh_run(client, cmd).strip())
        except RuntimeError as e:
            print(e)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
