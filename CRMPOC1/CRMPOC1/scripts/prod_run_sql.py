"""Run a local .sql file against the production DB via SSH and print the output.

Usage (from project root):
  py scripts\\prod_run_sql.py path\\to\\file.sql
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOST = "97.74.83.211"
USER = "indcooladmin"
PASSWORD = "JAdJh@yg4SFDP#!nGH"
REMOTE_API = "/var/www/indcool/api"

REMOTE_RUNNER = r"""
import os, re, subprocess, tempfile
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

cnf_fd, cnf_path = tempfile.mkstemp(suffix=".cnf")
with os.fdopen(cnf_fd, "w") as f:
    f.write(f"[client]\nuser={user}\npassword={pwd}\nhost={host}\nport={port}\n")
os.chmod(cnf_path, 0o600)

try:
    with open("/tmp/indcool_run.sql", "rb") as f:
        result = subprocess.run(
            ["mysql", f"--defaults-extra-file={cnf_path}", "--table", db],
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
    if len(sys.argv) != 2:
        raise SystemExit("Usage: py scripts\\prod_run_sql.py path\\to\\file.sql")
    sql_file = Path(sys.argv[1])
    if not sql_file.is_file():
        raise SystemExit(f"SQL file not found: {sql_file}")

    try:
        import paramiko
    except ImportError:
        import subprocess
        print("Installing paramiko...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST} as {USER}...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    sftp = client.open_sftp()
    try:
        print(f"Uploading {sql_file.name}...")
        sftp.put(str(sql_file), "/tmp/indcool_run.sql")

        sftp_file = sftp.file("/tmp/indcool_run_sql.py", "w")
        sftp_file.write(REMOTE_RUNNER)
        sftp_file.close()

        print("\n=== Running SQL on production ===")
        _, stdout, stderr = client.exec_command(
            f"sudo -u www-data {REMOTE_API}/venv/bin/python /tmp/indcool_run_sql.py",
            get_pty=True,
        )
        print(stdout.read().decode("utf-8", "replace"))
        err = stderr.read().decode("utf-8", "replace")
        if err.strip():
            print("STDERR:", err)
    finally:
        sftp.close()
        client.close()


if __name__ == "__main__":
    main()
