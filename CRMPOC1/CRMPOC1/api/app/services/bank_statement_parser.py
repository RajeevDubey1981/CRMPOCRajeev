"""Parses an uploaded bank statement into (date, description, amount) rows.

CSV is fully supported with flexible header matching for the common bank-export column names. The
amount taken is money paid OUT of INDcool's account (a Debit/Withdrawal column) -- that is the only
kind of line relevant to paying a vendor or engineer, so a Credit-only row (money coming in) is skipped.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

DATE_HEADERS = {"date", "txn date", "transaction date", "value date", "tran date"}
DESC_HEADERS = {"description", "narration", "particulars", "remarks", "details", "transaction details"}
DEBIT_HEADERS = {"amount", "debit", "debit amount", "withdrawal amt", "withdrawal amt.", "withdrawal", "withdrawal amount"}
CREDIT_HEADERS = {"credit", "credit amount", "deposit amt", "deposit amt.", "deposit", "deposit amount"}

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y"]


@dataclass
class ParsedLine:
    line_date: date
    description: str
    amount: float


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: str) -> float | None:
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        amount = float(value)
    except ValueError:
        return None
    return amount if amount > 0 else None


def parse_csv(contents: bytes) -> list[ParsedLine]:
    text = contents.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    lower_map = {(h or "").strip().lower(): h for h in reader.fieldnames}

    def find(headers: set[str]) -> str | None:
        for h in headers:
            if h in lower_map:
                return lower_map[h]
        return None

    date_col = find(DATE_HEADERS)
    desc_col = find(DESC_HEADERS)
    debit_col = find(DEBIT_HEADERS)
    if not date_col or not desc_col or not debit_col:
        raise ValueError(
            "Could not find Date / Description / Debit columns in this CSV. "
            "Expected headers like Date, Narration, Withdrawal Amt."
        )

    lines: list[ParsedLine] = []
    for row in reader:
        line_date = _parse_date(row.get(date_col, ""))
        amount = _parse_amount(row.get(debit_col, ""))
        if line_date is None or amount is None:
            continue
        lines.append(ParsedLine(line_date=line_date, description=(row.get(desc_col) or "").strip(), amount=amount))
    return lines
