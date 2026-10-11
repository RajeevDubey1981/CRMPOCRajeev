"""Store the Meta app keys on the server, once:   py scripts/set_meta_keys.py

You paste two values from developers.facebook.com, your app, App settings, Basic:
  * the App ID (a number),
  * the App Secret (press Show there). It is asked without showing it on screen.
They are added to the server .env as META_APP_ID and META_APP_SECRET. A copy of the .env is kept as .env.before-meta first,
the secret is never printed or saved on this PC, and the API service is restarted so it picks the keys up.
It uses the same connection settings as the deploy (scripts/deploy.env).
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (the same settings and the same restart as the deploy)


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    app_id = input("Meta App ID (digits): ").strip()
    if not re.fullmatch(r"\d{8,20}", app_id):
        print("The App ID is only digits, 8 to 20 of them. Nothing was changed.")
        return 1
    secret = getpass.getpass("Meta App Secret (hidden as you paste): ").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{20,64}", secret):
        print("That does not look like an App Secret (letters a-f and digits, 20 to 64 of them). Nothing was changed.")
        return 1

    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    if not password:
        password = getpass.getpass(f"SSH password for {user}@{host}: ")
    api = config["REMOTE_API"]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    client.connect(host, username=user, password=password, timeout=30)

    def run_quiet(cmd: str, stdin_text: str | None = None) -> tuple[int, str, str]:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        if stdin_text is not None:
            stdin.write(stdin_text)
            stdin.flush()
            stdin.channel.shutdown_write()
        return stdout.channel.recv_exit_status(), stdout.read().decode("utf-8", "replace"), stderr.read().decode("utf-8", "replace")

    try:
        code, _, err = run_quiet(f"sudo cp -p {api}/.env {api}/.env.before-meta")
        if code != 0:
            print(f"Could not keep a copy of .env, so nothing was changed: {err.strip()[:200]}")
            return 1
        print("A copy of the server .env is kept as .env.before-meta")
        run_quiet(f"sudo sed -i -e '/^META_APP_ID=/d' -e '/^META_APP_SECRET=/d' {api}/.env")  # replace an older pair, if any
        code, _, err = run_quiet(f"sudo tee -a {api}/.env > /dev/null", stdin_text=f"\nMETA_APP_ID={app_id}\nMETA_APP_SECRET={secret}\n")
        if code != 0:
            print(f"The keys could not be added: {err.strip()[:200]}")
            return 1
        _c, out, _ = run_quiet(f"sudo grep -c -E '^META_APP_(ID|SECRET)=' {api}/.env")
        print(f"Meta lines in the server .env: {out.strip()} (should be 2)")
        deploy.restart_production_services(client)
        print("\nDone. Open Marketing, Channels, and press Connect Meta.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
