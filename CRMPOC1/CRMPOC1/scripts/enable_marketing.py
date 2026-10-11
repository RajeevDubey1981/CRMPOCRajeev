"""Switch Marketing on, once, on the production server. You run this yourself:   py scripts/enable_marketing.py

What it does:
  1. Makes a long random password here on your PC. The password is never printed, logged or saved on this PC.
  2. Creates the database `indcool_marketing` and its own MySQL login `indcool_mk` on the server.
  3. Keeps a copy of the server .env as .env.before-marketing, then adds ONE line to it:
     MARKETING_DATABASE_URL=...  (this is the only place the password lives; to see it later, read that line on the server)
  4. Does nothing, and says so, if the line is already there.

It uses the same connection settings as the deploy (scripts/deploy.env). After it finishes, deploy as usual so the
Marketing tables are created and the service restarts.
"""
from __future__ import annotations

import getpass
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (the same settings as the deploy)


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    if not password or password == "YOUR_PASSWORD_HERE":
        password = getpass.getpass(f"SSH password for {user}@{host}: ")
    api = config["REMOTE_API"]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    client.connect(host, username=user, password=password, timeout=30)

    def run_quiet(cmd: str, stdin_text: str | None = None) -> tuple[int, str, str]:
        """Run a command; neither the command nor the text sent to it is printed."""
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        if stdin_text is not None:
            stdin.write(stdin_text)
            stdin.flush()
            stdin.channel.shutdown_write()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        return stdout.channel.recv_exit_status(), out, err

    try:
        _code, out, _ = run_quiet(f"sudo grep -c '^MARKETING_DATABASE_URL=' {api}/.env")
        if out.strip() not in ("", "0"):
            print("MARKETING_DATABASE_URL is already in the server .env: nothing to do.")
            return 0
        secret = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

        code, _, err = run_quiet(f"sudo cp -p {api}/.env {api}/.env.before-marketing")
        if code != 0:
            print(f"Could not keep a copy of .env, so nothing was changed: {err.strip()[:200]}")
            return 1
        print("A copy of the server .env is kept as .env.before-marketing")

        sql = (
            "CREATE DATABASE IF NOT EXISTS indcool_marketing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
            f"CREATE USER IF NOT EXISTS 'indcool_mk'@'localhost' IDENTIFIED BY '{secret}';\n"
            f"ALTER USER 'indcool_mk'@'localhost' IDENTIFIED BY '{secret}';\n"
            "GRANT ALL PRIVILEGES ON indcool_marketing.* TO 'indcool_mk'@'localhost';\n"
            "FLUSH PRIVILEGES;\n"
        )
        code, _, err = run_quiet("sudo mysql", stdin_text=sql)
        if code != 0:
            print(f"The database and login could not be made, .env was not touched: {err.strip()[:300]}")
            return 1
        print("The database indcool_marketing and its login indcool_mk are ready")

        line = f"\nMARKETING_DATABASE_URL=mysql+mysqlconnector://indcool_mk:{secret}@localhost/indcool_marketing\n"
        code, _, err = run_quiet(f"sudo tee -a {api}/.env > /dev/null", stdin_text=line)
        if code != 0:
            print(f"The line could not be added to .env: {err.strip()[:300]}")
            return 1
        _code, out, _ = run_quiet(f"sudo grep -c '^MARKETING_DATABASE_URL=' {api}/.env")
        print(f"Lines named MARKETING_DATABASE_URL in the server .env: {out.strip()}")
        print("\nDone. Now deploy as usual (py scripts/deploy.py) so the Marketing tables are created and the service restarts.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
