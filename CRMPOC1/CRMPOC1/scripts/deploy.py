"""Interactive deploy: native local startup or production UI/API deployment.

Usage (from project root):
  py scripts/deploy.py

Config: scripts/deploy.env (copy from scripts/deploy.env.example)
"""
from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
UI_DIST = UI_DIR / "dist"
API_DIR = ROOT / "api"
CONFIG_FILE = Path(__file__).resolve().parent / "deploy.env"
ROOT_ENV_FILE = ROOT / ".env"

API_SKIP_DIRS = {"venv", "__pycache__", ".pytest_cache", ".mypy_cache", "uploads", ".git"}
API_SKIP_FILES = {".env", ".env.local", "uvicorn.stdout.log"}
API_SKIP_SUFFIXES = {".log", ".pyc", ".pyo"}


def load_config() -> dict[str, str]:
    config: dict[str, str] = {
        "INDCOOL_DEPLOY_HOST": "97.74.83.211",
        "INDCOOL_DEPLOY_USER": "indcooladmin",
        "INDCOOL_DEPLOY_PASSWORD":"JAdJh@yg4SFDP#!nGH",
        "REMOTE_API": "/var/www/indcool/api",
        "REMOTE_UI": "/var/www/indcool/ui",
    }
    if CONFIG_FILE.is_file():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    for key in config:
        env_val = os.environ.get(key)
        if env_val:
            config[key] = env_val
    return config


def run_local(cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    print(f"\n> {' '.join(cmd)}")
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check, env=run_env)


def stop_port_processes(ports: tuple[int, ...]) -> None:
    """Stop processes holding local deployment ports before starting Docker."""
    if sys.platform == "win32":
        netstat = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids: set[str] = set()
        for line in netstat.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[3] != "LISTENING":
                continue
            local_address = parts[1]
            if any(local_address.endswith(f":{port}") for port in ports):
                pids.add(parts[4])
        for pid in sorted(pids):
            print(f"Stopping process {pid} holding a local deployment port")
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], check=False, capture_output=True)
        return

    for port in ports:
        if shutil.which("fuser"):
            subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False)
        elif shutil.which("lsof"):
            result = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"],
                capture_output=True,
                text=True,
                check=False,
            )
            for pid in result.stdout.split():
                subprocess.run(["kill", "-9", pid], check=False)


