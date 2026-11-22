"""Send the SMS settings to the server, once:   py scripts/set_sms_config.py

Reads scripts/sms-config.env (you fill it in; it is ignored by git) and sets the filled-in lines in the server .env.
Empty lines are skipped and any older value of the same name is replaced. A copy of the server .env is kept as
.env.before-sms first, the values are never printed, and the API service is restarted so it picks them up.
Same connection settings as the deploy (scripts/deploy.env).
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

SRC = Path(__file__).resolve().parent / "sms-config.env"
KEYS = (
    "SMS_ENABLED", "SMS_USER", "SMS_PASSWORD", "SMS_SENDER_ID", "SMS_PE_ID",
    "SMS_HAPPY_CODE_TEMPLATE_ID", "SMS_EMAIL_LINK_TEMPLATE_ID", "SMS_CHANNEL", "SMS_ROUTE",
)
SAFE_RE = re.compile(r"[^\s\"'`$\;&|<>]{1,200}")  # one word, nothing the shell or .env could misread


def read_values() -> dict[str, str]:
    if not SRC.is_file():
        raise SystemExit(f"{SRC.name} is not in the scripts folder. Nothing was changed.")
    values: dict[str, str] = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if key.strip() in KEYS and value:
            values[key.strip()] = value
    return values


def main() -> int:
    values = read_values()
    if not values:
        print("Nothing is filled in yet in sms-config.env. Nothing was changed.")
        return 1
    bad = [k for k, v in values.items() if not SAFE_RE.fullmatch(v)]
    if bad:
        print("Nothing was changed. These look wrong (spaces or special characters): " + ", ".join(bad))
        return 1
    if values.get("SMS_ENABLED", "false").lower() == "true":
        missing = [k for k in ("SMS_USER", "SMS_PASSWORD", "SMS_SENDER_ID", "SMS_PE_ID") if k not in values]
        if missing:
            print("SMS_ENABLED is true but these are empty: " + ", ".join(missing) + ". Nothing was changed.")
            return 1

    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1
    host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD", "") or getpass.getpass(f"SSH password for {user}@{host}: ")
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
        code, _, err = run_quiet(f"sudo cp -p {api}/.env {api}/.env.before-sms")
        if code != 0:
            print(f"Could not keep a copy of .env, so nothing was changed: {err.strip()[:200]}")
            return 1
        print("A copy of the server .env is kept as .env.before-sms")
        pattern = " ".join(f"-e '/^{k}=/d'" for k in values)
        run_quiet(f"sudo sed -i {pattern} {api}/.env")
        body = "\n" + "".join(f"{k}={v}\n" for k, v in values.items())
        code, _, err = run_quiet(f"sudo tee -a {api}/.env > /dev/null", stdin_text=body)
        if code != 0:
            print(f"The settings could not be added: {err.strip()[:200]}")
            return 1
        print(f"Set {len(values)} SMS line(s): " + ", ".join(values))
        deploy.restart_production_services(client)
        print("\nDone.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
