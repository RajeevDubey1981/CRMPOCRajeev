"""The knowledge the WhatsApp assistant may use.

Where it lives: once anyone adds or imports an entry in the CRM ("WhatsApp Knowledge" screen) the database is the source and
changes apply to the very next reply, no deploy. Until then the two built-in files (app/data/wa_knowledge.md and
wa_knowledge_extra.md) are used. The first change from the screen copies the built-in files into the database, so nothing is lost.

The model's memory is small, so the general rules are always sent and only the few entries that match the customer's words
are added.
"""
from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.whatsapp import WaKnowledge

DATA = Path(__file__).resolve().parent.parent / "data"
KNOWLEDGE_FILE = DATA / "wa_knowledge.md"
EXTRA_FILE = DATA / "wa_knowledge_extra.md"
HEAD_LIMIT = 14000
PRODUCT_LIMIT = 7000
PER_PRODUCT = 2200
MAX_PRODUCTS = 5
CHUNK = 2000

_CACHE: dict = {"sig": None, "head": "", "products": []}
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


# ---------------- reading the built-in files ----------------
def parse_files() -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """([(title, text)] general sections, [(category, title, text)] searchable entries) from the two built-in files."""
    heads: list[tuple[str, str]] = []
    blocks: list[tuple[str, str, str]] = []
    for f in (KNOWLEDGE_FILE, EXTRA_FILE):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        cut = text.find("## Product catalogue")
        head, catalogue = (text[:cut], text[cut:]) if cut != -1 else (text, "")
        for sec in re.split(r"(?m)^(?=## )", head):
            if sec.startswith("## "):
                title, _, body = sec.partition("\n")
                if body.strip():
                    heads.append((title[3:].strip(), body.strip()))
        category = ""
        for block in re.split(r"(?m)^(?=#{2,3} )", catalogue):
            if block.startswith("### "):
                title, _, body = block.partition("\n")
                blocks.append((category, title[4:].strip(), body.strip()))
            elif block.startswith("## "):
                category = block.splitlines()[0][3:].strip()
    return heads, blocks


def import_builtin(db: Session, user_id: int | None) -> int:
    """Copy the built-in files into the database (only when it is empty). Returns how many entries were created."""
    if db.scalar(select(func.count()).select_from(WaKnowledge)):
        return 0
    heads, blocks = parse_files()
    for title, body in heads:
        db.add(WaKnowledge(title=title[:200], category="General rules", body=body, always_send=True, active=True, source="builtin", updated_by=user_id))
    for category, title, body in blocks:
        db.add(WaKnowledge(title=title[:200], category=category[:100], body=body, always_send=False, active=True, source="builtin", updated_by=user_id))
    db.commit()
    return len(heads) + len(blocks)


def ensure_seeded(db: Session, user_id: int | None) -> None:
    """The first change made from the screen keeps everything that was in the files."""
    import_builtin(db, user_id)


# ---------------- reading what the assistant will use ----------------
def _from_files() -> tuple[str, list[tuple[str, set[str]]]]:
    heads, blocks = parse_files()
    head = "\n\n".join(f"## {t}\n{b}" for t, b in heads)[:HEAD_LIMIT]
    products = [(f"[{c}] ### {t}\n\n{b}" if c else f"### {t}\n\n{b}", tokens(c + " " + t + " " + b[:2600])) for c, t, b in blocks]
    return head, products


def _from_db(db: Session) -> tuple[str, list[tuple[str, set[str]]]] | None:
    try:
        return _from_db_unsafe(db)
    except Exception:  # noqa: BLE001  the table is missing or the database hiccuped: fall back to the built-in files, never fail a reply
        db.rollback()
        return None