def wait_for_http(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status < 400:
                    return
        except Exception as exc:  # Service startup is expected to fail briefly.
            last_error = exc
        time.sleep(1)
    raise SystemExit(f"Timed out waiting for {url}: {last_error}")


def load_root_env() -> dict[str, str]:
    env = os.environ.copy()
    if not ROOT_ENV_FILE.is_file():
        return env
    for raw_line in ROOT_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    if env.get("MYSQL_DATABASE_URL"):
        env["MYSQL_DATABASE_URL"] = env["MYSQL_DATABASE_URL"].replace("host.docker.internal", "127.0.0.1")
    env.update(
        {
            "API_PORT": "8010",
            "UI_PORT": "5173",
            "CORS_ORIGINS": "http://localhost:5173",
            "APP_PUBLIC_URL": "http://localhost:5173",
            "VITE_API_BASE_URL": "http://localhost:8010",
        }
    )
    return env


def start_local_process(cmd: list[str], cwd: Path, env: dict[str, str], label: str) -> None:
    print(f"Starting {label}: {' '.join(cmd)}")
    kwargs: dict[str, object] = {"cwd": cwd, "env": env}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(cmd, **kwargs)


def npm_executable() -> str:
    if sys.platform == "win32":
        return "npm.cmd"
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found. Install Node.js and try again.")
    return npm


def python_executable() -> str:
    if sys.platform == "win32":
        for candidate in ("py", "python", "python3"):
            if shutil.which(candidate):
                return candidate
    py = shutil.which("python3") or shutil.which("python")
    if not py:
        raise SystemExit("Python not found.")
    return py


def build_ui(*, for_production: bool = False) -> None:
    print("\n=== Build UI (production) ===")
    npm = npm_executable()
    if not (UI_DIR / "node_modules").is_dir():
        run_local([npm, "install"], cwd=UI_DIR)
    build_env: dict[str, str] = {}
    if for_production:
        # .env.local overrides .env.production during vite build; force same-origin API.
        build_env["VITE_API_BASE_URL"] = ""
    run_local([npm, "run", "build", "--", "--mode", "production"], cwd=UI_DIR, env=build_env)
    if not UI_DIST.is_dir():
        raise SystemExit(f"UI build failed: {UI_DIST} not found")
    print(f"UI build OK -> {UI_DIST}")


def deploy_local() -> None:
    print("\n=== Local deploy (native: UI 5173 / API 8010) ===")
    local_env = load_root_env()

    print("\n=== Stop existing local services ===")
    stop_port_processes((5173, 8010))

    api_python = API_DIR / ("venv\\Scripts\\python.exe" if sys.platform == "win32" else "venv/bin/python")
    if not api_python.is_file():
        raise SystemExit(f"API virtual environment not found: {api_python}")
    if not (UI_DIR / "node_modules").is_dir():
        run_local([npm_executable(), "install"], cwd=UI_DIR, env=local_env)

    print("\n=== Local database migrations ===")
    run_local([str(api_python), "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=API_DIR, env=local_env)
    print("\n=== Local seed (safe bootstrap) ===")
    run_local([str(api_python), "-m", "app.seed"], cwd=API_DIR, env=local_env, check=False)

    start_local_process(
        [str(api_python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8010"],
        API_DIR,
        local_env,
        "API",
    )
    start_local_process(
        [npm_executable(), "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        UI_DIR,
        local_env,
        "UI",
    )
    print("\n=== Verify local services ===")
    wait_for_http("http://localhost:8010/health")
    wait_for_http("http://localhost:5173")
    print("\nLocal deploy complete.")
    print("  UI:  http://localhost:5173")
    print("  API: http://localhost:8010/docs")


def iter_api_files() -> list[Path]:
    files: list[Path] = []
    for path in API_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(API_DIR).parts
        if any(part in API_SKIP_DIRS for part in rel_parts):
            continue
        if path.name in API_SKIP_FILES:
            continue
        if path.suffix in API_SKIP_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def ssh_run(client, cmd: str) -> str:
    _, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        out += "\nSTDERR: " + err
    return out


def upload_file(sftp, client, local: Path, remote: str) -> None:
    tmp = f"/tmp/indcool_deploy_{local.name}"
    sftp.put(str(local), tmp)
    ssh_run(client, f"sudo mkdir -p $(dirname {remote}) && sudo cp {tmp} {remote} && sudo rm -f {tmp}")


def deploy_api_remote(sftp, client, remote_api: str) -> None:
    print("\n=== Deploy API to production ===")
    files = iter_api_files()
    print(f"  {len(files)} files")
    for idx, local in enumerate(files, start=1):
        rel = local.relative_to(API_DIR).as_posix()
        remote = f"{remote_api}/{rel}"
        if idx % 50 == 0 or idx == len(files):
            print(f"  [{idx}/{len(files)}] {rel}")
        upload_file(sftp, client, local, remote)


def deploy_ui_remote(sftp, client, remote_ui: str) -> None:
    print("\n=== Deploy UI to production ===")
    count = 0
    for root_dir, _dirs, files in os.walk(UI_DIST):
        rel = Path(root_dir).relative_to(UI_DIST)
        remote_dir = remote_ui if rel == Path(".") else f"{remote_ui}/{rel.as_posix()}"
        ssh_run(client, f"sudo mkdir -p {remote_dir}")
        for name in files:
            local_path = Path(root_dir) / name
            remote_path = f"{remote_dir}/{name}"
            upload_file(sftp, client, local_path, remote_path)
            ssh_run(client, f"sudo chown www-data:www-data {remote_path}")
            count += 1
    print(f"  {count} files uploaded")


def deploy_database_remote(client, remote_api: str) -> None:
    print("\n=== Production database migrations ===")
    remote_migrate = r"""
import os, subprocess
from pathlib import Path
for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()
os.chdir("/var/www/indcool/api")
subprocess.run(["/var/www/indcool/api/venv/bin/alembic", "-c", "alembic.ini", "current"], check=False)
subprocess.run(["/var/www/indcool/api/venv/bin/alembic", "-c", "alembic.ini", "upgrade", "head"], check=True)
""".replace("/var/www/indcool/api", remote_api)
    ssh_run(client, f"cat > /tmp/indcool_migrate.py <<'PY'\n{remote_migrate}\nPY")
    print(ssh_run(client, f"sudo -u www-data {remote_api}/venv/bin/python /tmp/indcool_migrate.py"))

    print("\n=== Production seed (safe bootstrap) ===")
    print(ssh_run(
        client,
        f"sudo -u www-data bash -lc 'cd {remote_api} && "
        f"export $(grep -E ^DATABASE_BACKEND= .env | xargs) "
        f"$(grep -E ^MYSQL_DATABASE_URL= .env | xargs) && "
        f"venv/bin/python -m app.seed'",
    ))


def restart_production_services(client) -> None:
    print("\n=== Restart API service ===")
    print(ssh_run(client, "sudo systemctl restart indcool-api && sleep 2 && sudo systemctl is-active indcool-api"))
    print("\n=== Reload nginx ===")
    print(ssh_run(client, "sudo nginx -t && sudo systemctl reload nginx"))


def verify_production(client, remote_api: str) -> None:
    print("\n=== Verify production ===")
    print(ssh_run(client, f"curl -s -o /dev/null -w 'health:%{{http_code}}\\n' http://127.0.0.1:8000/health"))
    print(ssh_run(client, "curl -s -o /dev/null -w 'site:%{http_code}\\n' http://127.0.0.1/"))


def deploy_production(config: dict[str, str]) -> None:
    try:
        import paramiko
    except ImportError:
        py = python_executable()
        print("Installing paramiko...")
        subprocess.run([py, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko

    host = config["INDCOOL_DEPLOY_HOST"]
    user = config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    remote_api = config["REMOTE_API"]
    remote_ui = config["REMOTE_UI"]

    if not password or password == "YOUR_PASSWORD_HERE":
        password = getpass.getpass(f"SSH password for {user}@{host}: ")

    build_ui(for_production=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\nConnecting to {host} as {user}...")
    client.connect(host, username=user, password=password, timeout=30)
    sftp = client.open_sftp()
    try:
        deploy_api_remote(sftp, client, remote_api)
        deploy_ui_remote(sftp, client, remote_ui)
        deploy_database_remote(client, remote_api)
        restart_production_services(client)
        verify_production(client, remote_api)
    finally:
        sftp.close()
        client.close()

    print("\nProduction deploy complete.")
    print(f"  Site: https://indcoolappliances.com (server: {host})")


def prompt_target() -> str:
    print("\nIndcool CRM — Deploy")
    print("====================")
    print("  1) Local   (native API 8010 + UI 5173 + DB migrations)")
    print("  2) Production (UI build + API upload + DB migrations + restart)")
    print("  q) Quit")
    while True:
        choice = input("\nWhere do you want to deploy? [1/2/q]: ").strip().lower()
        if choice in {"1", "local", "l"}:
            return "local"
        if choice in {"2", "production", "prod", "p"}:
            return "production"
        if choice in {"q", "quit", "exit"}:
            raise SystemExit(0)
        print("Invalid choice. Enter 1, 2, or q.")


def ensure_config_hint() -> None:
    if not CONFIG_FILE.is_file():
        example = CONFIG_FILE.with_suffix(".env.example")
        print(f"\nNote: create {CONFIG_FILE.name} from {example.name} to store production SSH settings.")


def main() -> int:
    ensure_config_hint()
    config = load_config()
    target = prompt_target()
    if target == "local":
        deploy_local()
    else:
        deploy_production(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
