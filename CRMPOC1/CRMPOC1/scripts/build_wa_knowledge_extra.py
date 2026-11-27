"""Build api/app/data/wa_knowledge_extra.md from the Word files kept in the Sarvam knowledge bases.

Usage:  py scripts/build_wa_knowledge_extra.py <folder with the .docx files>

Reads AC_Fault_Code_Reference_Unit.docx, INDcool_AC_Model_Directory.docx and INDcool_Full_Product_Directory.docx and writes
the extra knowledge in the same ### block format the WhatsApp assistant's lookup uses. The manual's troubleshooting table
(transcribed by hand from the PDF) is added too. The rate card documents are deliberately NOT used: they hold internal
pricing rules that must never reach customers.
"""
from __future__ import annotations

import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
OUT = Path(__file__).resolve().parent.parent / "api" / "app" / "data" / "wa_knowledge_extra.md"
CHUNK = 2000


def docx_lines(path: Path) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    body = root.find(W + "body")

    def para(p) -> str:
        return "".join(t.text or "" for t in p.iter(W + "t")).strip()

    out: list[str] = []
    for el in body:
        if el.tag == W + "p":
            t = para(el)
            if t:
                out.append(t)
        elif el.tag == W + "tbl":
            for tr in el.iter(W + "tr"):
                cells = [" ".join(para(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")]
                if any(cells):
                    out.append(" | ".join(cells))
    return out


def chunks(lines: list[str], title: str, header: str = "") -> list[str]:
    """Group lines into blocks of about CHUNK characters; every block repeats the table header so it stands alone."""
    blocks, cur = [], []
    size = 0
    for ln in lines:
        if size + len(ln) > CHUNK and cur:
            blocks.append(cur)
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        blocks.append(cur)
    out = []
    for i, b in enumerate(blocks, 1):
        head = f"### {title} (part {i} of {len(blocks)})" if len(blocks) > 1 else f"### {title}"
        out.append(head + "\n\n" + (header + "\n" if header else "") + "\n".join(b))
    return out


GENERAL = """# Extra knowledge (built from the files in the Sarvam knowledge bases)

Source files: AC_Fault_Code_Reference_Unit.docx, INDcool_AC_Model_Directory.docx, INDcool_Full_Product_Directory.docx and the
split AC user manual. Built by scripts/build_wa_knowledge_extra.py.

## How to handle error codes and AC problems on WhatsApp

- Explain what the code or problem means in simple words. Suggest ONLY safe customer steps: switch the AC off at the main
  power, wait 3 minutes, switch on again; clean the air filter; replace the remote controller batteries; keep doors and windows closed.
- Never tell a customer to open the indoor or outdoor unit, touch the wiring or circuit board, measure resistance, or handle
  refrigerant. Technical checks in the explanations below are for the service technician only.
- If the problem is still there after the safe steps, offer to register a service request. Ask for the model, the error code and
  the PIN code. Warranty is decided by the service team, so do not promise a free repair.
- For smoke, a burning smell or sparks, tell the customer to switch the AC off at the main power and hand over to staff.
- Where this extra knowledge and the product pages in the main knowledge differ, prefer the main product pages (newer) and
  offer to confirm with sales.

## Product catalogue
"""

TROUBLE = [
    ("Remote controller not working, indoor unit not receiving the signal",
     "Causes and solutions (split AC user manual):\n- Remote signal interference such as static electricity or unstable voltage: switch the AC off at the main power, pull out the plug, wait 3 minutes, plug in and switch on.\n- Remote out of range or not pointing at the receiver: the range is 8 m, point it at the receiver.\n- Obstacles in between: clear the path.\n- Low remote sensitivity, weak or no display: check the remote batteries and change them if needed.\n- No display on the remote screen: if the remote is damaged, replace it.\n- Fluorescent lamp in the room: bring the remote closer to the indoor unit or switch the fluorescent lamp off."),
    ("No air from the indoor unit",
     "Causes and solutions (split AC user manual):\n- Air inlet or outlet blocked: clear the inlet and outlet and clean the filters.\n- In heating mode the indoor temperature reached the set temperature: the blower switches off, so no air comes out. This is normal.\n- Heating mode was just turned on: the indoor unit starts after a delay of several minutes so it does not blow cold air. This is normal."),
    ("AC unit is not starting",
     "Causes and solutions (split AC user manual):\n- Power failure: check whether there is a power failure at your place.\n- Plug not inserted properly: switch off at the main power, insert the plug properly and start again.\n- Circuit breaker tripped or fuse burnt: ask a professional electrician to replace it.\n- Wiring malfunction: ask a professional electrician to replace or repair the wiring.\n- Unit restarting immediately after stopping: wait 3 minutes, then switch on again.\n- Incorrect function setting on the remote: reset the function."),
    ("Mist blown out of the indoor unit",
     "Cause: indoor temperature and humidity are high. Solution: the room air is cooled quickly, so after a while the temperature and humidity drop and the mist disappears. This is normal (split AC user manual)."),
    ("Not able to adjust the set temperature",
     "Causes and solutions (split AC user manual):\n- The unit is in Auto mode: the temperature cannot be adjusted in Auto mode; switch to another operation mode to set the temperature.\n- The required temperature is outside the range: the set temperature range is 16 to 30 degrees C."),
    ("Cooling or heating effect is not good",
     "Causes and solutions (split AC user manual):\n- Too low voltage: wait for the voltage to become normal, then operate the unit.\n- Dirty filter: clean the filter.\n- Set temperature not in the proper range: adjust it.\n- Leaks in the room: close all doors and windows."),
    ("Odour coming from the indoor unit",
     "Cause: an odour source nearby such as cigarette smoke. Solution: remove the odour source and clean the filter (split AC user manual)."),
    ("Abnormal behaviour of the AC unit",
     "Cause: interference such as thunder or wireless devices. Solution: switch off the power, remove the plug, wait 3 minutes, insert the plug and switch the AC on again (split AC user manual)."),
    ("Vapour from the outdoor unit",
     "Cause: heating mode is on. During defrosting in heating mode the AC may produce vapour; this is a normal phenomenon (split AC user manual)."),
    ("Water flowing sound",
     "Cause: heard when the AC is switched on or off. It is the sound of refrigerant flowing and is normal (split AC user manual). Note: the manual's own wording for this item is mixed; if the customer reports actual water leaking, offer a service request."),
    ("Cracking noise",
     "Cause: heard when the AC is switched on or off. It is the sound of friction of plastic parts caused by expansion and contraction of panels or other parts when the temperature changes. It is normal (split AC user manual)."),
]


def build(src: Path) -> str:
    parts = [GENERAL]

    # error codes
    fault = docx_lines(src / "AC_Fault_Code_Reference_Unit.docx")
    parts.append("## Split AC error codes\n")
    for ln in fault:
        cells = [c.strip() for c in ln.split(" | ")]
        if len(cells) >= 6 and cells[0].isdigit():
            _, odu, idu, unit, name, expl = cells[0], cells[1], cells[2], cells[3], cells[4], " | ".join(cells[5:])
            parts.append(
                f"### Split AC error code {idu}: {name}\n\n"
                f"- Error code shown on the indoor unit display: {idu} (outdoor unit light flashes: {odu})\n"
                f"- Unit: {unit}\n- Meaning: {name}\n- Details for the technician: {expl}"
            )

    # troubleshooting from the manual
    parts.append("## Split AC troubleshooting (user manual)\n")
    for title, body in TROUBLE:
        parts.append(f"### Split AC problem: {title}\n\n{body}")

    # model directory
    model = docx_lines(src / "INDcool_AC_Model_Directory.docx")
    head = next((l for l in model if l.startswith("Model Number |")), "")
    rows = [l for l in model if re.match(r"^IDC[A-Z0-9]+ \|", l)]
    parts.append("## AC model guide by room (older compilation, 20 Aug 2026)\n")
    parts += chunks(rows, "AC model directory: model, series, tonnage, stars, type and best-for rooms", head)

    # full product directory
    full = docx_lines(src / "INDcool_Full_Product_Directory.docx")
    keep = [l for l in full if "voice AI" not in l and "GeM" not in l and not l.lower().startswith("source:")]
    parts.append("## Product directory by category (older compilation, 20 Aug 2026)\n")
    parts += chunks(keep, "Product directory: models by category with capacity, star rating and key spec")
    return "\n\n".join(parts) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    text = build(Path(sys.argv[1]))
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(text):,} characters, {text.count(chr(10) + '### ')} blocks)")
