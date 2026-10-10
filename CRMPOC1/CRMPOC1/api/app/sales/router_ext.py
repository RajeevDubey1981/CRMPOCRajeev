"""Lead types, connections (sources), the public web addresses they use, file upload and the export-market lists."""

import json
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.sales import crm_link, importer, leads as L, sources as S, types as T
from app.sales.access import Ctx, get_ctx, require
from app.sales.db import get_sales_db
from app.sales.models import SalesInbound, SalesInboxLog, SalesLeadType, SalesProspect, SalesSource
from app.sales.secrets_box import seal, unseal

router = APIRouter(prefix="/api/sales", tags=["sales"])


def commit(main_db: Session, sdb: Session) -> None:
    sdb.commit()
    main_db.commit()


def need_admin(ctx: Ctx) -> None:
    if not ctx.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin and Sub Admin do this")


# ======================= lead types =======================
class TypeIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    color: str = "#475569"


class TypePatch(BaseModel):
    label: Optional[str] = Field(default=None, min_length=2, max_length=80)
    color: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/types")
def list_types(ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db)):
    used = dict(sdb.execute(select(L.SalesLead.lead_type, func.count()).group_by(L.SalesLead.lead_type)).all())
    return [{**t, "used": used.get(t["key"], 0)} for t in T.type_map(sdb).values()]


