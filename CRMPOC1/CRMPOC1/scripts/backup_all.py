"""One-shot INDcool backup: server app backup + database dumps to Google Drive, with cleanup of old ones.

What it does, in this order (nothing is deleted until the new copy is made and checked):

  1. SERVER  creates a new backup folder /var/backups/indcool/daily-<time> holding every database dump
             (indcool, indcool_sales, indcool_marketing, indcool_parts -- each only if present), the uploads
             folder as files.tar.gz, and a copy of api/.env (the .env stays on the server, never goes to Drive).
             Every file is gzip-tested and its SHA-256 recorded.
  2. SERVER  deletes old app backups: folders older than --server-keep-days (default 7). The newest 3 are
             always kept, so there is never a day without a backup.
  3. DRIVE   downloads the dumps + files archive to this PC, checks each against the server's SHA-256,
             uploads them to <remote>/<time>/ with rclone, then runs `rclone check` to prove they arrived.
  4. DRIVE   only when step 3 is fully verified: deletes Drive backup folders older than --drive-keep-days
             (default 7). The newest 2 are always kept. Deletes are permanent (they skip the Drive trash).

Nothing in the databases or the live uploads folder is changed. No password or Google credential is written
anywhere: SSH settings come from scripts/deploy.env (gitignored, same as deploy.py) or a prompt, and rclone
keeps its own Google sign-in.

Usage (from the project root):
  py scripts\\backup_all.py                 # real run
  py scripts\\backup_all.py --dry-run       # print the plan, touch nothing
  py scripts\\backup_all.py --skip-drive    # server backup + server cleanup only
  py scripts\\backup_all.py --remote "indcool-gdrive:INDcool CRM Backups" --drive-keep-days 14

One-time setup: py -m pip install paramiko, and an rclone remote (rclone config) signed in to the Drive.
"""
from __future__ import annotations

import argparse
import getpass
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (same settings loader as deploy.py / server_backup.py)

BACKUP_ROOT = "/var/backups/indcool"
SERVER_PREFIXES = ("predeploy-", "daily-")  # only folders with these prefixes are ever cleaned up
DATABASES = ("indcool", "indcool_sales", "indcool_marketing", "indcool_parts")
DEFAULT_REMOTE = "indcool-gdrive:INDcool CRM Backups"
STAMP_RE = re.compile(r"^\d{8}-\d{6}$")


def say(text: str = "") -> None:
    print(text, flush=True)


def step(text: str) -> None:
    say(f"\n== {text}")


def find_rclone() -> str | None:
    found = shutil.which("rclone")
    if found:
        return found
    candidates = [str(Path.home() / ".indcool-backup" / "rclone" / "rclone.exe")]
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates += glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Rclone.Rclone_*", "**", "rclone.exe"), recursive=True)
    return next((c for c in candidates if os.path.isfile(c)), None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class Server:
    def __init__(self, host: str, user: str, password: str) -> None:
        import paramiko

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=user, password=password, timeout=30)

    def run(self, cmd: str, timeout: int = 1800) -> str:
        _, out, err = self.client.exec_command(cmd, timeout=timeout)
        text = out.read().decode("utf-8", "replace")
        status = out.channel.recv_exit_status()
        if status != 0:
            raise RuntimeError(f"server command failed ({status}): {cmd[:120]}\n{err.read().decode('utf-8', 'replace')[-500:]}")
        return text

    def close(self) -> None:
        self.client.close()


