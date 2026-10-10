"""Connections that bring enquiries into Sales: IndiaMART, Meta lead forms, a web address (webhook), any API, a
Google Sheet, a mailbox (for marketplaces that send an e-mail, such as Alibaba.com).

Every connection turns what it receives into the same small record (Incoming). Each one is then registered first in
the CRM as a Sales enquiry (an IDC_ number), and the lead is made from it, exactly as for a website enquiry.
Keys and passwords are stored encrypted and are never sent back to a browser.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.sales import crm_link, leads as L, types as T
from app.sales.models import SalesInbound, SalesInboxLog, SalesLead, SalesSource
from app.sales.secrets_box import seal, unseal

KINDS = {
    "indiamart": "IndiaMART",
    "meta": "Meta lead forms (Facebook and Instagram)",
    "webhook": "Web address (any form or tool that can post)",
    "api": "Any API (your own account with a supplier or marketplace)",
    "sheet": "Google Sheet (published as CSV)",
    "mailbox": "Mailbox (for marketplaces that send an e-mail: Alibaba.com, TradeWheel ...)",
}
PULL_KINDS = ("indiamart", "meta", "api", "sheet", "mailbox")
MIN_MINUTES = {"indiamart": 6, "meta": 5, "api": 5, "sheet": 5, "mailbox": 5}
CHANNEL = {"indiamart": "indiamart", "meta": "meta", "webhook": "webhook", "api": "api", "sheet": "file", "mailbox": "mail"}
ISO_COUNTRY = {"IN": "India", "NP": "Nepal", "LK": "Sri Lanka", "KE": "Kenya", "GH": "Ghana", "NG": "Nigeria", "TZ": "Tanzania", "UG": "Uganda", "BD": "Bangladesh", "AE": "United Arab Emirates"}
HTTP_TIMEOUT = 25


@dataclass
class Incoming:
    external_id: str | None = None
    name: str = ""
    phone: str = ""
    email: str = ""
    company: str = ""
    message: str = ""
    product: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    address: str = ""
    received_at: datetime | None = None
    extra: dict = field(default_factory=dict)


# ---------------- turning a flat record into an Incoming ----------------
def _k(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


GUESS = {
    "external_id": ["uniquequeryid", "id", "leadid", "queryid", "enquiryid", "inquiryid", "rfqid", "externalid", "ticketid", "referenceid"],
    "name": ["sendername", "name", "fullname", "contactname", "customername", "buyername", "contactperson", "person"],
    "phone": ["sendermobile", "mobile", "phone", "phonenumber", "mobilenumber", "contactnumber", "telephone", "whatsapp", "mobileno", "phoneno", "tel"],
    "email": ["senderemail", "email", "emailid", "mail", "emailaddress"],
    "company": ["sendercompany", "company", "companyname", "firm", "organization", "organisation"],
    "message": ["querymessage", "message", "requirement", "details", "comments", "remarks", "description", "enquiry", "inquiry", "body"],
    "product": ["queryproductname", "productname", "product", "item", "itemname", "subject"],
    "city": ["sendercity", "city", "town"],
    "state": ["senderstate", "state", "province"],
    "country": ["sendercountryiso", "sendercountry", "country", "countryname", "nation"],
    "address": ["senderaddress", "address"],
    "received_at": ["querytime", "createdtime", "createdat", "time", "date", "timestamp"],
}


def _dig(data, path: str):
    cur = data
    for part in [p for p in (path or "").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def _parse_time(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%d-%b-%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(text, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def country_name(value: str) -> str:
    v = (value or "").strip()
    return ISO_COUNTRY.get(v.upper(), v) if len(v) == 2 else v


def incoming_from_flat(record: dict, mapping: dict | None = None) -> Incoming | None:
    """mapping: our field -> the key (or a dotted path) in the record. Without it, the names are guessed."""
    if not isinstance(record, dict):
        return None
    flat = {_k(k): v for k, v in record.items() if not isinstance(v, (dict, list))}

    def get(field_name: str) -> str:
        if mapping and mapping.get(field_name):
            value = _dig(record, mapping[field_name])
            if value is None:
                value = flat.get(_k(mapping[field_name]))
            return "" if value is None else str(value).strip()
        for g in GUESS[field_name]:
            if g in flat and flat[g] not in (None, ""):
                return str(flat[g]).strip()
        return ""

    inc = Incoming(
        external_id=get("external_id") or None, name=get("name"), phone=get("phone"), email=get("email"), company=get("company"),
        message=get("message"), product=get("product"), city=get("city"), state=get("state"), country=country_name(get("country")),
        address=get("address"), received_at=_parse_time(get("received_at")),
    )
    if not inc.name and not inc.company and not inc.phone and not inc.email:
        return None
    if not inc.name:
        inc.name = inc.company or inc.email or inc.phone
    # a first name and a last name in separate fields
    if not (mapping and mapping.get("name")) and not get("name"):
        first, last = flat.get("firstname"), flat.get("lastname")
        if first or last:
            inc.name = f"{first or ''} {last or ''}".strip()
    return inc


# ---------------- the web (one place, so a test can replace it) ----------------
def http(method: str, url: str, *, params=None, headers=None, json_body=None, data=None):
    r = requests.request(method, url, params=params, headers=headers, json=json_body, data=data, timeout=HTTP_TIMEOUT)
    return r


def _json(r) -> object:
    try:
        return r.json()
    except ValueError:
        raise ValueError(f"The answer was not JSON (HTTP {r.status_code}): {(r.text or '')[:160]}")


# ---------------- IndiaMART ----------------
IM_URL = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"


def indiamart_records(payload) -> list[dict]:
    """IndiaMART answers {"CODE":200,"STATUS":"SUCCESS","RESPONSE":[...]} (pull) or posts {"RESPONSE":{...}} (push)."""
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        resp = payload.get("RESPONSE", payload)
        if isinstance(resp, list):
            return [p for p in resp if isinstance(p, dict)]
        if isinstance(resp, dict):
            return [resp]
    return []


def fetch_indiamart(cfg: dict, secret: dict, since: datetime | None) -> list[Incoming]:
    key = (secret.get("crm_key") or "").strip()
    if not key:
        raise ValueError("The IndiaMART CRM key is missing")
    end = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    start = max(since + timedelta(hours=5, minutes=30) - timedelta(days=1), end - timedelta(days=7)) if since else end - timedelta(days=2)
    r = http("GET", IM_URL, params={"glusr_crm_key": key, "start_time": start.strftime("%d-%b-%Y"), "end_time": end.strftime("%d-%b-%Y")})
    payload = _json(r)
    if isinstance(payload, dict) and str(payload.get("CODE", 200)) not in ("200",) and not payload.get("RESPONSE"):
        raise ValueError(f"IndiaMART said: {payload.get('MESSAGE') or payload.get('STATUS') or payload.get('CODE')}")
    out = []
    for rec in indiamart_records(payload):
        inc = incoming_from_flat(rec)
        if inc is None:
            continue
        qt = {"W": "Direct enquiry", "B": "Buy-lead", "P": "Call enquiry", "V": "WhatsApp enquiry", "BIZ": "Buy-lead"}.get(str(rec.get("QUERY_TYPE", "")).upper(), "")
        if qt:
            inc.extra["query_type"] = qt
        out.append(inc)
    return out


# ---------------- Meta lead forms ----------------
META_URL = "https://graph.facebook.com/v19.0"


def meta_incoming(lead: dict) -> Incoming | None:
    fields = {}
    for f in lead.get("field_data") or []:
        vals = f.get("values") or []
        fields[f.get("name", "")] = ", ".join(str(v) for v in vals)
    base = {_k(k): v for k, v in fields.items()}
    inc = incoming_from_flat({**fields, "id": lead.get("id")})
    if inc is None:
        return None
    inc.external_id = str(lead.get("id") or inc.external_id or "") or None
    inc.received_at = _parse_time(lead.get("created_time"))
    others = [f"{k}: {v}" for k, v in fields.items() if _k(k) not in {_k(x) for names in GUESS.values() for x in names} and v]
    ad = ", ".join(x for x in (lead.get("campaign_name") and f"campaign {lead['campaign_name']}", lead.get("ad_name") and f"ad {lead['ad_name']}", lead.get("form_id") and f"form {lead['form_id']}") if x)
    inc.message = " · ".join(x for x in [inc.message, "; ".join(others), f"Meta lead ad ({ad})" if ad else "Meta lead ad"] if x)
    if base.get("fullname") and not inc.name:
        inc.name = base["fullname"]
    return inc


def fetch_meta(cfg: dict, secret: dict, since: datetime | None) -> list[Incoming]:
    token = (secret.get("page_token") or "").strip()
    forms = cfg.get("form_ids") or []
    if isinstance(forms, str):
        forms = [x.strip() for x in re.split(r"[,\s]+", forms) if x.strip()]
    if not token or not forms:
        raise ValueError("The Meta page access token and at least one form number are needed")
    out: list[Incoming] = []
    for form in forms:
        params = {"access_token": token, "limit": 100, "fields": "id,created_time,field_data,ad_name,campaign_name,form_id"}
        if since:
            params["filtering"] = json.dumps([{"field": "time_created", "operator": "GREATER_THAN", "value": int((since - timedelta(hours=1)).timestamp())}])
        r = http("GET", f"{META_URL}/{form}/leads", params=params)
        payload = _json(r)
        if isinstance(payload, dict) and payload.get("error"):
            raise ValueError(f"Meta said: {payload['error'].get('message', 'error')}")
        for lead in (payload.get("data") or []) if isinstance(payload, dict) else []:
            inc = meta_incoming(lead)
            if inc:
                out.append(inc)
    return out


def fetch_meta_lead(secret: dict, leadgen_id: str) -> Incoming | None:
    token = (secret.get("page_token") or "").strip()
    if not token:
        raise ValueError("The Meta page access token is missing")
    r = http("GET", f"{META_URL}/{leadgen_id}", params={"access_token": token, "fields": "id,created_time,field_data,ad_name,campaign_name,form_id"})
    payload = _json(r)
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(f"Meta said: {payload['error'].get('message', 'error')}")
    return meta_incoming(payload) if isinstance(payload, dict) else None


# ---------------- any API ----------------
def fetch_api(cfg: dict, secret: dict, since: datetime | None) -> list[Incoming]:
    url = (cfg.get("url") or "").strip()
    if not url.lower().startswith("https://") and not url.lower().startswith("http://"):
        raise ValueError("The address of the API must start with https://")
    headers = {}
    if secret.get("header_name") and secret.get("header_value"):
        headers[secret["header_name"]] = secret["header_value"]
    params = dict(cfg.get("params") or {})
    if secret.get("query_key") and secret.get("query_value"):
        params[secret["query_key"]] = secret["query_value"]
    method = (cfg.get("method") or "GET").upper()
    r = http(method, url, params=params or None, headers=headers or None, json_body=cfg.get("body") if method == "POST" else None)
    if r.status_code >= 400:
        raise ValueError(f"The API answered HTTP {r.status_code}: {(r.text or '')[:160]}")
    payload = _json(r)
    items = _dig(payload, cfg.get("list_path") or "") if cfg.get("list_path") else payload
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("The list of enquiries was not found in the answer. Check the path to the list.")
    mapping = cfg.get("mapping") or None
    return [i for i in (incoming_from_flat(rec, mapping) for rec in items) if i]


# ---------------- Google Sheet published as CSV ----------------
def fetch_sheet(cfg: dict, secret: dict, since: datetime | None) -> list[Incoming]:
    url = (cfg.get("csv_url") or "").strip()
    if not url.lower().startswith("https://"):
        raise ValueError("The sheet address must start with https:// (use File, Share, Publish to the web, CSV)")
    r = http("GET", url)
    if r.status_code >= 400:
        raise ValueError(f"The sheet answered HTTP {r.status_code}. Is it published to the web?")
    text = r.content.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    mapping = cfg.get("mapping") or None
    out = []
    for rec in rows:
        inc = incoming_from_flat(rec, mapping)
        if inc and inc.phone:
            if not inc.external_id:
                inc.external_id = hashlib.sha1("|".join(str(v) for v in rec.values()).encode()).hexdigest()[:32]
            out.append(inc)
    return out


# ---------------- mailbox ----------------
LABELS = {
    "name": ["name", "contact name", "contact person", "buyer name", "from", "full name"],
    "phone": ["phone", "mobile", "tel", "telephone", "contact number", "whatsapp", "phone number", "mobile number"],
    "email": ["email", "e-mail", "email address"],
    "company": ["company", "company name", "organization"],
    "country": ["country", "country/region", "nation", "country or region"],
    "product": ["product", "product name", "item", "looking for", "keyword"],
    "quantity": ["quantity", "order quantity", "qty", "required quantity"],
    "message": ["message", "requirement", "details", "description", "inquiry details", "enquiry"],
}
PHONE_RE = re.compile(r"(?<![\w])(\+?\d[\d\s().-]{7,18}\d)(?![\w])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def parse_inquiry_mail(subject: str, sender: str, body: str, own_domains: list[str]) -> Incoming | None:
    """Reads the buyer's details out of a marketplace notification mail. Marketplaces write these mails in their own
    way, so this reads labelled lines ("Name: ...", "Country: ...") and falls back to the first phone number and
    e-mail address in the mail. The whole text is kept on the lead, so nothing is lost if a field is missed."""
    text = re.sub(r"<[^>]+>", "\n", body or "")
    text = re.sub(r"&nbsp;", " ", text)
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n")]
    found: dict[str, str] = {}
    for ln in lines:
        m = re.match(r"^\W*([A-Za-z][A-Za-z /_-]{1,30}?)\s*[:：=-]\s*(.+)$", ln)
        if not m:
            continue
        label, value = m.group(1).strip().lower(), m.group(2).strip()
        for field_name, names in LABELS.items():
            if label in names and field_name not in found and value:
                found[field_name] = value
    emails = [e for e in EMAIL_RE.findall(text) if not any(d and d in e.lower() for d in own_domains)]
    email = found.get("email") or (emails[0] if emails else "")
    phone = found.get("phone", "")
    if not phone:
        m = PHONE_RE.search(text)
        phone = m.group(1).strip() if m else ""
    product = found.get("product") or re.sub(r"^(re|fwd|fw):\s*", "", subject or "", flags=re.I)
    name = found.get("name") or found.get("company") or (email.split("@")[0] if email else "")
    if not name and not phone and not email:
        return None
    msg = found.get("message", "")
    qty = found.get("quantity")
    clean = " ".join(text.split())[:800]
    message = " · ".join(x for x in [msg, f"Quantity: {qty}" if qty else "", f"Mail: {subject}" if subject else "", "Please check the details against the mail:" + (" " + clean if not msg else "")] if x)
    return Incoming(
        name=name, phone=phone, email=email, company=found.get("company", ""), message=message[:1800], product=product[:200],
        country=country_name(found.get("country", "")), extra={"parsed_from_mail": True, "sender": sender},
    )


def fetch_mailbox(cfg: dict, secret: dict, since: datetime | None) -> list[Incoming]:
    import email as email_lib
    import imaplib
    from email.header import decode_header, make_header

    host, user = (cfg.get("host") or "").strip(), (cfg.get("user") or "").strip()
    password = secret.get("password") or ""
    if not host or not user or not password:
        raise ValueError("The mailbox server, the login and the password are needed")
    senders = [s.strip().lower() for s in re.split(r"[,\s]+", cfg.get("senders") or "") if s.strip()]
    own = [d.strip().lower() for d in re.split(r"[,\s]+", cfg.get("ignore_domains") or "") if d.strip()] + [x for x in senders]
    out: list[Incoming] = []
    box = imaplib.IMAP4_SSL(host, int(cfg.get("port") or 993), timeout=HTTP_TIMEOUT)
    try:
        box.login(user, password)
        box.select(cfg.get("folder") or "INBOX", readonly=True)
        crit = ["SINCE", (since or datetime.now(timezone.utc) - timedelta(days=14)).strftime("%d-%b-%Y")]
        status_, data = box.search(None, *crit)
        ids = (data[0] or b"").split()[-200:]
        for num in ids:
            status_, msg_data = box.fetch(num, "(RFC822)")
            if status_ != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email_lib.message_from_bytes(msg_data[0][1])
            sender = str(make_header(decode_header(msg.get("From", ""))))
            if senders and not any(s in sender.lower() for s in senders):
                continue
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            body = ""
            for part in msg.walk() if msg.is_multipart() else [msg]:
                ctype = part.get_content_type()
                if ctype in ("text/plain", "text/html"):
                    payload = part.get_payload(decode=True) or b""
                    text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    if ctype == "text/plain" or not body:
                        body = text
                    if ctype == "text/plain":
                        break
            inc = parse_inquiry_mail(subject, sender, body, own)
            if inc:
                inc.external_id = (msg.get("Message-ID") or hashlib.sha1(f"{sender}|{subject}|{msg.get('Date')}".encode()).hexdigest()).strip("<> ")[:150]
                inc.received_at = _parse_time(msg.get("Date")) or None
                inc.extra["mail_from"] = sender
                out.append(inc)
    finally:
        try:
            box.logout()
        except Exception:
            pass
    return out


FETCHERS = {"indiamart": fetch_indiamart, "meta": fetch_meta, "api": fetch_api, "sheet": fetch_sheet, "mailbox": fetch_mailbox}


# ---------------- a webhook that arrives ----------------
def incoming_from_webhook(src: SalesSource, payload) -> list[Incoming]:
    cfg, secret = jload(src.config), unseal(src.secret)
    if src.kind == "meta":
        out = []
        for entry in (payload.get("entry") or []) if isinstance(payload, dict) else []:
            for ch in entry.get("changes") or []:
                if ch.get("field") == "leadgen":
                    lead_id = (ch.get("value") or {}).get("leadgen_id")
                    if lead_id:
                        inc = fetch_meta_lead(secret, str(lead_id))
                        if inc:
                            out.append(inc)
        return out
    records: list[dict] = []
    if src.kind == "indiamart":
        records = indiamart_records(payload)
    elif isinstance(payload, list):
        records = [p for p in payload if isinstance(p, dict)]
    elif isinstance(payload, dict):
        for key in ("leads", "data", "items", "records", "RESPONSE"):
            if isinstance(payload.get(key), list):
                records = [p for p in payload[key] if isinstance(p, dict)]
                break
            if isinstance(payload.get(key), dict) and key != "data":
                records = [payload[key]]
                break
        if not records:
            records = [payload]
    mapping = cfg.get("mapping") or None
    return [i for i in (incoming_from_flat(r, mapping) for r in records[:200]) if i]


def jload(text: str | None) -> dict:
    try:
        v = json.loads(text) if text else {}
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


# ---------------- registered first, then lead ----------------
def _external_id(inc: Incoming) -> str:
    if inc.external_id:
        return str(inc.external_id)[:160]
    raw = "|".join([inc.phone, inc.email, inc.message, inc.product, inc.received_at.isoformat() if inc.received_at else ""])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def ingest(main_db: Session, sdb: Session, src: SalesSource, items: list[Incoming]) -> dict:
    stats = {"new": 0, "again": 0, "skipped": 0, "no_phone": 0}
    label = src.name or KINDS.get(src.kind, src.kind)
    for inc in items:
        ext = _external_id(inc)
        if sdb.scalar(select(SalesInbound.id).where(SalesInbound.source_id == src.id, SalesInbound.external_id == ext)):
            stats["skipped"] += 1
            continue
        phone = L.norm_phone(inc.phone)
        if len(phone) < 7:
            sdb.add(SalesInbound(source_id=src.id, external_id=ext))
            sdb.add(SalesInboxLog(source=label, crm_ref=None, result=f"No phone number on the enquiry from {inc.name or inc.company or 'a buyer'}: no lead made. Their e-mail: {inc.email or 'not given'}"))
            stats["no_phone"] += 1
            continue
        place = ", ".join(x for x in (inc.city, inc.state, inc.country) if x)
        message = " · ".join(x for x in [inc.message, f"Wants: {inc.product}" if inc.product else "", f"Company: {inc.company}" if inc.company else ""] if x) or "-"
        c = crm_link.register_enquiry(
            main_db, name=inc.name or inc.company, mobile=phone, email=inc.email or None, message=message,
            address=", ".join(x for x in (inc.address, place) if x) or None, state=(inc.state if (inc.country or "India").lower() == "india" else inc.country) or None,
            source_key=CHANNEL.get(src.kind, src.kind), source_label=label,
        )
        main_db.commit()  # the CRM keeps the enquiry first, whatever happens next
        lead = sdb.scalar(select(SalesLead).where(SalesLead.crm_kind == "complaint", SalesLead.crm_ref == c.comp_no))
        created = False
        if lead is None:
            details = " · ".join(x for x in [inc.company, inc.country, inc.extra.get("query_type")] if x) or None
            lead, created = L.create_lead(main_db, sdb, {
                "name": inc.name or inc.company, "phone": phone, "email": inc.email or None, "item": inc.product or inc.message[:200], "message": message,
                "place": place or None, "state": inc.state or None, "district": inc.city or None, "country": inc.country or None,
                "source": label, "channel": CHANNEL.get(src.kind, "api"), "details": details,
                "lead_type": src.default_lead_type, "owner_user_id": src.default_owner_user_id,
                "crm_kind": "complaint", "crm_ref": c.comp_no, "crm_id": c.id,
            })
        else:
            created = True
            _enrich(sdb, lead, src, label, inc, place)
        stats["new" if created else "again"] += 1
        sdb.add(SalesInbound(source_id=src.id, external_id=ext, lead_id=lead.id, crm_ref=c.comp_no))
        sdb.add(SalesInboxLog(source=label, crm_ref=c.comp_no, lead_id=lead.id, result=(
            f"Registered as {c.comp_no}, lead {lead.lead_no} made for {lead.name} ({T.label_of(sdb, lead.lead_type)})" if created
            else f"Registered as {c.comp_no}. Same phone as lead {lead.lead_no}: added to its history, no new lead")))
        src.received_count = (src.received_count or 0) + 1
        sdb.flush()
    return stats


def _enrich(sdb: Session, lead: SalesLead, src: SalesSource, label: str, inc: Incoming, place: str) -> None:
    """The sync made the lead first from the bare CRM record: put in what the connection knows."""
    lead.source, lead.channel = label, CHANNEL.get(src.kind, "api")
    if inc.country:
        lead.country = inc.country
    if inc.product:
        lead.item = inc.product[:500]
    if src.default_lead_type and T.valid_type(sdb, src.default_lead_type):
        lead.lead_type = src.default_lead_type
    lead.details = " · ".join(x for x in [inc.company, inc.country] if x) or lead.details
    if src.default_owner_user_id and not lead.owner_user_id:
        lead.owner_user_id = src.default_owner_user_id
    L.refresh_priority(lead, force=True)


# ---------------- running the pull connections ----------------
def due(src: SalesSource, now: datetime) -> bool:
    if not src.is_active or src.kind not in PULL_KINDS:
        return False
    if src.last_run_at is None:
        return True
    last = L.aware(src.last_run_at)
    return now - last >= timedelta(minutes=max(MIN_MINUTES.get(src.kind, 5), src.interval_minutes or 15))


def run_source(main_db: Session, sdb: Session, src: SalesSource, *, dry: bool = False) -> dict:
    cfg, secret = jload(src.config), unseal(src.secret)
    now = L.now()
    try:
        items = FETCHERS[src.kind](cfg, secret, L.aware(src.last_ok_at))
    except Exception as exc:  # the answer of another company's server can be anything
        if not dry:
            src.last_run_at, src.last_error = now, str(exc)[:500]
        return {"ok": False, "error": str(exc)[:500], "count": 0}
    if dry:
        return {"ok": True, "count": len(items), "sample": [f"{i.name or i.company} ({i.country or i.city or 'place not given'}): {i.product or i.message[:60]}" for i in items[:3]]}
    stats = ingest(main_db, sdb, src, items)
    src.last_run_at, src.last_ok_at, src.last_error = now, now, None
    return {"ok": True, "count": len(items), **stats}


def run_due_sources(main_db: Session, sdb: Session) -> int:
    n = 0
    now = L.now()
    for src in list(sdb.scalars(select(SalesSource).where(SalesSource.is_active.is_(True)))):
        if due(src, now):
            try:
                run_source(main_db, sdb, src)
                sdb.commit()
                main_db.commit()
                n += 1
            except Exception:
                sdb.rollback()
                main_db.rollback()
    return n


def new_token() -> str:
    return secrets.token_hex(24)
