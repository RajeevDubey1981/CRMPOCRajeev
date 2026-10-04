"""Open SSH tunnel to production MySQL for MySQL Workbench.

Uses the same SSH settings as deploy.py (scripts/deploy.env).

Usage (from project root):
  py scripts/prod_mysql_tunnel.py

Optional:
  py scripts/prod_mysql_tunnel.py --local-port 3307
  set INDCOOL_TUNNEL_LOCAL_PORT=3308 && py scripts/prod_mysql_tunnel.py

Leave this running. Workbench: Standard TCP/IP, 127.0.0.1, local port below,
MySQL user/password from MYSQL_DATABASE_URL on the server (not SSH password).
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import select
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

if TYPE_CHECKING:
    import paramiko

DEFAULT_LOCAL_PORT = 3307
REMOTE_MYSQL_HOST = "127.0.0.1"
REMOTE_MYSQL_PORT = 3306
REMOTE_API_ENV = "/var/www/indcool/api/.env"


def ensure_paramiko():
    try:
        import paramiko
    except ImportError:
        print("Installing paramiko...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko
    return paramiko


def port_is_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def parse_mysql_url(url: str) -> tuple[str, str, str]:
    """Return (user, database, host_hint) without exposing password."""
    m = re.match(
        r"mysql\+mysqlconnector://([^:]+):[^@]+@([^:/]+):(\d+)/([^?\s]+)",
        url.strip(),
    )
    if not m:
        return ("?", "indcool", "?")
    user, host, _port, database = m.groups()
    return (user, database, host)


def fetch_mysql_hints(client: paramiko.SSHClient) -> tuple[str, str, str]:
    try:
        raw = ssh_run(
            client,
            f"grep -E '^MYSQL_DATABASE_URL=' {REMOTE_API_ENV} 2>/dev/null | head -1",
            timeout=30,
        )
        line = raw.strip()
        if line.startswith("MYSQL_DATABASE_URL="):
            return parse_mysql_url(line.split("=", 1)[1])
    except Exception as exc:
        print(f"(Could not read remote .env for hints: {exc})")
    return ("indcool_app", "indcool", REMOTE_MYSQL_HOST)


def start_local_forward(
    transport: paramiko.Transport,
    bind_host: str,
    bind_port: int,
    remote_host: str,
    remote_port: int,
) -> socketserver.ThreadingTCPServer:
    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            chan = None
            try:
                chan = transport.open_channel(
                    "direct-tcpip",
                    (remote_host, remote_port),
                    self.request.getpeername(),
                )
            except Exception:
                return
            if chan is None:
                return
            try:
                while True:
                    readers, _, _ = select.select([self.request, chan], [], [], 1.0)
                    if self.request in readers:
                        data = self.request.recv(1024)
                        if not data:
                            break
                        chan.send(data)
                    if chan in readers:
                        data = chan.recv(1024)
                        if not data:
                            break
                        self.request.send(data)
            finally:
                try:
                    chan.close()
                except Exception:
                    pass

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = Server((bind_host, bind_port), Handler)
    thread = threading.Thread(target=server.serve_forever, name="prod-mysql-tunnel", daemon=True)
    thread.start()
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="SSH tunnel to production MySQL")
    parser.add_argument(
        "--local-port",
        type=int,
        default=int(os.environ.get("INDCOOL_TUNNEL_LOCAL_PORT", DEFAULT_LOCAL_PORT)),
        help=f"Local port (default {DEFAULT_LOCAL_PORT})",
    )
    args = parser.parse_args()
    local_port = args.local_port

    if port_is_listening("127.0.0.1", local_port):
        print(f"Port 127.0.0.1:{local_port} is already open (tunnel may already be running).")
        print_workbench_help(local_port, "?", "indcool")
        return 0

    paramiko = ensure_paramiko()
    config = load_config()
    ssh_host = config["INDCOOL_DEPLOY_HOST"]
    ssh_user = config["INDCOOL_DEPLOY_USER"]
    ssh_password = config.get("INDCOOL_DEPLOY_PASSWORD", "")
    if not ssh_password or ssh_password == "YOUR_PASSWORD_HERE":
        ssh_password = getpass.getpass(f"SSH password for {ssh_user}@{ssh_host}: ")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {ssh_host} as {ssh_user}...")
    try:
        client.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=30)
    except Exception as exc:
        print(f"\nSSH connect failed: {exc}")
        print("Fix INDCOOL_DEPLOY_PASSWORD in scripts/deploy.env")
        return 1

    transport = client.get_transport()
    if transport is None or not transport.is_active():
        print("SSH transport not active.")
        client.close()
        return 1

    print(f"Reading MySQL hints from {REMOTE_API_ENV}...")
    db_user, db_name, _ = fetch_mysql_hints(client)

    print(f"\nOpening tunnel 127.0.0.1:{local_port} -> {ssh_host} {REMOTE_MYSQL_HOST}:{REMOTE_MYSQL_PORT}")
    server = start_local_forward(
        transport, "127.0.0.1", local_port, REMOTE_MYSQL_HOST, REMOTE_MYSQL_PORT
    )

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if port_is_listening("127.0.0.1", local_port):
            break
        time.sleep(0.2)
    else:
        print("Tunnel failed to bind locally. Try another --local-port.")
        server.shutdown()
        client.close()
        return 1

    print("\nTunnel is active.")
    print_workbench_help(local_port, db_user, db_name)
    print("\nPress Ctrl+C to close the tunnel.\n")

    try:
        while transport.is_active():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping tunnel...")
    finally:
        server.shutdown()
        client.close()
    return 0


def print_workbench_help(local_port: int, db_user: str, db_name: str) -> None:
    print("")
    print("MySQL Workbench (Standard TCP/IP, not SSH):")
    print("  Hostname:       127.0.0.1")
    print(f"  Port:           {local_port}")
    print(f"  Username:       {db_user}")
    print("  Password:       from MYSQL_DATABASE_URL on server (not SSH password)")
    print(f"  Default schema: {db_name}")


if __name__ == "__main__":
    raise SystemExit(main())
