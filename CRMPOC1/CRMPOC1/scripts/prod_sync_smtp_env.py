"""Sync SMTP_* and EMAIL_ENABLED from .env.production.example to production api/.env."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".env.production.example"
ENV_PATH = "/var/www/indcool/api/.env"

SMTP_KEYS = (
    "EMAIL_ENABLED",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_FROM_NAME",
    "SMTP_USE_TLS",
    "SMTP_USE_AUTH",
)


def load_smtp_from_example() -> dict[str, str]:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing {SOURCE}")
    updates: dict[str, str] = {}
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in SMTP_KEYS:
            val = value.strip()
            if key == "SMTP_PASSWORD":
                val = val.replace(" ", "")
            updates[key] = val
    missing = [k for k in SMTP_KEYS if k not in updates]
    if missing:
        raise SystemExit(f"Missing keys in {SOURCE.name}: {', '.join(missing)}")
    return updates


REMOTE_MERGE = r'''
import json
import sys
from pathlib import Path

env_path = sys.argv[1]
patch_path = sys.argv[2]
patch = json.loads(Path(patch_path).read_text(encoding="utf-8"))

lines = Path(env_path).read_text(encoding="utf-8").splitlines()
seen = set()
out = []
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key = line.split("=", 1)[0].strip()
        if key in patch:
            out.append(f"{key}={patch[key]}")
            seen.add(key)
            continue
    out.append(line)
for key, value in patch.items():
    if key not in seen:
        out.append(f"{key}={value}")

Path(env_path).write_text("\n".join(out) + "\n", encoding="utf-8")
print("merged_keys", ",".join(sorted(patch.keys())))
'''


def main() -> int:
    patch = load_smtp_from_example()
    print("Syncing SMTP settings to production", ENV_PATH)
    for key in SMTP_KEYS:
        if key == "SMTP_PASSWORD":
            print(f"  {key}=***")
        else:
            print(f"  {key}={patch[key]}")

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
    remote_py = "/tmp/prod_merge_smtp_env.py"
    remote_patch = "/tmp/prod_smtp_patch.json"
    with sftp.open(remote_py, "w") as f:
        f.write(REMOTE_MERGE)
    with sftp.open(remote_patch, "w") as f:
        f.write(json.dumps(patch))
    sftp.close()

    cmd = f"sudo python3 {remote_py} {ENV_PATH} {remote_patch}"
    print(ssh_run(client, cmd))

    print(ssh_run(client, "sudo systemctl restart indcool-api && sleep 2 && sudo systemctl is-active indcool-api"))
    client.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