def _from_db_unsafe(db: Session) -> tuple[str, list[tuple[str, set[str]]]] | None:
    sig = db.execute(select(func.count(), func.max(WaKnowledge.updated_at), func.sum(WaKnowledge.active))).one()
    if not sig[0]:
        return None
    key = ("db", sig[0], str(sig[1]), sig[2])
    if _CACHE["sig"] != key:
        rows = db.scalars(select(WaKnowledge).where(WaKnowledge.active.is_(True)).order_by(WaKnowledge.id)).all()
        head = "\n\n".join(f"## {r.title}\n{r.body}" for r in rows if r.always_send)[:HEAD_LIMIT]
        products = [
            (f"[{r.category}] ### {r.title}\n\n{r.body}" if r.category else f"### {r.title}\n\n{r.body}", tokens(f"{r.category} {r.title} {r.body[:2600]}"))
            for r in rows if not r.always_send
        ]
        _CACHE.update({"sig": key, "head": head, "products": products})
    return _CACHE["head"], _CACHE["products"]


def load(db: Session | None = None) -> tuple[str, list[tuple[str, set[str]]]]:
    """(general text, [(block, its words)]): from the database when it has entries, else from the built-in files."""
    if db is not None:
        found = _from_db(db)
        if found is not None:
            return found
    key = ("files", tuple(f.stat().st_mtime for f in (KNOWLEDGE_FILE, EXTRA_FILE) if f.is_file()))
    if _CACHE["sig"] != key:
        head, products = _from_files()
        _CACHE.update({"sig": key, "head": head, "products": products})
    return _CACHE["head"], _CACHE["products"]


def select_blocks(query: str, db: Session | None = None) -> tuple[str, list[str]]:
    head, products = load(db)
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
    return head, chosen


def for_query(query: str, db: Session | None = None) -> str:
    """Everything general, plus the few entries that best match what the customer is asking about."""
    head, chosen = select_blocks(query, db)
    out = head or "(none provided: hand over to staff for product or price questions)"
    if chosen:
        out += "\n\nDetails that may match what the customer asked about:\n\n" + "\n\n".join(chosen)
    return out


# ---------------- reading an uploaded file ----------------
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class UploadError(Exception):
    pass


def _docx_text(data: bytes) -> str:
    try:
        root = ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise UploadError("This does not look like a Word (.docx) file.") from exc

    def para(p) -> str:
        return "".join(t.text or "" for t in p.iter(W + "t")).strip()

    out: list[str] = []
    for el in root.find(W + "body"):
        if el.tag == W + "p":
            t = para(el)
            if t:
                out.append(t)
        elif el.tag == W + "tbl":
            for tr in el.iter(W + "tr"):
                cells = [" ".join(para(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")]
                if any(cells):
                    out.append(" | ".join(cells))
    return "\n".join(out)


def read_upload(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith((".md", ".txt", ".csv")):
        return data.decode("utf-8", "replace")
    if name.endswith(".docx"):
        return _docx_text(data)
    if name.endswith(".pdf"):
        raise UploadError("PDF files are not supported yet. Save the PDF as a Word file, or paste its text into a new entry.")
    raise UploadError("Upload a Word (.docx), Markdown (.md) or text (.txt) file.")


def split_into_entries(stem: str, text: str, category: str) -> list[tuple[str, str, str]]:
    """[(title, category, body)]: by '###' headings when there are any, otherwise in parts of about 2000 characters."""
    text = text.strip()
    if not text:
        raise UploadError("The file has no text in it.")
    if re.search(r"(?m)^### ", text):
        out, cat = [], category
        for block in re.split(r"(?m)^(?=#{2,3} )", text):
            if block.startswith("### "):
                title, _, body = block.partition("\n")
                if body.strip():
                    out.append((title[4:].strip()[:200], cat, body.strip()))
            elif block.startswith("## "):
                cat = block.splitlines()[0][3:].strip()[:100] or category
        if out:
            return out
    parts, cur, size = [], [], 0
    for ln in text.splitlines():
        if size + len(ln) > CHUNK and cur:
            parts.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        parts.append("\n".join(cur))
    return [(f"{stem} (part {i} of {len(parts)})" if len(parts) > 1 else stem, category, p) for i, p in enumerate(parts, 1)]
