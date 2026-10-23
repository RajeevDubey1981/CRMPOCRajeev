"""Show the Marketing database login in YOUR terminal, once:   py scripts/show_marketing_login.py

It reads the MARKETING_DATABASE_URL line from the server .env with the same saved login the deploy uses
(scripts/deploy.env), and prints the database, the login name, the host and the password on your screen only.
Nothing is saved to a file and nothing is sent anywhere else. Copy it into a password manager, then clear the screen.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (the same settings as the deploy)


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    if not config.get("INDCOOL_DEPLOY_PASSWORD"):
        print("scripts/deploy.env has no INDCOOL_DEPLOY_PASSWORD, so this cannot log in.")
        return 1
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(config["INDCOOL_DEPLOY_HOST"], username=config["INDCOOL_DEPLOY_USER"], password=config["INDCOOL_DEPLOY_PASSWORD"], timeout=30)
    try:
        _in, out, _err = client.exec_command(f"sudo grep '^MARKETING_DATABASE_URL=' {config['REMOTE_API']}/.env", timeout=60)
        line = out.read().decode("utf-8", "replace").strip()
    finally:
        client.close()
    if not line:
        print("There is no MARKETING_DATABASE_URL line in the server .env.")
        return 1
    parts = urlsplit(line.split("=", 1)[1])
    print("\nMarketing database login (on the server only; it cannot be reached from the internet)\n")
    print(f"  Database : {parts.path.lstrip('/')}")
    print(f"  Login    : {unquote(parts.username or '')}")
    print(f"  Password : {unquote(parts.password or '')}")
    print(f"  Host     : {parts.hostname}")
    print("\nCopy these into your password manager, then clear this screen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
