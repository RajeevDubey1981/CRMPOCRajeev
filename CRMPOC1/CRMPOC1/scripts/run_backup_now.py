"""Run the full INDcool backup on the production server, right now, and show the progress live.

It logs in with the SSH key ~/.ssh/indcool_backup (no password). Without that key it falls back to the
password from scripts/deploy.env (or asks for it), like deploy.py. It then starts
/usr/local/sbin/indcool-backup.sh on the server, which does everything:
  1. new app backup on the server (4 database dumps + uploads archive)
  2. deletes server backups older than 7 days (newest 3 always kept)
  3. uploads to Google Drive "INDcool Server Backups" and checks the copy
  4. only after the check passes: deletes Drive backups older than 7 days (newest 2 always kept)

Usage (from the project root):
  py scripts\\run_backup_now.py

Takes about 3 minutes. Exit code 0 = every step ok.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

SERVER_SCRIPT = "/usr/local/sbin/indcool-backup.sh"
KEY_FILE = Path.home() / ".ssh" / "indcool_backup"  # private key; its public half is in the server's authorized_keys


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1

    config = deploy.load_config()
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    key = Path(config.get("INDCOOL_DEPLOY_KEY_FILENAME") or KEY_FILE)

    print(f"Connecting to {host} as {user}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key.is_file():  # key login: no password needed
        client.connect(host, username=user, key_filename=str(key), look_for_keys=False, allow_agent=False, timeout=30)
    else:
        password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
        if not password or password == "YOUR_PASSWORD_HERE":
            password = getpass.getpass(f"SSH password for {user}@{host}: ")
        client.connect(host, username=user, password=password, timeout=30)
    try:
        chan = client.get_transport().open_session()
        chan.set_combine_stderr(True)
        chan.exec_command(f"sudo {SERVER_SCRIPT}")
        while True:
            data = chan.recv(4096)
            if not data:
                break
            sys.stdout.write(data.decode("utf-8", "replace"))
            sys.stdout.flush()
        status = chan.recv_exit_status()
    finally:
        client.close()

    print("\nBackup finished: all steps ok." if status == 0 else f"\nBackup FAILED (exit code {status}). See the lines above.")
    return 0 if status == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
