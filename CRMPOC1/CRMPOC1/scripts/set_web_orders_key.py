"""Switch on the Web Orders sync on the CRM server, once:   py scripts/set_web_orders_key.py

Makes a new random key, puts it in the CRM server .env as WEB_ORDERS_INGEST_KEY (a copy of .env is kept as
.env.before-web-orders first) and restarts the API. The same key is saved on this computer in scripts/web-orders-sync.env
(ignored by git) so the sync script on the website server can be given it. The key is never printed.
Run it again to replace the key (the website script must then be given the new one).
Same connection settings as the deploy (scripts/deploy.env).
"""
from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

OUT = Path(__file__).resolve().parent / "web-orders-sync.env"
CRM_URL = "https://indcoolapplainces.com"  # spelled this way on purpose: it is the real domain


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "") or getpass.getpass(f"SSH password for {user}@{host}: ")
    api = config["REMOTE_API"]
    key = secrets.token_urlsafe(40)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    client.connect(host, username=user, password=password, timeout=30)

    def run(cmd: str, stdin_text: str | None = None) -> tuple[int, str]:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        if stdin_text is not None:
            stdin.write(stdin_text)
            stdin.flush()
            stdin.channel.shutdown_write()
        return stdout.channel.recv_exit_status(), stderr.read().decode("utf-8", "replace")

    try:
        code, err = run(f"sudo cp -p {api}/.env {api}/.env.before-web-orders")
        if code != 0:
            print(f"Could not keep a copy of .env, so nothing was changed: {err.strip()[:200]}")
            return 1
        run(f"sudo sed -i -e '/^WEB_ORDERS_INGEST_KEY=/d' {api}/.env")
        code, err = run(f"sudo tee -a {api}/.env > /dev/null", stdin_text=f"\nWEB_ORDERS_INGEST_KEY={key}\n")
        if code != 0:
            print(f"The key could not be added: {err.strip()[:200]}")
            return 1
        OUT.write_text(f"CRM_URL={CRM_URL}\nCRM_KEY={key}\n", encoding="utf-8")
        print("The key is set on the server and saved in scripts/web-orders-sync.env (not shown here).")
        deploy.restart_production_services(client)
        print("\nDone. Now the sync script on the website server can be given the key.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
