#!/usr/bin/env python3
"""Fix the INDcool website product page: the picture strip (multi view), zoom and quantity buttons are dead.

Cause: a Facebook Pixel snippet (<script> ... </script>) was pasted INSIDE the main product script, under the comment
"ADD TO CART". The browser ends the main script at that first </script>, so everything after it never runs.

This moves the pixel snippet to just AFTER the main script's closing </script>, as its own script block.

Run it on the website server (the one that serves indcool.in), in the folder of the Laravel site:

    python3 website_fix_product_pixel.py /path/to/site            # shows what it would change, writes nothing
    python3 website_fix_product_pixel.py /path/to/site --apply    # backs the file up, then writes the change

It looks in resources/views for a template that has the problem. Each changed file gets a copy named file.bak-YYYYMMDD-HHMMSS.
"""

from __future__ import annotations

import difflib
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# the comment, then a nested <script>...</script> block, inside the main script
BROKEN = re.compile(r"(/\*\s*=+\s*ADD TO CART\s*=+\s*\*/[ \t]*\r?\n)(\s*<script>.*?</script>[ \t]*\r?\n)", re.S)


def fix(text: str) -> tuple[str, bool]:
    m = BROKEN.search(text)
    if not m:
        return text, False
    pixel = m.group(2).strip("\r\n")
    without = text[: m.start(2)] + text[m.end(2):]
    close = without.find("</script>", m.start())
    if close < 0:
        raise SystemExit("Found the pixel block but not the end of the main script: stopping, nothing was changed")
    after = close + len("</script>")
    return without[:after] + "\n\n" + pixel + "\n" + without[after:], True


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if not args:
        raise SystemExit(__doc__)
    site = Path(args[0])
    views = site / "resources" / "views"
    if not views.is_dir():
        raise SystemExit(f"{views} not found. Give the folder of the Laravel site (the one that has artisan)")
    found = 0
    for path in sorted(views.rglob("*.php")):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if "ADD TO CART" not in text:
            continue
        new, changed = fix(text)
        if not changed:
            continue
        found += 1
        print(f"\n=== {path}")
        for line in difflib.unified_diff(text.splitlines(), new.splitlines(), "before", "after", lineterm="", n=2):
            print(line)
        if apply:
            backup = path.with_name(path.name + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            shutil.copy2(path, backup)
            path.write_text(new, encoding="utf-8", errors="surrogateescape")
            print(f"\nWritten. Backup: {backup}")
    if not found:
        print("No template with the problem was found (nothing to change).")
        return
    if apply:
        artisan = site / "artisan"
        if artisan.exists():
            subprocess.run(["php", str(artisan), "view:clear"], cwd=site, check=False)
        print("\nDone. Open a product page, press Ctrl+F5: the picture strip under the big picture should show.")
    else:
        print("\nThis was a preview. Nothing was changed. Add --apply to write it.")


if __name__ == "__main__":
    main()