@router.post("/types", status_code=201)
def add_type(body: TypeIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    need_admin(ctx)
    label = body.label.strip()
    if any(t["label"].lower() == label.lower() for t in T.type_map(sdb).values()):
        raise HTTPException(400, "There is already a type with this name")
    key = T.make_key(sdb, label)
    top = max([t["sort_order"] for t in T.type_map(sdb).values()] + [0])
    sdb.add(SalesLeadType(key=key, label=label, color=T.clean_color(body.color), sort_order=top + 10, is_active=True, is_builtin=False))
    sdb.info.pop("types_cache", None)
    commit(main_db, sdb)
    return T.type_map(sdb)[key]


@router.patch("/types/{key}")
def patch_type(key: str, body: TypePatch, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    need_admin(ctx)
    row = sdb.get(SalesLeadType, key)
    if row is None:
        raise HTTPException(404, "Type not found")
    data = body.model_dump(exclude_unset=True)
    if "label" in data:
        label = data["label"].strip()
        if any(t["label"].lower() == label.lower() and t["key"] != key for t in T.type_map(sdb).values()):
            raise HTTPException(400, "There is already a type with this name")
        row.label = label
    if "color" in data:
        row.color = T.clean_color(data["color"])
    if "sort_order" in data:
        row.sort_order = int(data["sort_order"])
    if data.get("is_active") is False and row.is_active:
        if len(T.active_types(sdb)) <= 1:
            raise HTTPException(400, "At least one lead type must stay on")
        row.is_active = False
    elif data.get("is_active") is True:
        row.is_active = True
    sdb.info.pop("types_cache", None)
    commit(main_db, sdb)
    return T.type_map(sdb)[key]


# ======================= connections =======================
class SourceIn(BaseModel):
    kind: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=120)
    config: Optional[dict] = None
    secret: Optional[dict] = None
    default_lead_type: Optional[str] = None
    default_owner_user_id: Optional[int] = None
    interval_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    is_active: Optional[bool] = None


SECRET_FIELDS = {
    "indiamart": ["crm_key"], "meta": ["page_token", "verify_token"], "api": ["header_name", "header_value", "query_key", "query_value"],
    "mailbox": ["password"], "sheet": [], "webhook": [],
}
CONFIG_FIELDS = {
    "indiamart": ["mode"], "meta": ["form_ids"], "webhook": ["mapping"],
    "api": ["url", "method", "list_path", "mapping", "params", "body"], "sheet": ["csv_url", "mapping"],
    "mailbox": ["host", "port", "user", "folder", "senders", "ignore_domains"],
}


def source_out(src: SalesSource) -> dict:
    cfg, secret = S.jload(src.config), unseal(src.secret)
    base = (settings.app_public_url or "").rstrip("/")
    return {
        "id": src.id, "kind": src.kind, "kind_label": S.KINDS.get(src.kind, src.kind), "name": src.name, "is_active": src.is_active,
        "config": cfg, "secret_set": {k: bool(secret.get(k)) for k in SECRET_FIELDS.get(src.kind, [])},
        "default_lead_type": src.default_lead_type, "default_owner_user_id": src.default_owner_user_id,
        "interval_minutes": src.interval_minutes, "pulls": src.kind in S.PULL_KINDS,
        "webhook_path": f"/api/sales/in/{src.token}", "webhook_url": f"{base}/api/sales/in/{src.token}" if base else None,
        "verify_token_set": bool(secret.get("verify_token")) if src.kind == "meta" else None,
        "last_run_at": L.aware(src.last_run_at).isoformat() if src.last_run_at else None,
        "last_ok_at": L.aware(src.last_ok_at).isoformat() if src.last_ok_at else None,
        "last_error": src.last_error, "received_count": src.received_count,
    }


def _check_and_store(sdb: Session, src: SalesSource, body: SourceIn, creating: bool) -> None:
    kind = src.kind
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] and data["name"].strip():
        src.name = data["name"].strip()
    if "default_lead_type" in data:
        dt = data["default_lead_type"] or None
        if dt and not T.valid_type(sdb, dt):
            raise HTTPException(400, "Unknown lead type")
        src.default_lead_type = dt
    if "default_owner_user_id" in data:
        src.default_owner_user_id = data["default_owner_user_id"] or None
    if "interval_minutes" in data and data["interval_minutes"]:
        src.interval_minutes = max(S.MIN_MINUTES.get(kind, 5), int(data["interval_minutes"]))
    if "is_active" in data and data["is_active"] is not None:
        src.is_active = bool(data["is_active"])
    cfg = S.jload(src.config)
    if body.config is not None:
        for k in CONFIG_FIELDS.get(kind, []):
            if k in body.config:
                cfg[k] = body.config[k]
    secret = unseal(src.secret)
    if body.secret is not None:
        for k in SECRET_FIELDS.get(kind, []):
            v = body.secret.get(k)
            if isinstance(v, str) and v.strip():
                secret[k] = v.strip()
    # what each kind must have before it can be switched on
    problems = []
    if kind == "indiamart" and (cfg.get("mode") or "pull") in ("pull", "both") and not secret.get("crm_key"):
        problems.append("the IndiaMART CRM key")
    if kind == "meta":
        if not secret.get("page_token"):
            problems.append("the Meta page access token")
        if not secret.get("verify_token"):
            secret["verify_token"] = S.new_token()[:24]
        if isinstance(cfg.get("form_ids"), str):
            cfg["form_ids"] = [x for x in re.split(r"[,\s]+", cfg["form_ids"]) if x]
    if kind == "api":
        if not str(cfg.get("url") or "").lower().startswith(("https://", "http://")):
            problems.append("the address of the API (it starts with https://)")
        if (cfg.get("method") or "GET").upper() not in ("GET", "POST"):
            problems.append("the method (GET or POST)")
    if kind == "sheet" and not str(cfg.get("csv_url") or "").lower().startswith("https://"):
        problems.append("the address of the published sheet (it starts with https://)")
    if kind == "mailbox":
        for k, label in (("host", "the mail server"), ("user", "the mailbox login")):
            if not str(cfg.get(k) or "").strip():
                problems.append(label)
        if not secret.get("password"):
            problems.append("the mailbox password")
    if problems:
        raise HTTPException(400, "Still needed: " + ", ".join(problems))
    src.config = json.dumps(cfg, ensure_ascii=False)
    src.secret = seal(secret)


@router.get("/sources")
def list_sources(ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db)):
    return {"kinds": [{"key": k, "label": v, "pulls": k in S.PULL_KINDS} for k, v in S.KINDS.items()],
            "items": [source_out(s) for s in sdb.scalars(select(SalesSource).order_by(SalesSource.id))]}