def make_server_backup(srv: Server, stamp: str, remote_api: str) -> tuple[str, dict[str, tuple[int, str]]]:
    """Create the folder and return (folder, {filename: (bytes, sha256)}) for the files Drive will get."""
    folder = f"{BACKUP_ROOT}/daily-{stamp}"
    srv.run(f"sudo mkdir -p {folder} && sudo chmod 700 {folder}")
    made: dict[str, tuple[int, str]] = {}

    def check(name: str) -> None:
        path = f"{folder}/{name}"
        srv.run(f"sudo gzip -t {path}")  # a damaged file fails here
        size, digest = srv.run(f"sudo sh -c 'echo $(stat -c %s {path}) $(sha256sum {path} | cut -d\" \" -f1)'").split()
        made[name] = (int(size), digest)
        say(f"   ok  {name}  {int(size) / 1024 / 1024:.1f} MB")

    for db in DATABASES:
        present = srv.run(f"sudo mysql -N -e \"SHOW DATABASES LIKE '{db}'\"").strip()
        if present != db:
            say(f"   --  {db}: not on this server, skipped")
            continue
        name = f"db-{db}.sql.gz"
        srv.run(
            "sudo bash -c \"set -o pipefail; mysqldump --single-transaction --routines --triggers --no-tablespaces "
            f"--default-character-set=utf8mb4 {db} | gzip > {folder}/{name}\""
        )
        check(name)

    lines = srv.run(f"sudo grep -i '^UPLOAD_DIR=' {remote_api}/.env | cut -d= -f2").strip().splitlines()
    upload_dir = lines[-1].strip() if lines and lines[-1].strip().startswith("/") else "/var/www/indcool/uploads"
    srv.run(f"sudo tar -czf {folder}/files.tar.gz -C {upload_dir} .")
    check("files.tar.gz")

    srv.run(f"sudo cp {remote_api}/.env {folder}/api.env && sudo chmod 600 {folder}/api.env")
    return folder, made


def clean_server(srv: Server, keep_days: int, dry_run: bool) -> None:
    rows = srv.run(f"sudo find {BACKUP_ROOT} -mindepth 1 -maxdepth 1 -type d -printf '%T@ %f\\n'").strip().splitlines()
    folders = sorted(((float(t), n) for t, n in (r.split(" ", 1) for r in rows) if n.startswith(SERVER_PREFIXES)), reverse=True)
    cutoff = time.time() - keep_days * 86400
    old = [n for t, n in folders[3:] if t < cutoff]  # the newest 3 are always kept
    say(f"   {len(folders)} app backup folder(s) on the server, {len(old)} older than {keep_days} days")
    for name in old:
        if dry_run:
            say(f"   [dry run] would delete {BACKUP_ROOT}/{name}")
        else:
            srv.run(f"sudo rm -rf {BACKUP_ROOT}/{name}")
            say(f"   deleted {name}")


