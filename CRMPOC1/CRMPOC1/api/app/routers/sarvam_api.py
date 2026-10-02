"""Sarvam AI call-centre endpoints for the INDcool CRM.

Additive module: it only READS/INSERTS complaint rows through the existing models.
Auth: header X-API-Key must equal env SARVAM_API_KEY (set in the service .env).
Routes (all under /api/sarvam):
  GET  /complaints/options        valid query types
  POST /complaints                register a complaint / service / sales / installation query
  GET  /complaints/track          ?comp_no=...&mobile=... (mobile optional but recommended)
  GET  /complaints/{comp_no}      same as track
"""
import hmac
import threading
import os
import re
_EMAIL_RE = 1
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.complaint_whatsapp import send_complaint_registered_whatsapp
from app.services.complaint_intake import link_and_sync, send_confirmation_email
from app.models.complaint import Complaint, ComplaintStatusLog
from app.routers.complaints import _generate_access_code, _generate_comp_no

router = APIRouter(prefix="/api/sarvam", tags=["sarvam"])

QUERY_TYPES = [
    {"value": "Service", "label": "Service / repair complaint"},
    {"value": "Installation", "label": "Installation"},
    {"value": "Sales", "label": "Sales query"},
    {"value": "Others", "label": "Other queries"},
]


