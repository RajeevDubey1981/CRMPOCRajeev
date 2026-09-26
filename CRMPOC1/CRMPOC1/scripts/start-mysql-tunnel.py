"""Start local SSH tunnel to production MySQL (127.0.0.1:3307 -> server:3306)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PORT = 3307
REMOTE_MYSQL = "127.0.0.1:3306"
PLINK = Path(r"C:\Program Files\PuTTY\plink.exe")

spec = importlib.util.spec_from_file_location("deploy", ROOT / "scripts" / "deploy.py")
deploy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deploy)

cfg = deploy.load_config()
host = cfg["INDCOOL_DEPLOY_HOST"]
user = cfg["INDCOOL_DEPLOY_USER"]
password = cfg.get("INDCOOL_DEPLOY_PASSWORD", "")

if not PLINK.is_file():
    print("PuTTY plink.exe not found. Install PuTTY or use: ssh -N -L 3307:127.0.0.1:3306 user@host", file=sys.stderr)
    sys.exit(1)

target = f"{user}@{host}"
cmd = [
    str(PLINK),
    "-batch",
    "-N",
    "-L",
    f"{LOCAL_PORT}:{REMOTE_MYSQL}",
    target,
    "-pw",
    password,
]
background = "--background" in sys.argv
print(f"Tunnel: localhost:{LOCAL_PORT} -> {host} MySQL")
print("Workbench: Standard TCP/IP, Host 127.0.0.1, Port 3307")
if background:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    print(f"Started in background (PID {proc.pid}). Stop with: taskkill /PID {proc.pid} /F")
else:
    print("Leave this window open. Press Ctrl+C to stop.")
    subprocess.run(cmd, check=True)
