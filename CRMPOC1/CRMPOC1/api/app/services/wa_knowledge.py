"""The knowledge the WhatsApp assistant may use (app/data/wa_knowledge.md and wa_knowledge_extra.md).

The files are big (a whole product catalogue, error codes, troubleshooting), the model's memory is not. So the general rules
and policies at the top are always sent, and only the few blocks that match the customer's words are added.
"""
from __future__ import annotations

import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
KNOWLEDGE_FILE = DATA / "wa_knowledge.md"
EXTRA_FILE = DATA / "wa_knowledge_extra.md"
HEAD_LIMIT = 14000
PRODUCT_LIMIT = 7000
PER_PRODUCT = 2200
MAX_PRODUCTS = 5

_CACHE: dict = {"mtime": None, "head": "", "products": []}
_STOP = {"the", "and", "for", "with", "you", "your", "are", "this", "that", "what", "which", "have", "has", "can", "any",
         "how", "much", "price", "cost", "please", "hai", "kya", "ka", "ki", "ke", "mera", "meri", "hello", "need", "want",
         "tell", "about", "model"}
# AC error codes are short (E6, F1, P4, EE ...): ordinary word matching would drop them
_CODE = re.compile(r"\b(?:ee|e[0-9]|f[0-9]|p[0-9a-c]|ph|pc|l[1-4])\b")


def tokens(text: str) -> set[str]:
    """Lower-case words plus normalised sizes and codes: '1.5 ton' -> 1.5ton, '5 star' -> 5star, '300 L' -> 300l, 'E6' -> codee6."""
    t = (text or "").lower()
    out = {w[:-1] if len(w) >= 6 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]{3,}", t) if w not in _STOP}  # bedrooms -> bedroom
    if re.search(r"\b(?:acs?|a\.c)\b", t):  # "AC" is too short to match on its own
        out.add("conditioner")
    out |= {f"{n}ton" for n in re.findall(r"(\d+(?:\.\d+)?)\s*(?:ton|tonne|tr)\b", t)}
    out |= {f"{n}star" for n in re.findall(r"(\d)\s*[- ]?star", t)}
    out |= {f"{n}l" for n in re.findall(r"(\d+)\s*(?:l|ltr|litre|liter|litres|liters)\b", t)}
    out |= {f"code{c}" for c in _CODE.findall(t)}
    return out


def _parse(text: str) -> tuple[str, list[tuple[str, set[str]]]]:
    cut = text.find("## Product catalogue")
    head, catalogue = (text[:cut], text[cut:]) if cut != -1 else (text, "")
    products, category = [], ""
    for block in re.split(r"(?m)^(?=#{2,3} )", catalogue):
        if block.startswith("### "):
            products.append((f"[{category}] {block.strip()}" if category else block.strip(), tokens(category + " " + block[:2600])))
        elif block.startswith("## "):
            category = block.splitlines()[0][3:].strip()
    return head.strip(), products


def load() -> tuple[str, list[tuple[str, set[str]]]]:
    """(general text, [(block, its words)]) from both files. Re-read when either file changes."""
    files = [f for f in (KNOWLEDGE_FILE, EXTRA_FILE) if f.is_file()]
    if not files:
        return "", []
    mtime = tuple(f.stat().st_mtime for f in files)
    if _CACHE["mtime"] != mtime:
        heads, products = [], []
        for f in files:
            h, p = _parse(f.read_text(encoding="utf-8"))
            heads.append(h)
            products += p
        _CACHE.update({"mtime": mtime, "head": "\n\n".join(x for x in heads if x)[:HEAD_LIMIT], "products": products})
    return _CACHE["head"], _CACHE["products"]


def for_query(query: str) -> str:
    """Everything general, plus the few blocks that best match what the customer is asking about."""
    head, products = load()
    want = tokens(query)
    scored = []
    for block, toks in products:
        hit = want & toks
        if not hit:
            continue
        # model codes, sizes and error codes (words with digits) count more than ordinary words
        score = len(hit) + 3 * sum(1 for w in hit if re.search(r"\d", w) and len(w) >= 5)
        scored.append((score, block))
    scored.sort(key=lambda x: -x[0])
    chosen, used = [], 0
    for _, block in scored[:MAX_PRODUCTS]:
        piece = block[:PER_PRODUCT]
        if used + len(piece) > PRODUCT_LIMIT:
            break
        chosen.append(piece)
        used += len(piece)
    out = head or "(none provided: hand over to staff for product or price questions)"
    if chosen:
        out += "\n\nDetails that may match what the customer asked about:\n\n" + "\n\n".join(chosen)
    return out
