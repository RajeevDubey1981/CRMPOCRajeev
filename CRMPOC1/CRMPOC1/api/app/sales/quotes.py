"""Quotations: made from a lead, items copied from the CRM item master onto the line, a discount per line, GST split
by the customer's state (none on an export), approval by the Sales Manager (and Admin above the discount limit),
and Admin's override."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.sales import crm_link
from app.sales.leads import get_setting, log, now
from app.sales.models import SalesLead, SalesQuotation, SalesQuotationHistory, SalesQuotationLine
from app.sales.rules import QUOTE_STATUSES, QUOTE_TERMS, default_gst_for_hsn

CENT = Decimal("0.01")


def d(value) -> Decimal:
    return Decimal(str(value if value is not None else 0))


def q2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def bad(msg: str, code: int = status.HTTP_400_BAD_REQUEST):
    raise HTTPException(code, msg)


def fiscal_year(today: date) -> str:
    start = today.year if today.month >= 4 else today.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def next_quote_no(sdb: Session, today: date | None = None) -> str:
    today = today or date.today()
    fy = fiscal_year(today)
    prefix = f"QT/{fy}/"
    count = sdb.scalar(select(func.count()).select_from(SalesQuotation).where(SalesQuotation.quote_no.like(prefix + "%"))) or 0
    n = count + 1
    while sdb.scalar(select(SalesQuotation.id).where(SalesQuotation.quote_no == f"{prefix}{n:04d}")):
        n += 1
    return f"{prefix}{n:04d}"


def history(sdb: Session, q: SalesQuotation, text: str, user: User | None) -> None:
    sdb.add(SalesQuotationHistory(quotation_id=q.id, text=text, by_user_id=user.id if user else None, by_name=user.name if user else ""))


def lines_of(sdb: Session, q: SalesQuotation) -> list[SalesQuotationLine]:
    return list(sdb.scalars(select(SalesQuotationLine).where(SalesQuotationLine.quotation_id == q.id).order_by(SalesQuotationLine.position, SalesQuotationLine.id)))


def calc(q: SalesQuotation, lines: list[SalesQuotationLine], home_state: str, limit: Decimal) -> dict:
    export = q.currency == "USD"
    gross = disc = taxable = tax = Decimal(0)
    max_disc = Decimal(0)
    rows = []
    for ln in lines:
        g = d(ln.rate) * d(ln.qty)
        dd = g * d(ln.discount_pct) / 100
        t = g - dd
        gst = Decimal(0) if export else d(ln.gst_pct)
        x = t * gst / 100
        gross += g
        disc += dd
        taxable += t
        tax += x
        max_disc = max(max_disc, d(ln.discount_pct))
        rows.append({
            "id": ln.id, "item_code": ln.item_code, "item_name": ln.item_name, "hsn": ln.hsn, "qty": float(ln.qty), "rate": float(ln.rate),
            "discount_pct": float(ln.discount_pct), "gst_pct": float(gst), "gross": float(q2(g)), "taxable": float(q2(t)), "tax": float(q2(x)), "amount": float(q2(t + x)),
        })
    overall = (disc * 100 / gross) if gross else Decimal(0)
    high = max_disc > limit or overall > limit
    intra = (not export) and (q.state or "").strip().lower() == home_state.strip().lower()
    return {
        "rows": rows, "gross": q2(gross), "discount": q2(disc), "taxable": q2(taxable), "tax": q2(tax), "total": q2(taxable + tax),
        "discount_pct": q2(overall), "high_discount": high, "intra_state": intra,
    }


def recalc(sdb: Session, q: SalesQuotation) -> dict:
    limit = d(get_setting(sdb, "discount_limit"))
    c = calc(q, lines_of(sdb, q), get_setting(sdb, "home_state"), limit)
    q.gross, q.discount, q.taxable, q.tax, q.total = c["gross"], c["discount"], c["taxable"], c["tax"], c["total"]
    q.discount_pct, q.high_discount = c["discount_pct"], c["high_discount"]
    return c


def set_lines(main_db: Session | None, sdb: Session, q: SalesQuotation, items: list[dict]) -> None:
    for ln in lines_of(sdb, q):
        sdb.delete(ln)
    sdb.flush()
    fx = d(q.fx_rate) or d(get_setting(sdb, "fx_rate"))
    usd = q.currency == "USD"
    for pos, it in enumerate(items):
        code = (it.get("item_code") or "").strip()
        base = crm_link.get_item(main_db, code) if (main_db is not None and code) else None
        name = (it.get("item_name") or (base or {}).get("item_name") or "").strip()
        if not name:
            bad("Every line needs an item")
        hsn = it.get("hsn") or (base or {}).get("hsn")
        if it.get("rate") is not None and str(it.get("rate")) != "":
            rate = d(it["rate"])
        elif base is not None and base["mrp"]:
            rate = d(base["mrp"]) / fx if usd else d(base["mrp"])
        else:
            rate = Decimal(0)
        gst = d(it["gst_pct"]) if it.get("gst_pct") not in (None, "") else Decimal(default_gst_for_hsn(hsn))
        qty = d(it.get("qty") or 1)
        disc = d(it.get("discount_pct") or 0)
        if qty <= 0:
            bad("The quantity must be more than zero")
        if disc < 0 or disc > 40:
            bad("The discount must be between 0 and 40%")
        sdb.add(SalesQuotationLine(quotation_id=q.id, position=pos, item_code=code or (base or {}).get("item_code", ""), item_name=name, hsn=hsn, qty=qty, rate=q2(rate), discount_pct=disc, gst_pct=gst))
    sdb.flush()
    recalc(sdb, q)


def create_quotation(main_db: Session | None, sdb: Session, lead: SalesLead, user: User, *, items: list[dict] | None = None) -> SalesQuotation:
    export = lead.lead_type == "export"
    pay, delivery, warranty = QUOTE_TERMS.get(lead.lead_type, QUOTE_TERMS["retail"])
    ref = None
    if lead.lead_type == "gem":
        ref = f"GeM bid: {lead.details or lead.item}"[:250]
    elif lead.lead_type == "export" and lead.price_basis:
        delivery = f"Within 35 days of the advance, {lead.price_basis}"
    q = SalesQuotation(
        quote_no=next_quote_no(sdb), lead_id=lead.id, party=lead.name, address=lead.place, state=lead.country if export else lead.state,
        valid_days=30 if export else 15, lead_type=lead.lead_type, currency="USD" if export else "INR",
        fx_rate=d(get_setting(sdb, "fx_rate")) if export else None, status="draft", payment_terms=pay, delivery_terms=delivery,
        warranty_terms=warranty, reference_line=ref, created_by=user.id,
    )
    sdb.add(q)
    sdb.flush()
    history(sdb, q, f"Draft started from the lead {lead.name}", user)
    if items:
        set_lines(main_db, sdb, q, items)
    log(sdb, lead, "quotation", f"Quotation {q.quote_no} started", user)
    return q


EDITABLE = ("draft", "ret")


def update_quotation(main_db: Session | None, sdb: Session, q: SalesQuotation, data: dict) -> None:
    if q.status not in EDITABLE:
        bad("This quotation can no longer be changed")
    for key in ("party", "address", "state", "gstin", "valid_days", "payment_terms", "delivery_terms", "warranty_terms", "reference_line", "note"):
        if key in data and data[key] is not None:
            setattr(q, key, data[key])
    if "items" in data and data["items"] is not None:
        set_lines(main_db, sdb, q, data["items"])
    else:
        recalc(sdb, q)


def transition(sdb: Session, q: SalesQuotation, action: str, user: User, ticks: set[str], *, reason: str = "", is_admin: bool = False) -> None:
    """One step of the approval path. ticks decide who may do it."""
    st = q.status
    reason = (reason or "").strip()

    def need(*keys):
        if not (set(keys) & ticks):
            bad("You do not have this tick in Sales", status.HTTP_403_FORBIDDEN)

    def need_reason():
        if len(reason) < 5:
            bad("Write a short reason")

    if action == "submit":
        need("make_quote")
        if st not in EDITABLE:
            bad("Only a draft or a returned quotation can be submitted")
        if not lines_of(sdb, q):
            bad("Add at least one item")
        recalc(sdb, q)
        q.status = "wadm" if q.high_discount else "wait"
        history(sdb, q, "Submitted for approval" + (f": {q.note}" if q.note else "") + (". The discount is above the limit, so Admin or Sub Admin must approve." if q.high_discount else ""), user)
    elif action == "approve":
        if st == "wait":
            need("approve_quote", "override")
            q.status, q.approved_by, q.approved_by_name = "appr", user.id, user.name
            history(sdb, q, "Approved", user)
        elif st == "wadm":
            need("approve_high", "override")
            q.status, q.approved_by, q.approved_by_name = "appr", user.id, user.name
            history(sdb, q, "Approved (high discount, Admin level)", user)
        elif st == "rej":
            need("override")
            need_reason()
            q.status, q.approved_by, q.approved_by_name = "appr", user.id, user.name
            history(sdb, q, f"ADMIN OVERRIDE: approved over a rejection. Reason: {reason}", user)
        else:
            bad("This quotation is not waiting for approval")
    elif action == "override_approve":
        need("override")
        need_reason()
        if st not in ("wait", "wadm", "rej"):
            bad("Nothing to override here")
        q.status, q.approved_by, q.approved_by_name = "appr", user.id, user.name
        history(sdb, q, f"ADMIN OVERRIDE: approved. Reason: {reason}", user)
    elif action == "send_up":
        need("approve_quote")
        if st != "wait":
            bad("Only a quotation waiting for the manager can be sent up")
        q.status = "wadm"
        history(sdb, q, "Sent to Admin / Sub Admin", user)
    elif action == "return":
        need("approve_quote", "approve_high", "override")
        need_reason()
        if st not in ("wait", "wadm"):
            bad("This quotation is not waiting for approval")
        q.status = "ret"
        history(sdb, q, f"Returned for changes: {reason}", user)
    elif action == "reject":
        need("approve_quote", "approve_high", "override")
        need_reason()
        if st not in ("wait", "wadm"):
            bad("This quotation is not waiting for approval")
        if st == "wadm" and not ({"approve_high", "override"} & ticks):
            bad("Only Admin or Sub Admin can decide a high discount", status.HTTP_403_FORBIDDEN)
        q.status = "rej"
        history(sdb, q, f"Rejected: {reason}", user)
    elif action == "send":
        need("send_quote")
        if st != "appr":
            bad("Only an approved quotation can be sent")
        q.status, q.sent_at = "sent", now()
        history(sdb, q, "Emailed to the customer with the PDF (marked as sent)", user)
    elif action == "accept":
        need("send_quote", "make_quote")
        if st != "sent":
            bad("Only a sent quotation can be accepted")
        q.status = "acc"
        history(sdb, q, "Customer accepted", user)
    elif action == "decline":
        need("send_quote", "make_quote")
        if st != "sent":
            bad("Only a sent quotation can be declined")
        q.status = "cust_rej"
        history(sdb, q, "Customer declined", user)
    elif action == "cancel":
        need("override")
        need_reason()
        if st not in ("appr", "sent"):
            bad("Only an approved or sent quotation can be cancelled")
        q.status = "cancel"
        history(sdb, q, f"ADMIN OVERRIDE: cancelled. Reason: {reason}", user)
    else:
        bad("Unknown action")


def quotation_out(sdb: Session, q: SalesQuotation, *, with_lines: bool = True) -> dict:
    out = {
        "id": q.id, "quote_no": q.quote_no, "lead_id": q.lead_id, "party": q.party, "address": q.address, "state": q.state,
        "gstin": q.gstin, "valid_days": q.valid_days, "lead_type": q.lead_type, "currency": q.currency,
        "fx_rate": float(q.fx_rate) if q.fx_rate is not None else None, "status": q.status, "status_label": QUOTE_STATUSES.get(q.status, q.status),
        "payment_terms": q.payment_terms, "delivery_terms": q.delivery_terms, "warranty_terms": q.warranty_terms,
        "reference_line": q.reference_line, "note": q.note, "gross": float(q.gross), "discount": float(q.discount),
        "taxable": float(q.taxable), "tax": float(q.tax), "total": float(q.total), "discount_pct": float(q.discount_pct),
        "high_discount": q.high_discount, "approved_by_name": q.approved_by_name,
        "created_at": q.created_at.isoformat() if q.created_at else None, "created_by": q.created_by,
    }
    if with_lines:
        limit = d(get_setting(sdb, "discount_limit"))
        c = calc(q, lines_of(sdb, q), get_setting(sdb, "home_state"), limit)
        out["lines"] = c["rows"]
        out["intra_state"] = c["intra_state"]
        out["discount_limit"] = float(limit)
        out["history"] = [
            {"text": h.text, "by": h.by_name, "at": h.at.isoformat() if h.at else None}
            for h in sdb.scalars(select(SalesQuotationHistory).where(SalesQuotationHistory.quotation_id == q.id).order_by(SalesQuotationHistory.id))
        ]
        out["company"] = {
            "name": get_setting(sdb, "company_name", "INDcool") or "INDcool",
            "tagline": "Air conditioners · Refrigeration · Appliances",
            "address": get_setting(sdb, "company_address", "OC528, Gaur City, Greater Noida West, Uttar Pradesh") or "",
            "gstin": get_setting(sdb, "company_gstin", ""),
        }
    return out