def require_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)) -> None:
    if not x_api_key and authorization and authorization.lower().startswith("bearer "):
        x_api_key = authorization[7:].strip()
    secret = os.environ.get("SARVAM_API_KEY", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Sarvam API key is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _pick(d: dict, *keys: str) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return None


def _mobile10(raw: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        return None
    m = digits[-10:]
    return m if re.fullmatch(r"[6-9]\d{9}", m) else None


def _query_type(raw: Optional[str]) -> str:
    t = (raw or "").lower()
    if "install" in t:
        return "Installation"
    if "sale" in t or "purchase" in t or "buy" in t or "enquiry" in t or "inquiry" in t:
        return "Sales"
    if "service" in t or "repair" in t or "complain" in t or "issue" in t:
        return "Service"
    return "Others"


# Words that clearly describe a product fault. Used only to rescue a genuine repair request that the
# voice agent labelled with an unrecognised category (which _query_type() maps to "Others").
_FAULT_HINTS = (
    "not cooling", "cooling", "not working", "stopped working", "not start", "not turn", "not switch",
    "repair", "breakdown", "break down", "broken", "leak", "noise", "fault", "defect", "damage",
    "compressor", "error code", "warranty", "gas", "not heating", "tripping", "service",
)


_SALES_RE = re.compile(
    r"\b(buy|buying|purchase|price|prices|pricing|quotation|quote|discount|offer|emi|dealer|dealership|"
    r"distributor|franchise|showroom|bulk|kharid\w*|khareed\w*|lena hai|lene hai|daam|new ac|new split|"
    r"new fridge|new refrigerator|naya ac|naya fridge|want to order|how much)\b",
    re.I,
)
_INSTALL_RE = re.compile(r"\b(install|installation|installed|fitting|mounting|demo|lagwa\w*|lagana|lagvana|uninstall)\b", re.I)


def _refine_type(qtype: str, problem: Optional[str], remark: Optional[str], extra: Optional[str] = None) -> str:
    """If the category came out as 'Others', look at what the caller actually said and pick the interest:
    Installation, Sales (buying / price / dealer ...) or Service (a product fault).
    Never overrides Installation / Sales / Service."""
    if qtype != "Others":
        return qtype
    text = ((problem or "") + " " + (remark or "") + " " + (extra or "")).lower()
    if _INSTALL_RE.search(text):
        return "Installation"
    if _SALES_RE.search(text):
        return "Sales"
    if any(h in text for h in _FAULT_HINTS):
        return "Service"
    return qtype


def _int_or_none(raw: Optional[str]) -> Optional[int]:
    try:
        return int(float(str(raw).strip())) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _log_call(db: Session, complaint: Complaint, qtype: str, name: str, mobile: str, email: Optional[str],
              summary: Optional[str], interest_line: str, duration: Optional[int]) -> None:
    """Add the Sarvam conversation to the CRM call log. Sales and Installation leads get a follow-up for tomorrow.
    Never blocks the registration: any problem is only logged."""
    try:
        with db.begin_nested():
            from app.models.call import Call
            from app.routers.calls import _generate_ref_no
            from app.services.pending_action_sync import sync_call_pending_actions

            now = datetime.now(timezone.utc)
            follow = qtype in ("Sales", "Installation")
            notes = "Sarvam voice agent call (" + qtype + "), complaint " + complaint.comp_no + "."
            if interest_line:
                notes += " " + interest_line
            if summary:
                notes += " Summary: " + summary
            call = Call(
                ref_no=_generate_ref_no(db),
                customer_name=name,
                customer_email=email,
                phone=mobile,
                call_type="Inbound",
                status="Completed",
                priority="High" if follow else "Medium",
                call_datetime=now,
                duration_secs=duration,
                followup_date=(now + timedelta(days=1)) if follow else None,
                notes=notes[:4000],
                follow_up_notes=("Call back the customer about this " + qtype.lower() + " enquiry.") if follow else None,
                follow_up_status="Pending" if follow else None,
                complaint_id=complaint.id,
            )
            db.add(call)
            db.flush()
            sync_call_pending_actions(db, call)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("could not log the Sarvam call in the call log")


def _ok(message: str, data: dict) -> dict:
    return {"success": True, "message": message, "data": data}


def _find(db: Session, comp_no: str, mobile: Optional[str]) -> Optional[Complaint]:
    stmt = select(Complaint).where(Complaint.comp_no == comp_no.strip(), Complaint.deleted_at.is_(None))
    c = db.execute(stmt).scalars().first()
    if c is None:
        return None
    m = _mobile10(mobile) if mobile else None
    if m and _mobile10(c.customer_mobile) != m:
        return None
    return c


@router.get("/complaints/options", dependencies=[Depends(require_key)])
def complaint_options():
    return _ok("Valid query types", {"query_types": QUERY_TYPES})


@router.post("/complaints", dependencies=[Depends(require_key)])
def register_complaint(data: dict = Body(...), db: Session = Depends(get_db)):
    name = _pick(data, "customer_name", "cust_name", "name", "cname", "customer")
    mobile = _mobile10(_pick(data, "customer_mobile", "cust_mobile", "mobile", "phone", "cmobile"))
    if not name:
        raise HTTPException(status_code=422, detail="Customer name is required")
    if not mobile:
        raise HTTPException(status_code=422, detail="A valid 10-digit Indian mobile number is required")
    qtype = _query_type(_pick(data, "query_type", "querytype", "type", "category", "query"))
    problem = _pick(data, "problem_description", "problem", "prob", "issue", "description", "query_desc")
    model = _pick(data, "model_details", "model_det", "model")
    email = _pick(data, "customer_email", "email")
    address = _pick(data, "customer_address", "cost_add", "address", "cust_add")
    remark = _pick(data, "remark", "remarks", "summary")
    interest = _pick(data, "interest", "product_interest", "interested_in", "product")
    capacity = _pick(data, "capacity", "tonnage", "size")
    budget = _pick(data, "budget", "price_range")
    city = _pick(data, "city", "location", "area")
    preferred = _pick(data, "preferred_time", "callback_time", "best_time")
    call_summary = _pick(data, "call_summary", "conversation_summary", "transcript_summary")
    duration = _int_or_none(_pick(data, "call_duration", "duration", "duration_secs"))
    qtype = _refine_type(qtype, problem, remark, " ".join(x for x in (interest, call_summary) if x))
    if not model and (interest or capacity):
        model = " ".join(x for x in (interest, capacity) if x)[:255]
    interest_bits = []
    if interest:
        interest_bits.append("Interest: " + interest)
    if capacity:
        interest_bits.append("Capacity: " + capacity)
    if budget:
        interest_bits.append("Budget: " + budget)
    if city:
        interest_bits.append("City: " + city)
    if preferred:
        interest_bits.append("Preferred call time: " + preferred)
    interest_line = " | ".join(interest_bits)
    if not problem and qtype in ("Sales", "Installation") and (interest or call_summary):
        problem = ("Sales enquiry: " if qtype == "Sales" else "Installation request: ") + (interest or call_summary)
    if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="A valid customer email address is required. Ask the customer for it and confirm it.")
    gem_order = _pick(data, "gem_order_id", "gem_order", "order_id")
    pi_no = _pick(data, "pi_number", "pi_no", "pi")
    extra = []
    if gem_order:
        extra.append("GeM Order ID: " + gem_order)
    if pi_no:
        extra.append("PI No: " + pi_no)
    if extra:
        remark = ((remark + " | ") if remark else "") + " | ".join(extra)
    if interest_line:
        remark = ((remark + " | ") if remark else "") + interest_line
    sms = (_pick(data, "smsreq", "send_sms") or "").lower() in ("1", "true", "yes", "y")

    # Duplicate guard: same mobile + type + problem in the last 10 minutes returns the existing record.
    since = datetime.now(timezone.utc) - timedelta(minutes=10)
    dup = db.execute(
        select(Complaint).where(
            Complaint.customer_mobile == mobile,
            Complaint.query_type == qtype,
            Complaint.source == "callcenter",
            Complaint.problem_description == problem,
            Complaint.created_at >= since,
            Complaint.deleted_at.is_(None),
        )
    ).scalars().first()
    if dup is not None:
        return _ok("Registered earlier in this call", {"comp_no": dup.comp_no, "comp_date": str(dup.comp_date), "duplicate": True})

    complaint = Complaint(
        comp_no=_generate_comp_no(),
        comp_date=date.today(),
        customer_name=name,
        customer_mobile=mobile,
        customer_email=email,
        customer_address=address,
        model_details=model,
        problem_description=problem,
        query_type=qtype,
        remark=remark,
        send_sms=sms,
        access_code=_generate_access_code(),
        status="Pending",
        created_by=None,
        source="callcenter",
    )
    db.add(complaint)
    db.flush()
    db.add(ComplaintStatusLog(
        complaint_id=complaint.id, old_status=None, new_status="Pending",
        changed_by=None, remark="Complaint created from Sarvam call",
    ))
    linked_service = link_and_sync(db, complaint)
    _log_call(db, complaint, qtype, name, mobile, email, call_summary or remark, interest_line, duration)
    service_request_no = linked_service.request_no if linked_service is not None else None
    db.commit()
    db.refresh(complaint)
    try:
        threading.Thread(
            target=send_complaint_registered_whatsapp,
            args=(mobile, name, qtype, complaint.comp_no, problem),
            daemon=True,
        ).start()
    except Exception:
        pass
    try:
        threading.Thread(
            target=send_confirmation_email,
            args=(email, name, complaint.comp_no, qtype, complaint.status, mobile, problem, service_request_no),
            daemon=True,
        ).start()
    except Exception:
        pass
    return _ok("Complaint registered successfully", {"comp_no": complaint.comp_no, "comp_date": str(complaint.comp_date), "query_type": qtype, "status": complaint.status})


def _track_by_mobile(mobile: Optional[str], db: Session) -> dict:
    m = _mobile10(mobile)
    if not m:
        return {"success": False, "message": "Complaint number or a valid mobile number is required", "data": {}}
    rows = db.execute(
        select(Complaint).where(Complaint.deleted_at.is_(None)).order_by(Complaint.id.desc()).limit(300)
    ).scalars().all()
    mine = [c for c in rows if _mobile10(c.customer_mobile) == m][:3]
    if not mine:
        return {"success": False, "message": "No complaint found for this mobile number", "data": {}}
    c = mine[0]
    return _ok("Complaint found", {
        "comp_no": c.comp_no,
        "comp_date": str(c.comp_date),
        "status": c.status,
        "status_date": c.status_date.isoformat() if c.status_date else None,
        "query_type": c.query_type,
        "model_details": c.model_details,
        "problem": (c.problem_description or "")[:200],
        "total_found": len(mine),
        "recent": [{"comp_no": x.comp_no, "comp_date": str(x.comp_date), "status": x.status, "query_type": x.query_type} for x in mine],
    })


def _track_by_identifier(key: str, db: Session) -> Optional[dict]:
    """Find by email, GeM order id or PI number (stored in remark)."""
    k = (key or "").strip().lower()
    if len(k) < 3:
        return None
    rows = db.execute(
        select(Complaint).where(Complaint.deleted_at.is_(None)).order_by(Complaint.id.desc()).limit(500)
    ).scalars().all()
    if "@" in k:
        mine = [c for c in rows if (c.customer_email or "").strip().lower() == k][:3]
    else:
        mine = [c for c in rows if k in (c.remark or "").lower()][:3]
    if not mine:
        return None
    c = mine[0]
    return _ok("Complaint found", {
        "comp_no": c.comp_no,
        "comp_date": str(c.comp_date),
        "status": c.status,
        "status_date": c.status_date.isoformat() if c.status_date else None,
        "query_type": c.query_type,
        "model_details": c.model_details,
        "problem": (c.problem_description or "")[:200],
        "total_found": len(mine),
        "recent": [{"comp_no": x.comp_no, "comp_date": str(x.comp_date), "status": x.status, "query_type": x.query_type} for x in mine],
    })


def _order_summary(key: str, db: Session) -> Optional[dict]:
    """Look up a CRM order (GeM order no / bill no / LR no) and summarise dispatch + installation status."""
    from sqlalchemy import func
    from app.models.order import Order, OrderItem
    from app.models.installation import InstallationRequest
    k = (key or "").strip().lower()
    if len(k) < 3:
        return None
    o = db.execute(
        select(Order).where(
            Order.deleted_at.is_(None),
            (func.lower(Order.order_no) == k) | (func.lower(Order.oem_bill_no) == k)
            | (func.lower(Order.vendor_bill_no) == k) | (func.lower(Order.lrn_no) == k),
        ).order_by(Order.id.desc())
    ).scalars().first()
    if o is None:
        return None
    parts = ["Order " + str(o.order_no) + " status: " + str(o.status or "Unknown")]
    if o.order_date:
        parts.append("order date " + str(o.order_date))
    if o.actual_delivery_date:
        parts.append("delivered on " + str(o.actual_delivery_date))
    elif o.expected_delivery_date:
        parts.append("expected delivery " + str(o.expected_delivery_date))
    if o.lrn_no:
        parts.append("LR number " + str(o.lrn_no))
    try:
        items = db.execute(select(OrderItem).where(OrderItem.order_id == o.id)).scalars().all()
        counts = {}
        for it in items:
            s = str(it.installation_status or "Unknown")
            counts[s] = counts.get(s, 0) + 1
        if counts:
            parts.append("installation status of items: " + ", ".join(str(v) + " " + s for s, v in counts.items()))
        reqs = db.execute(select(InstallationRequest).where(InstallationRequest.order_id == o.id)).scalars().all()
        for r in reqs[:3]:
            line = "installation request " + str(r.status or "Unknown")
            if r.installation_date:
                line += " on " + str(r.installation_date)[:10]
            parts.append(line)
    except Exception:
        pass
    return {"order_no": o.order_no, "customer_name": o.customer_name, "status": o.status, "order_date": str(o.order_date) if o.order_date else None, "text": "; ".join(parts)}


def _track_complaint(comp_no: str, mobile: Optional[str], db: Session) -> dict:
    if (comp_no or "").strip().lower() in ("", "na", "n/a", "none", "null", "0", "unknown", "-", "dontknow"):
        return _track_by_mobile(mobile, db)
    c = _find(db, comp_no, mobile)
    if c is None:
        alt = _track_by_identifier(comp_no, db)
        if alt is not None:
            return alt
        return {"success": False, "message": "No complaint found for this number", "data": {}}
    return _ok("Complaint found", {
        "comp_no": c.comp_no,
        "comp_date": str(c.comp_date),
        "status": c.status,
        "status_date": c.status_date.isoformat() if c.status_date else None,
        "query_type": c.query_type,
        "model_details": c.model_details,
        "problem": (c.problem_description or "")[:200],
    })


_NAME_STOP = {"pvt", "private", "ltd", "limited", "llp", "co", "company", "and", "the", "m/s", "ms", "mr", "mrs", "shri", "sri", "of", "india", "enterprises", "enterprise", "traders", "trading"}


def _name_tokens(s: Optional[str]) -> list:
    words = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
    return [w for w in words if w not in _NAME_STOP]


def _name_ok(caller: Optional[str], record: Optional[str]) -> bool:
    """Loose match of the firm/customer name spoken by the caller against the CRM record."""
    import difflib
    a, b = _name_tokens(caller), _name_tokens(record)
    if not a or not b:
        return False
    def has(tok, pool):
        return any(tok == x or difflib.SequenceMatcher(None, tok, x).ratio() >= 0.82 for x in pool)
    if all(has(x, b) for x in a):
        return True
    if all(has(x, a) for x in b):
        return True
    return False


_DENY = {"success": False, "message": "Unable to verify this request. Do not share any details; tell the caller you cannot share information without verification.", "data": {}}


def _vendor_name(order_no, db):
    try:
        from sqlalchemy import select
        from app.models.order import Order
        from app.models.vendor import Vendor
        return db.execute(select(Vendor.name_of_firm).join(Order, Order.vendor_id == Vendor.id).where(Order.order_no == order_no)).scalars().first()
    except Exception:
        return None


def _track_verified(key: str, name: Optional[str], db: Session) -> dict:
    """Order / GeM order / PI style identifiers: only answer if the caller's firm name matches the CRM record."""
    if not (name or "").strip():
        return _DENY
    parts = []
    first = None
    o = None
    try:
        o = _order_summary(key, db)
    except Exception:
        o = None
    if o and (_name_ok(name, o.get("customer_name")) or _name_ok(name, _vendor_name(o["order_no"], db))):
        parts.append(o["text"])
        first = {"comp_no": o["order_no"], "comp_date": o["order_date"], "status": o["status"], "query_type": "Order"}
    k = key.strip().lower()
    if len(k) >= 3:
        rows = db.execute(
            select(Complaint).where(Complaint.deleted_at.is_(None)).order_by(Complaint.id.desc()).limit(500)
        ).scalars().all()
        for c in [c for c in rows if k in (c.remark or "").lower() and _name_ok(name, c.customer_name)][:3]:
            parts.append("Complaint " + str(c.comp_no) + " status: " + str(c.status) + ", category " + str(c.query_type) + ", registered " + str(c.comp_date))
            if first is None:
                first = {"comp_no": c.comp_no, "comp_date": str(c.comp_date), "status": c.status, "query_type": c.query_type}
    if not parts:
        return _DENY
    return _ok(". ".join(parts), first)


def _track(comp_no: str, mobile: Optional[str], db: Session, name: Optional[str] = None) -> dict:
    if comp_no and "|" in comp_no:
        left, _, right = comp_no.partition("|")
        comp_no = left.strip()
        if not (name or "").strip():
            name = right.strip()
    kl = (comp_no or "").strip().lower()
    plain = kl in ("", "na", "n/a", "none", "null", "0", "unknown", "-", "dontknow") or kl.startswith("idc_") or "@" in kl
    if plain:
        return _track_complaint(comp_no, mobile, db)
    return _track_verified(comp_no, name, db)


@router.get("/complaints/track", dependencies=[Depends(require_key)])
def track_complaint(comp_no: str, mobile: Optional[str] = None, name: Optional[str] = None, db: Session = Depends(get_db)):
    return _track(comp_no, mobile, db, name)


@router.get("/complaints/{comp_no:path}", dependencies=[Depends(require_key)])
def track_complaint_by_path(comp_no: str, mobile: Optional[str] = None, name: Optional[str] = None, db: Session = Depends(get_db)):
    return _track(comp_no, mobile, db, name)
