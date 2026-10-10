"""Reads an Excel (.xlsx) or CSV file that someone uploads, and guesses which column is which."""

from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET

from fastapi import HTTPException, status

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _bad(msg: str):
    raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref or "")
    n = 0
    for ch in (letters.group(0) if letters else "A"):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(data: bytes) -> list[list[str]]:
    """The first sheet of an .xlsx file as rows of text (no extra library needed)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        _bad("This is not an Excel (.xlsx) file")
    names = set(zf.namelist())
    strings: list[str] = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            strings.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    sheet_path = "xl/worksheets/sheet1.xml"
    if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        first = wb.find("m:sheets/m:sheet", NS)
        if first is not None:
            rid = first.get("{%s}id" % NS["r"])
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rels:
                if rel.get("Id") == rid:
                    target = rel.get("Target", "")
                    sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
    if sheet_path not in names:
        _bad("The first sheet of the Excel file could not be read")
    root = ET.fromstring(zf.read(sheet_path))
    rows: list[list[str]] = []
    for row in root.iter("{%s}row" % NS["m"]):
        cells: dict[int, str] = {}
        for c in row.findall("m:c", NS):
            idx = _col_index(c.get("r", ""))
            t = c.get("t")
            v = c.find("m:v", NS)
            if t == "s" and v is not None and v.text is not None:
                text = strings[int(v.text)] if int(v.text) < len(strings) else ""
            elif t == "inlineStr":
                text = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            elif v is not None and v.text is not None:
                text = v.text
                if t is None and re.fullmatch(r"-?\d+\.0+", text):
                    text = text.split(".")[0]
                elif t is None and re.fullmatch(r"-?\d+\.?\d*[eE]\+?\d+", text):
                    try:
                        text = str(int(float(text)))
                    except ValueError:
                        pass
            else:
                text = ""
            cells[idx] = text.strip()
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
        if len(rows) > MAX_ROWS + 1:
            break
    return rows


def read_csv(data: bytes) -> list[list[str]]:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            text = ""
    if not text:
        _bad("The file could not be read as text")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [[(c or "").strip() for c in row] for row in csv.reader(io.StringIO(text), dialect) if any((c or "").strip() for c in row)]


def read_table(filename: str, data: bytes) -> tuple[list[str], list[dict]]:
    """(column names, rows as dicts). The first non-empty row holds the column names."""
    if len(data) > MAX_BYTES:
        _bad("The file is bigger than 5 MB")
    name = (filename or "").lower()
    if name.endswith(".xlsx") or data[:2] == b"PK":
        table = read_xlsx(data)
    elif name.endswith(".csv") or name.endswith(".txt") or name.endswith(".tsv"):
        table = read_csv(data)
    elif name.endswith(".xls"):
        _bad("An old .xls file cannot be read. Save it as .xlsx or .csv and try again.")
    else:
        _bad("Upload an .xlsx or .csv file")
    if len(table) < 2:
        _bad("The file has no data rows")
    header = [h.strip() or f"Column {i + 1}" for i, h in enumerate(table[0])]
    seen: dict[str, int] = {}
    cols: list[str] = []
    for h in header:
        seen[h] = seen.get(h, 0) + 1
        cols.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
    rows = []
    for r in table[1:MAX_ROWS + 1]:
        rows.append({cols[i]: (r[i] if i < len(r) else "") for i in range(len(cols))})
    return cols, rows


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


GUESSES = {
    "name": ["name", "fullname", "contactname", "customername", "buyername", "sendername", "person", "contactperson"],
    "company": ["company", "companyname", "firm", "firmname", "organization", "organisation", "business"],
    "phone": ["phone", "phonenumber", "mobile", "mobilenumber", "contactnumber", "telephone", "tel", "whatsapp", "mobileno", "phoneno"],
    "email": ["email", "emailid", "mail", "emailaddress"],
    "item": ["item", "product", "products", "requirement", "wants", "productname", "itemname"],
    "message": ["message", "details", "remarks", "comments", "description", "notes", "enquiry", "inquiry"],
    "place": ["city", "place", "location", "town"],
    "state": ["state", "province", "region"],
    "country": ["country", "nation"],
    "pincode": ["pincode", "pin", "zip", "zipcode", "postalcode", "postcode"],
    "value_lakh": ["valuelakh", "value", "estimatedvalue", "amountlakh"],
    "kind": ["kind", "type", "category", "businesstype", "role"],
    "why": ["why", "evidence", "note", "reason", "shipments"],
}


def guess_mapping(columns: list[str]) -> dict[str, str]:
    """field -> column name, from how the columns are named."""
    by_key = {_key(c): c for c in columns}
    out: dict[str, str] = {}
    for field, names in GUESSES.items():
        for n in names:
            if n in by_key and by_key[n] not in out.values():
                out[field] = by_key[n]
                break
    return out


def pick(row: dict, mapping: dict, field: str) -> str:
    col = mapping.get(field)
    return (row.get(col) or "").strip() if col else ""
