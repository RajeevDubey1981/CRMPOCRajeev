"""Validate source changes required by the partner invite deployment."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
ROUTER_FILE = API_DIR / "app" / "routers" / "partner_registrations.py"
UI_FILE = ROOT / "ui" / "src" / "pages" / "partners" / "PartnerRegistrationList.jsx"


def fail(message: str) -> None:
    raise SystemExit(f"Deploy preflight failed: {message}")


def main() -> int:
    if not ROUTER_FILE.is_file():
        fail(f"missing API router: {ROUTER_FILE}")
    if not UI_FILE.is_file():
        fail(f"missing partner registration UI: {UI_FILE}")

    router_source = ROUTER_FILE.read_text(encoding="utf-8")
    ui_source = UI_FILE.read_text(encoding="utf-8")

    try:
        ast.parse(router_source, filename=str(ROUTER_FILE))
    except SyntaxError as exc:
        fail(f"API syntax error: {exc}")

    required_router_markers = (
        'email_in_registration = db.scalar(',
        'email_in_user = db.scalar(',
        'email_in_vendor = db.scalar(',
        'status.HTTP_409_CONFLICT',
    )
    missing_router_markers = [marker for marker in required_router_markers if marker not in router_source]
    if missing_router_markers:
        fail(f"API duplicate guard is incomplete: {', '.join(missing_router_markers)}")

    required_ui_markers = (
        'const [inviteError, setInviteError] = useState("");',
        'setInviteError(Array.isArray(detail)',
        '{inviteError && (',
    )
    missing_ui_markers = [marker for marker in required_ui_markers if marker not in ui_source]
    if missing_ui_markers:
        fail(f"invite modal validation display is incomplete: {', '.join(missing_ui_markers)}")

    python = sys.executable
    result = subprocess.run(
        [python, "-m", "compileall", "-q", str(API_DIR / "app")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        fail("API compile check failed")

    print("Deploy preflight passed: duplicate email/mobile validation is present in API and UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
