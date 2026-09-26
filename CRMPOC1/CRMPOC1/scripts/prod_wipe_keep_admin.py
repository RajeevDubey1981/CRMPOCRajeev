"""One-off admin script: back up production DB, then wipe all data except the admin user.

Keeps intact: users.email = admin@indcool.com, roles, permissions, alembic_version.
Everything else is deleted. Takes a mysqldump backup first (downloaded locally) before wiping.

Usage (from project root, with paramiko installed in the local Python env):
  py scripts\\prod_wipe_keep_admin.py
"""
from __future__ import annotations

import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "api" / "sql" / "delete_all_data_keep_admin_users_mysql.sql"

HOST = "97.74.83.211"
USER = "indcooladmin"
PASSWORD = "JAdJh@yg4SFDP#!nGH"
REMOTE_API = "/var/www/indcool/api"

REMOTE_WIPE_SCRIPT = r"""
import os, re, subprocess, datetime, tempfile
from pathlib import Path
from urllib.parse import unquote

for line in Path("__REMOTE_API__/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()

url = os.environ.get("MYSQL_DATABASE_URL", "")
m = re.match(r"mysql\+mysqlconnector://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(\w+)", url)
if not m:
    raise SystemExit(f"Could not parse MYSQL_DATABASE_URL: {url!r}")
user, pwd, host, port, db = m.groups()
pwd = unquote(pwd)
port = port or "3306"

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"/tmp/indcool_prod_backup_{ts}.sql"

cnf_fd, cnf_path = tempfile.mkstemp(suffix=".cnf")
with os.fdopen(cnf_fd, "w") as f:
    f.write(f"[client]\nuser={user}\npassword={pwd}\nhost={host}\nport={port}\n")
os.chmod(cnf_path, 0o600)

try:
    with open(backup_path, "wb") as out:
        subprocess.run(["mysqldump", f"--defaults-extra-file={cnf_path}", db], stdout=out, check=True)
    print(f"BACKUP_OK {backup_path}")

    with open("/tmp/indcool_cleanup.sql", "rb") as f:
        result = subprocess.run(
            ["mysql", f"--defaults-extra-file={cnf_path}", db],
            stdin=f, capture_output=True, text=True,
        )
    print(result.stdout)
    if result.stderr.strip():
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
finally:
    os.remove(cnf_path)
""".replace("__REMOTE_API__", REMOTE_API)


def main() -> None:
    try:
        import paramiko
    except ImportError:
        import subprocess
        import sys
        print("Installing paramiko...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko

    password = PASSWORD
    if not password or password == "YOUR_PASSWORD_HERE":
        password = getpass.getpass(f"SSH password for {USER}@{HOST}: ")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST} as {USER}...")
    client.connect(HOST, username=USER, password=password, timeout=30)
    sftp = client.open_sftp()
    try:
        print("Uploading cleanup SQL...")
        sftp.put(str(SQL_FILE), "/tmp/indcool_cleanup.sql")

        print("Uploading wipe/backup runner...")
        sftp_file = sftp.file("/tmp/indcool_wipe.py", "w")
        sftp_file.write(REMOTE_WIPE_SCRIPT)
        sftp_file.close()

        print("\n=== Running backup + wipe on production ===")
        _, stdout, stderr = client.exec_command(
            f"sudo -u www-data {REMOTE_API}/venv/bin/python /tmp/indcool_wipe.py",
            get_pty=True,
        )
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        print(out)
        if err.strip():
            print("STDERR:", err)

        backup_line = next((l for l in out.splitlines() if l.startswith("BACKUP_OK")), None)
        if backup_line:
            remote_backup_path = backup_line.split(" ", 1)[1].strip()
            local_backup_path = ROOT / "api" / f"prod_backup_{Path(remote_backup_path).stem.split('_', 2)[-1]}.sql"
            print(f"\nDownloading backup to {local_backup_path}...")
            sftp.get(remote_backup_path, str(local_backup_path))
            print(f"Backup saved locally: {local_backup_path}")
        else:
            print("\nWARNING: backup marker not found in output; verify manually before trusting the wipe.")
    finally:
        sftp.close()
        client.close()


if __name__ == "__main__":
    main()
