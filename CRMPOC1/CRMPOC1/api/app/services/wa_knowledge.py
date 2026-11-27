"""The knowledge the WhatsApp assistant may use (app/data/wa_knowledge.md).

The file is big (a whole product catalogue), the model's memory is not. So the general rules and policies at the top are
always sent, and only the few product blocks that match the customer's words are added.
"""
from __future__ import annotations

import re
from pathlib import Path

KNOWLEDGE_FILE = Path(__file__).resolve().parent.parent / "data" / "wa_knowledge.md"
HEAD_LIMIT = 12000
PRODUCT_LIMIT = 7000
PER_PRODUCT = 2200
MAX_PRODUCTS = 5

_CACHE: dict = {"mtime": None, "head": "", "products": []}
_STOP = {"the", "and", "for", "with", "you", "your", "are", "this", "that", "what", "which", "have", "has", "can", "any",
         "how", "much", "price", "cost", "please", "hai", "kya", "ka", "ki", "ke", "mera", "meri", "hello", "need", "want",
         "tell", "about", "model"}


def tokens(text: str) -> set[str]:
    """Lower-case words plus normalised sizes: '1.5 ton' -> 1.5ton, '5 star' -> 5star, '300 L' -> 300l."""
    t = (text or "").lower()
    out = {w for w in re.findall(r"[a-z0-9]{3,}", t) if w not in _STOP}
    out |= {f"{n}ton" for n in re.findall(r"(\d+(?:\.\d+)?)\s*(?:ton|tonne|tr)\b", t)}
    out |= {f"{n}star" for n in re.findall(r"(\d)\s*[- ]?star", t)}
    out |= {f"{n}l" for n in re.findall(r"(\d+)\s*(?:l|ltr|litre|liter|litres|liters)\b", t)}
    return out


def load() -> tuple[str, list[tuple[str, set[str]]]]:
    """(general text, [(product block, its words)]). Re-read when the file changes."""
    try:
        mtime = KNOWLEDGE_FILE.stat().st_mtime
    except OSError:
        return "", []
    if _CACHE["mtime"] != mtime:
        text = KNOWLEDGE_FILE.read_text(encoding="utf-8")
        cut = text.find("## Product catalogue")
        head, catalogue = (text[:cut], text[cut:]) if cut != -1 else (text, "")
        products, category = [], ""
        for block in re.split(r"(?m)^(?=#{2,3} )", catalogue):
            if block.startswith("### "):
                products.append((f"[{category}] {block.strip()}" if category else block.strip(), tokens(category + " " + block[:2600])))
            elif block.startswith("## "):
                category = block.splitlines()[0][3:].strip()
        _CACHE.update({"mtime": mtime, "head": head.strip()[:HEAD_LIMIT], "products": products})
    return _CACHE["head"], _CACHE["products"]


def for_query(query: str) -> str:
    """Everything general, plus the few product blocks that best match what the customer is asking about."""
    head, products = load()
    want = tokens(query)
    scored = []
    for block, toks in products:
        hit = want & toks
        if not hit:
            continue
        # model codes and sizes (words with digits) count more than ordinary words
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
        out += "\n\nProduct details that may match what the customer asked about:\n\n" + "\n\n".join(chosen)
    return out
