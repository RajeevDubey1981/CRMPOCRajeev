"""One-off: create the indcool_parts database + user on the server, add PARTS_DATABASE_URL to the server's api/.env,
migrate the Parts schema, and restart the API. Safe to re-run (every step is idempotent).

The password is generated here and never printed or sent anywhere except the server's own .env file; this script
never shows it to you. If you ever need it, read it on the server: sudo grep PARTS_DATABASE_URL /var/www/indcool/api/.env

Usage (from the project root):  py scripts/setup_parts_db.py
"""
from __future__ import annotations

import secrets
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

REMOTE_API = "/var/www/indcool/api"


def main() -> int:
    config = deploy.load_config()
    try:
        import paramiko
    except ImportError:
        print("Install paramiko first:  py -m pip install paramiko")
        return 1

    password = secrets.token_urlsafe(24)

    with tempfile.TemporaryDirectory() as tmp:
        sql_path = Path(tmp) / "parts_create.sql"
        sql_path.write_text(
            "CREATE DATABASE IF NOT EXISTS indcool_parts CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
            f"CREATE USER IF NOT EXISTS 'indcool_pt'@'localhost' IDENTIFIED BY '{password}';\n"
            f"ALTER USER 'indcool_pt'@'localhost' IDENTIFIED BY '{password}';\n"  # idempotent: fixes the password if the user already existed
            "GRANT ALL PRIVILEGES ON indcool_parts.* TO 'indcool_pt'@'localhost';\n"
            "FLUSH PRIVILEGES;\n",
            encoding="utf-8",
        )
        env_path = Path(tmp) / "parts_env_line.txt"
        env_path.write_text(
            f"\nPARTS_DATABASE_URL=mysql+mysqlconnector://indcool_pt:{password}@localhost/indcool_parts\n",
            encoding="utf-8",
        )

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host, user = config["INDCOOL_DEPLOY_HOST"], config["INDCOOL_DEPLOY_USER"]
        print(f"Connecting to {host} as {user}...")
        client.connect(host, username=user, password=config.get("INDCOOL_DEPLOY_PASSWORD", ""), timeout=30)
        sftp = client.open_sftp()
        try:
            run = deploy.ssh_run

            print("\n=== Create indcool_parts database + user ===")
            sftp.put(str(sql_path), "/tmp/indcool_parts_create.sql")
            run(client, "sudo mysql < /tmp/indcool_parts_create.sql && sudo rm -f /tmp/indcool_parts_create.sql")
            run(client, "sudo mysql -N -e \"SHOW DATABASES LIKE 'indcool_parts'\"")

            print("\n=== Add PARTS_DATABASE_URL to the server .env ===")
            already = run(client, f"sudo grep -c '^PARTS_DATABASE_URL=' {REMOTE_API}/.env || true").strip().splitlines()[-1].strip()
            if already == "0":
                sftp.put(str(env_path), "/tmp/indcool_parts_env_line.txt")
                run(client, f"sudo bash -c 'cat /tmp/indcool_parts_env_line.txt >> {REMOTE_API}/.env' && sudo rm -f /tmp/indcool_parts_env_line.txt")
                print("PARTS_DATABASE_URL appended.")
            else:
                print("PARTS_DATABASE_URL already present in .env; leaving it as is (not overwriting).")

            deploy.deploy_database_remote(client, REMOTE_API, seed_demo_data=False)
            deploy.restart_production_services(client)
            deploy.verify_production(client, REMOTE_API, config["REMOTE_UI"])

            print("\n=== Parts tables ===")
            run(client, "sudo mysql -N indcool_parts -e 'SHOW TABLES'")
        finally:
            sftp.close()
            client.close()

    print("\nindcool_parts is set up and switched on. The password lives only in the server's api/.env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