def rclone(exe: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([exe, *args], capture_output=True, text=True)


def upload_to_drive(srv: Server, exe: str, remote: str, stamp: str, folder: str, made: dict[str, tuple[int, str]]) -> None:
    tmp_remote = f"/tmp/bkdl-{stamp}"
    local = Path(tempfile.mkdtemp(prefix=f"indcool-backup-{stamp}-"))
    try:
        paths = " ".join(f"{folder}/{n}" for n in made)
        srv.run(f"rm -rf {tmp_remote} && mkdir {tmp_remote} && sudo cp {paths} {tmp_remote}/ && sudo chown -R $(id -un) {tmp_remote}")
        sftp = srv.client.open_sftp()
        for name, (size, digest) in made.items():
            sftp.get(f"{tmp_remote}/{name}", str(local / name))
            if (local / name).stat().st_size != size or sha256_file(local / name) != digest:
                raise RuntimeError(f"{name} was damaged in download (size or SHA-256 differs from the server)")
            say(f"   downloaded and verified {name}")
        sftp.close()

        target = f"{remote}/{stamp}"
        say(f"   uploading to {target} ...")
        res = rclone(exe, "copy", str(local), target, "--checksum")
        if res.returncode != 0:
            raise RuntimeError(f"rclone copy failed:\n{res.stderr[-800:]}")
        res = rclone(exe, "check", str(local), target)
        if res.returncode != 0:
            raise RuntimeError(f"rclone check says the upload does not match:\n{res.stderr[-800:]}")
        say(f"   Drive check passed: {len(made)} file(s) match")
    finally:
        shutil.rmtree(local, ignore_errors=True)
        try:
            srv.run(f"rm -rf {tmp_remote}")
        except Exception:
            pass


def clean_drive(exe: str, remote: str, keep_days: int, dry_run: bool) -> None:
    res = rclone(exe, "lsf", "--dirs-only", remote)
    if res.returncode != 0:
        raise RuntimeError(f"could not list Drive folder:\n{res.stderr[-500:]}")
    sets = sorted((n.strip("/") for n in res.stdout.splitlines() if STAMP_RE.match(n.strip("/"))), reverse=True)
    cutoff = datetime.now() - timedelta(days=keep_days)
    old = [n for n in sets[2:] if datetime.strptime(n, "%Y%m%d-%H%M%S") < cutoff]  # newest 2 always kept
    say(f"   {len(sets)} backup set(s) on Drive, {len(old)} older than {keep_days} days")
    for name in old:
        if dry_run:
            say(f"   [dry run] would delete {remote}/{name}")
        else:
            r = rclone(exe, "purge", f"{remote}/{name}", "--drive-use-trash=false")
            if r.returncode != 0:
                raise RuntimeError(f"could not delete {name} from Drive:\n{r.stderr[-500:]}")
            say(f"   deleted {name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Server app backup + database dumps to Google Drive, with cleanup.")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help=f'rclone remote and folder (default "{DEFAULT_REMOTE}")')
    ap.add_argument("--server-keep-days", type=int, default=7)
    ap.add_argument("--drive-keep-days", type=int, default=7)
    ap.add_argument("--skip-drive", action="store_true", help="server backup and server cleanup only")
    ap.add_argument("--dry-run", action="store_true", help="show the plan; connect to nothing, change nothing")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    exe = None if args.skip_drive else find_rclone()
    if not args.skip_drive and not exe and not args.dry_run:
        say("rclone not found. Install it (winget install Rclone.Rclone) or use --skip-drive.")
        return 1

    if args.dry_run:
        step(f"DRY RUN {stamp} (nothing will be touched)")
        say(f"   1. server: create {BACKUP_ROOT}/daily-{stamp} with dumps of {', '.join(DATABASES)} + files.tar.gz + api.env")
        say(f"   2. server: delete app backup folders older than {args.server_keep_days} days (newest 3 always kept)")
        if not args.skip_drive:
            say(f"   3. drive : download, verify, upload to {args.remote}/{stamp}, then rclone check  (rclone: {exe or 'NOT FOUND'})")
            say(f"   4. drive : delete backup sets older than {args.drive_keep_days} days (newest 2 always kept)")
        return 0

    try:
        import paramiko  # noqa: F401
    except ImportError:
        say("Install paramiko first:  py -m pip install paramiko")
        return 1

    config = deploy.load_config()
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    if not password or password == "YOUR_PASSWORD_HERE":
        password = getpass.getpass(f"SSH password for {user}@{host}: ")

    step(f"Connecting to {host} as {user}")
    srv = Server(host, user, password)
    failed = False
    try:
        step(f"1. New app backup on the server (daily-{stamp})")
        folder, made = make_server_backup(srv, stamp, config["REMOTE_API"])
        say(f"   folder: {folder}")

        step(f"2. Delete old app backups on the server (older than {args.server_keep_days} days)")
        clean_server(srv, args.server_keep_days, dry_run=False)

        if args.skip_drive:
            say("\nSkipped Google Drive (--skip-drive).")
        else:
            step(f"3. Database + files backup to Google Drive ({args.remote}/{stamp})")
            try:
                upload_to_drive(srv, exe, args.remote, stamp, folder, made)
            except Exception as exc:
                failed = True
                say(f"   FAILED: {exc}")
                say("   Old Drive backups were NOT deleted.")
            if not failed:
                step(f"4. Delete old backups on Google Drive (older than {args.drive_keep_days} days)")
                try:
                    clean_drive(exe, args.remote, args.drive_keep_days, dry_run=False)
                except Exception as exc:
                    failed = True
                    say(f"   FAILED: {exc}")
    finally:
        srv.close()

    say("\nFinished WITH ERRORS (see above)." if failed else "\nFinished: all steps ok.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
