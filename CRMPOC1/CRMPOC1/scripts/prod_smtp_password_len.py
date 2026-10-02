"""Verify SMTP_PASSWORD length on prod vs local example (no secret printed)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

SOURCE = Path(__file__).resolve().parents[1] / ".env.production.example"

def local_len() -> int:
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("SMTP_PASSWORD="):
            return len(line.split("=", 1)[1].strip())
    return -1

REMOTE = r'''
from pathlib import Path
for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    if line.strip().startswith("SMTP_PASSWORD="):
        print("prod_password_len", len(line.split("=", 1)[1].strip()))
        break
else:
    print("prod_password_len", "missing")
'''

def main() -> int:
    print("local_example_password_len", local_len())
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
    p = "/tmp/prod_smtp_len.py"
    with sftp.open(p, "w") as f:
        f.write(REMOTE)
    sftp.close()
    print(ssh_run(client, f"sudo python3 {p}"))
    client.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
