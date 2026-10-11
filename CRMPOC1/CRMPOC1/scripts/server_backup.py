"""Take a backup on the production server before a deploy: the CRM database, the Sales database, the Marketing database
(each one only if it exists), the uploaded files, and a copy of the .env, into a new folder
/var/backups/indcool/predeploy-<date>-<time> that only root can read. Nothing is changed or deleted.

Uses the same connection settings as scripts/deploy.py (scripts/deploy.env), so there is nothing new to configure.

Usage (from the project root):  py scripts/server_backup.py
"""
from __future__ import annotations

import getpass
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (the same settings and the same remote runner as the deploy)


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    if not password or password == "YOUR_PASSWORD_HERE":
        password = getpass.getpass(f"SSH password for {user}@{host}: ")
    remote_api = config["REMOTE_API"]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder = f"/var/backups/indcool/predeploy-{stamp}"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    client.connect(host, username=user, password=password, timeout=30)
    try:
        run = lambda cmd: deploy.ssh_run(client, cmd, timeout=1800)  # noqa: E731
        run(f"sudo mkdir -p {folder} && sudo chmod 700 {folder}")
        for db in ("indcool", "indcool_sales", "indcool_marketing"):
            exists = run(f"sudo mysql -N -e \"SHOW DATABASES LIKE '{db}'\" | wc -l").strip().splitlines()[-1].strip()
            if exists != "1":
                print(f"{db}: not on this server, skipped")
                continue
            out = f"{folder}/db-{db}.sql.gz"
            run(f"sudo sh -c \"mysqldump --single-transaction --routines {db} | gzip > {out}\"")
            run(f"sudo gzip -t {out}")  # a damaged dump fails here
            size = run(f"sudo stat -c %s {out}").strip().splitlines()[-1].strip()
            print(f"BACKUP {db}: ok, {size} bytes")
        up = run(f"sudo grep -i '^UPLOAD_DIR=' {remote_api}/.env | cut -d= -f2").strip().splitlines()
        upload_dir = (up[-1].strip() if up and up[-1].strip().startswith("/") else "/var/www/indcool/uploads")
        run(f"sudo tar -czf {folder}/files.tar.gz -C {upload_dir} .")
        run(f"sudo gzip -t {folder}/files.tar.gz")
        size = run(f"sudo stat -c %s {folder}/files.tar.gz").strip().splitlines()[-1].strip()
        print(f"BACKUP files: ok, {size} bytes")
        run(f"sudo cp {remote_api}/.env {folder}/api.env && sudo chmod 600 {folder}/api.env")
        print(f"BACKUP folder: {folder}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