@router.post("/sources", status_code=201)
def add_source(body: SourceIn, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    if body.kind not in S.KINDS:
        raise HTTPException(400, "Choose the kind of connection")
    src = SalesSource(kind=body.kind, name=(body.name or S.KINDS[body.kind]).strip(), token=S.new_token(), created_by=ctx.user.id, config="{}", interval_minutes=15)
    _check_and_store(sdb, src, body, True)
    sdb.add(src)
    sdb.flush()
    commit(main_db, sdb)
    return source_out(src)


@router.patch("/sources/{sid}")
def patch_source(sid: int, body: SourceIn, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    src = sdb.get(SalesSource, sid)
    if src is None:
        raise HTTPException(404, "Connection not found")
    _check_and_store(sdb, src, body, False)
    commit(main_db, sdb)
    return source_out(src)


@router.delete("/sources/{sid}")
def delete_source(sid: int, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    src = sdb.get(SalesSource, sid)
    if src is None:
        raise HTTPException(404, "Connection not found")
    sdb.execute(delete(SalesInbound).where(SalesInbound.source_id == sid))
    sdb.delete(src)
    commit(main_db, sdb)
    return {"deleted": True}


@router.post("/sources/{sid}/new-token")
def new_token(sid: int, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    src = sdb.get(SalesSource, sid)
    if src is None:
        raise HTTPException(404, "Connection not found")
    src.token = S.new_token()
    commit(main_db, sdb)
    return source_out(src)


@router.post("/sources/{sid}/test")
def test_source(sid: int, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    """Asks the other side what it has, without making any lead."""
    src = sdb.get(SalesSource, sid)
    if src is None:
        raise HTTPException(404, "Connection not found")
    if src.kind not in S.PULL_KINDS:
        return {"ok": True, "count": 0, "message": "This connection waits for the other side to post to its web address. Send a test from there."}
    return S.run_source(main_db, sdb, src, dry=True)


@router.post("/sources/{sid}/run")
def run_source(sid: int, ctx: Ctx = Depends(require("connect")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    src = sdb.get(SalesSource, sid)
    if src is None:
        raise HTTPException(404, "Connection not found")
    if src.kind not in S.PULL_KINDS:
        raise HTTPException(400, "This connection waits for the other side to post to its web address")
    out = S.run_source(main_db, sdb, src)
    commit(main_db, sdb)
    return out


# ---- the public addresses the other side posts to (the long random token in the address is the key) ----
@router.get("/in/{token}")
def inbound_verify(token: str, request: Request, sdb: Session = Depends(get_sales_db)):
    """Meta checks a new webhook with a GET and expects its challenge text back."""
    src = sdb.scalar(select(SalesSource).where(SalesSource.token == token))
    if src is None or not src.is_active:
        raise HTTPException(404, "Not found")
    q = request.query_params
    if q.get("hub.mode") == "subscribe":
        expected = unseal(src.secret).get("verify_token") or ""
        if expected and q.get("hub.verify_token") == expected:
            return Response(content=q.get("hub.challenge", ""), media_type="text/plain")
        raise HTTPException(403, "The verify token does not match")
    return {"ok": True, "message": "This address is ready. The other side posts its enquiries here."}


@router.post("/in/{token}")
async def inbound_post(token: str, request: Request, sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    src = sdb.scalar(select(SalesSource).where(SalesSource.token == token))
    if src is None or not src.is_active:
        raise HTTPException(404, "Not found")
    raw = await request.body()
    if len(raw) > 262144:
        raise HTTPException(413, "Too large")
    ctype = request.headers.get("content-type", "")
    try:
        if "json" in ctype or raw[:1] in (b"{", b"["):
            payload = json.loads(raw.decode("utf-8") or "{}")
        else:
            form = await request.form()
            payload = {k: v for k, v in form.items() if isinstance(v, str)}
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "The body could not be read")
    try:
        items = S.incoming_from_webhook(src, payload)
    except ValueError as exc:
        src.last_error = str(exc)[:500]
        sdb.commit()
        raise HTTPException(502, str(exc))
    stats = S.ingest(main_db, sdb, src, items)
    src.last_run_at = src.last_ok_at = L.now()
    src.last_error = None
    commit(main_db, sdb)
    return {"ok": True, "received": len(items), **stats}


# ======================= upload a file =======================
def _num(text: str):
    try:
        return float(re.sub(r"[^\d.\-]", "", text or "")) if re.search(r"\d", text or "") else None
    except ValueError:
        return None


@router.post("/uploads/preview")
async def upload_preview(file: UploadFile = File(...), ctx: Ctx = Depends(require("upload", "exp_search"))):
    data = await file.read()
    cols, rows = importer.read_table(file.filename or "", data)
    return {"filename": file.filename, "columns": cols, "total": len(rows), "sample": rows[:5], "mapping": importer.guess_mapping(cols)}


@router.post("/uploads/import")
async def upload_import(
    file: UploadFile = File(...), options: str = Form("{}"), ctx: Ctx = Depends(get_ctx),
    sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db),
):
    try:
        opts = json.loads(options or "{}")
    except ValueError:
        raise HTTPException(400, "The options could not be read")
    mode = opts.get("mode") or "leads"
    if mode == "prospects":
        if not ctx.has("exp_search"):
            raise HTTPException(403, "You do not have this tick in Sales")
    elif not ctx.has("upload"):
        raise HTTPException(403, "You do not have this tick in Sales")
    cols, rows = importer.read_table(file.filename or "", await file.read())
    mapping = {k: v for k, v in (opts.get("mapping") or {}).items() if v in cols}
    label = (opts.get("source_label") or "").strip() or f"Excel: {file.filename}"
    errors: list[str] = []
    if mode == "prospects":
        batch = datetime.utcnow().strftime("b%Y%m%d%H%M%S")
        added = dup = 0
        have = {(c.lower(), k.lower()) for c, k in sdb.execute(select(SalesProspect.company, SalesProspect.country)).all()}
        for i, row in enumerate(rows, start=2):
            company = importer.pick(row, mapping, "company") or importer.pick(row, mapping, "name")
            country = importer.pick(row, mapping, "country") or (opts.get("country") or "").strip()
            if not company or not country:
                if len(errors) < 20:
                    errors.append(f"Row {i}: the company and the country are needed")
                continue
            if (company.lower(), country.lower()) in have:
                dup += 1
                continue
            have.add((company.lower(), country.lower()))
            sdb.add(SalesProspect(
                company=company[:255], contact_name=(importer.pick(row, mapping, "name") if mapping.get("company") else "")[:255] or None,
                phone=(importer.pick(row, mapping, "phone") or None), email=(importer.pick(row, mapping, "email") or None), country=country[:100],
                city=(importer.pick(row, mapping, "place") or None), kind=(importer.pick(row, mapping, "kind") or opts.get("kind") or None),
                products=(importer.pick(row, mapping, "item") or None), why=(importer.pick(row, mapping, "why") or None),
                source=label[:120], batch=batch,
            ))
            added += 1
        sdb.add(SalesInboxLog(source=label, result=f"Company list loaded: {added} companies added, {dup} already there ({file.filename})"))
        commit(main_db, sdb)
        return {"mode": mode, "batch": batch, "added": added, "duplicates": dup, "errors": errors}

    created = again = 0
    owner = opts.get("owner_user_id") or None
    lead_type = opts.get("lead_type") or None
    if lead_type and not T.valid_type(sdb, lead_type):
        raise HTTPException(400, "Unknown lead type")
    for i, row in enumerate(rows, start=2):
        name = importer.pick(row, mapping, "name") or importer.pick(row, mapping, "company")
        phone = importer.pick(row, mapping, "phone")
        if not name or len(L.norm_phone(phone)) < 7:
            if len(errors) < 20:
                errors.append(f"Row {i}: the name and a phone number are needed")
            continue
        company = importer.pick(row, mapping, "company")
        country = importer.pick(row, mapping, "country")
        place = ", ".join(x for x in (importer.pick(row, mapping, "place"), importer.pick(row, mapping, "state"), country) if x)
        value = _num(importer.pick(row, mapping, "value_lakh"))
        data = {
            "name": name, "phone": phone, "email": importer.pick(row, mapping, "email") or None, "item": importer.pick(row, mapping, "item")[:500],
            "message": importer.pick(row, mapping, "message") or None, "place": place or None, "state": importer.pick(row, mapping, "state") or None,
            "district": importer.pick(row, mapping, "place") or None, "pincode": (importer.pick(row, mapping, "pincode") or None),
            "country": country or None, "details": " · ".join(x for x in [company, country] if x) or None, "source": label, "channel": "file",
            "lead_type": lead_type, "owner_user_id": owner, "value_lakh": value,
        }
        lead, was_new = L.create_lead(main_db, sdb, data, ctx.user)
        created += 1 if was_new else 0
        again += 0 if was_new else 1
    sdb.add(SalesInboxLog(source=label, result=f"File loaded by {ctx.user.name}: {created} leads made, {again} already open for the same phone, {len(rows) - created - again} rows skipped ({file.filename})"))
    commit(main_db, sdb)
    return {"mode": mode, "created": created, "again": again, "skipped": len(rows) - created - again, "errors": errors}


# ======================= export-market lists =======================
def prospect_out(p: SalesProspect) -> dict:
    return {
        "id": p.id, "company": p.company, "contact_name": p.contact_name, "phone": p.phone, "email": p.email, "country": p.country, "city": p.city,
        "kind": p.kind, "products": p.products, "source": p.source, "why": p.why, "batch": p.batch, "lead_id": p.lead_id,
    }


@router.get("/prospects")
def list_prospects(
    country: str = "", kind: str = "", product: str = "", q: str = "", batch: str = "", open_only: bool = False,
    limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
    ctx: Ctx = Depends(require("exp_search")), sdb: Session = Depends(get_sales_db),
):
    stmt = select(SalesProspect)
    if country:
        stmt = stmt.where(func.lower(SalesProspect.country) == country.lower())
    if kind:
        stmt = stmt.where(func.lower(SalesProspect.kind) == kind.lower())
    if product:
        stmt = stmt.where(func.lower(SalesProspect.products).like(f"%{product.lower()}%"))
    if batch:
        stmt = stmt.where(SalesProspect.batch == batch)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(SalesProspect.company).like(like) | func.lower(func.coalesce(SalesProspect.city, "")).like(like))
    if open_only:
        stmt = stmt.where(SalesProspect.lead_id.is_(None))
    total = sdb.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = sdb.scalars(stmt.order_by(SalesProspect.id.desc()).limit(limit).offset(offset))
    return {"total": total, "items": [prospect_out(p) for p in rows]}


@router.get("/prospects/facets")
def prospect_facets(ctx: Ctx = Depends(require("exp_search")), sdb: Session = Depends(get_sales_db)):
    def col(c):
        return [r for (r,) in sdb.execute(select(c).where(c.isnot(None), c != "").distinct().order_by(c))]
    batches = sdb.execute(select(SalesProspect.batch, SalesProspect.source, func.count()).group_by(SalesProspect.batch, SalesProspect.source).order_by(SalesProspect.batch.desc())).all()
    return {"countries": col(SalesProspect.country), "kinds": col(SalesProspect.kind), "batches": [{"batch": b, "source": s, "count": n} for b, s, n in batches]}


class MakeLeadsIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


@router.post("/prospects/make-leads")
def prospects_make_leads(body: MakeLeadsIn, ctx: Ctx = Depends(require("exp_search")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    made = linked = no_phone = 0
    for p in sdb.scalars(select(SalesProspect).where(SalesProspect.id.in_(body.ids))):
        if p.lead_id:
            continue
        if len(L.norm_phone(p.phone or "")) < 7:
            no_phone += 1
            continue
        lead, new = L.create_lead(main_db, sdb, {
            "name": p.contact_name or p.company, "phone": p.phone, "email": p.email, "item": ("Prospect: " + (p.products or "products to be asked"))[:500],
            "place": ", ".join(x for x in (p.city, p.country) if x), "country": p.country, "district": p.city, "source": p.source or "Search", "channel": "search",
            "lead_type": "export", "is_prospect": True, "heat": "cold", "heat_why": ["Found by search, has not asked us yet"],
            "details": " · ".join(x for x in ["Found by search", p.company, p.kind, p.why] if x), "value_lakh": None,
        }, ctx.user)
        p.lead_id = lead.id
        made += 1 if new else 0
        linked += 0 if new else 1
    commit(main_db, sdb)
    return {"made": made, "linked_to_existing": linked, "no_phone": no_phone}


@router.delete("/prospects/batch/{batch}")
def delete_prospect_batch(batch: str, ctx: Ctx = Depends(require("exp_search")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    """Removes a list that was loaded by mistake. Companies that already became a lead are kept."""
    res = sdb.execute(delete(SalesProspect).where(SalesProspect.batch == batch, SalesProspect.lead_id.is_(None)))
    commit(main_db, sdb)
    return {"deleted": res.rowcount}
