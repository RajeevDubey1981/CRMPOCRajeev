"""Send the Sarvam recording settings to the server, once:   py scripts/set_sarvam_recording_keys.py

Reads scripts/sarvam-recording.env (you fill it in; it is ignored by git) and adds these to the server .env:
SARVAM_ORG_ID, SARVAM_WORKSPACE_ID, SARVAM_APP_ID, SARVAM_WORKSPACE_API_KEY and, if you filled it,
SARVAM_WEBHOOK_SECRET. A copy of the server .env is kept as .env.before-sarvam-recording first, the values are
never printed, and the API service is restarted so it picks them up. Same connection settings as the deploy
(scripts/deploy.env).
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402  (the same settings and the same restart as the deploy)

SRC = Path(__file__).resolve().parent / "sarvam-recording.env"
REQUIRED = ("SARVAM_ORG_ID", "SARVAM_WORKSPACE_ID", "SARVAM_APP_ID", "SARVAM_WORKSPACE_API_KEY")
OPTIONAL = ("SARVAM_WEBHOOK_SECRET",)
ID_RE = re.compile(r"[A-Za-z0-9_.\-]{3,120}")
SECRET_RE = re.compile(r"\S{8,300}")


def read_values() -> dict[str, str]:
    if not SRC.is_file():
        raise SystemExit(f"{SRC.name} is not in the scripts folder. Nothing was changed.")
    values: dict[str, str] = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    values = read_values()
    problems = []
    for key in REQUIRED:
        v = values.get(key, "")
        ok = ID_RE.fullmatch(v) if key != "SARVAM_WORKSPACE_API_KEY" else SECRET_RE.fullmatch(v)
        if not ok:
            problems.append(key + (" is empty" if not v else " does not look right"))
    if values.get("SARVAM_WEBHOOK_SECRET") and not SECRET_RE.fullmatch(values["SARVAM_WEBHOOK_SECRET"]):
        problems.append("SARVAM_WEBHOOK_SECRET does not look right")
    if problems:
        print("Nothing was changed. Fix in sarvam-recording.env: " + "; ".join(problems))
        return 1
    keys = [k for k in REQUIRED + OPTIONAL if values.get(k)]

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
        code, _, err = run_quiet(f"sudo cp -p {api}/.env {api}/.env.before-sarvam-recording")
        if code != 0:
            print(f"Could not keep a copy of .env, so nothing was changed: {err.strip()[:200]}")
            return 1
        print("A copy of the server .env is kept as .env.before-sarvam-recording")
        pattern = " ".join(f"-e '/^{k}=/d'" for k in REQUIRED + OPTIONAL)  # replace older values, if any
        run_quiet(f"sudo sed -i {pattern} {api}/.env")
        body = "\n" + "".join(f"{k}={values[k]}\n" for k in keys)
        code, _, err = run_quiet(f"sudo tee -a {api}/.env > /dev/null", stdin_text=body)
        if code != 0:
            print(f"The settings could not be added: {err.strip()[:200]}")
            return 1
        _c, out, _ = run_quiet(f"sudo grep -c -E '^SARVAM_(ORG_ID|WORKSPACE_ID|APP_ID|WORKSPACE_API_KEY|WEBHOOK_SECRET)=' {api}/.env")
        print(f"Sarvam recording lines in the server .env: {out.strip()} (should be {len(keys)})")
        deploy.restart_production_services(client)
        print("\nDone. Set the webhook in Sarvam to https://indcoolapplainces.com/api/sarvam/call-completed")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
