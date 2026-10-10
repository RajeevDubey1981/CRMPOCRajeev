from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.sales import crm_link, leads as L, quotes as Q, types as T
from app.sales.access import Ctx, get_ctx, menu_flags, require, role_ticks, user_ticks, has_sales_menu
from app.sales.db import get_sales_db
from app.sales.models import (
    SalesInboxLog, SalesLead, SalesLeadActivity, SalesProfile, SalesQuotation, SalesRoleTick, SalesTickHistory, SalesUserTick,
)
from app.sales.rules import (
    ALL_TICKS, CLOSED_STATUSES, DISPOSALS, HEAT_RULES, HEAT_ORDER, LOCKED_TICKS, PRIORITY_ORDER, QUOTE_STATUSES,
    STATUSES, TICK_DEFAULTS, TICK_GROUPS,
)
from app.sales.summary import summary as build_summary
from app.sales.sync import sync_now

router = APIRouter(prefix="/api/sales", tags=["sales"])


# ---------------- request bodies ----------------
class LeadIn(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    item: str = ""
    place: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    lead_type: Optional[str] = None
    details: Optional[str] = None
    message: Optional[str] = None
    value_lakh: Optional[float] = None
    value_usd: Optional[float] = None
    price_basis: Optional[str] = None
    closes_on: Optional[date] = None
    source: Optional[str] = None


class LeadPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    item: Optional[str] = None
    place: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    lead_type: Optional[str] = None
    details: Optional[str] = None
    value_lakh: Optional[float] = None
    value_usd: Optional[float] = None
    price_basis: Optional[str] = None
    closes_on: Optional[date] = None


class GiveIn(BaseModel):
    owner_user_id: Optional[int] = None


class CallIn(BaseModel):
    outcome: str = "Spoke"
    note: str = ""
    next_follow_up: Optional[date] = None
    answers: Optional[dict] = None
    heat: Optional[str] = None
    why: str = ""


class RateIn(BaseModel):
    answers: dict = Field(default_factory=dict)
    heat: Optional[str] = None
    why: str = ""


class PriorityIn(BaseModel):
    level: str
    why: str = ""
    flag: bool = False


class StageIn(BaseModel):
    stage: str
    note: str = ""


class DisposeIn(BaseModel):
    reason: str
    note: str = ""
    order_no: Optional[str] = None


class SyncIn(BaseModel):
    backfill_days: Optional[int] = Field(default=None, ge=1, le=180)


class QuoteLineIn(BaseModel):
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    hsn: Optional[str] = None
    qty: float = 1
    rate: Optional[float] = None
    discount_pct: float = 0
    gst_pct: Optional[float] = None


class QuoteIn(BaseModel):
    items: Optional[list[QuoteLineIn]] = None


class QuotePatch(BaseModel):
    party: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    gstin: Optional[str] = None
    valid_days: Optional[int] = Field(default=None, ge=1, le=365)
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    warranty_terms: Optional[str] = None
    reference_line: Optional[str] = None
    note: Optional[str] = None
    items: Optional[list[QuoteLineIn]] = None


class ActionIn(BaseModel):
    reason: str = ""


class ProfilePatch(BaseModel):
    phone: Optional[str] = None
    pincode: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    extra_pincodes: Optional[str] = None
    areas: Optional[str] = None
    types_handled: Optional[str] = None
    target_lakh: Optional[float] = None
    is_active: Optional[bool] = None


class TicksIn(BaseModel):
    ticks: dict[str, Optional[bool]]


class SettingsIn(BaseModel):
    fx_rate: Optional[float] = Field(default=None, gt=0, le=1000)
    discount_limit: Optional[float] = Field(default=None, ge=0, le=40)
    home_state: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_gstin: Optional[str] = None


# ---------------- helpers ----------------
def commit(main_db: Session, sdb: Session) -> None:
    sdb.commit()
    main_db.commit()


def get_lead(sdb: Session, lead_id: int) -> SalesLead:
    lead = sdb.get(SalesLead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return lead


def visible(ctx: Ctx, lead: SalesLead) -> bool:
    return ctx.has("see_all") or lead.owner_user_id == ctx.user.id


def get_visible_lead(sdb: Session, ctx: Ctx, lead_id: int) -> SalesLead:
    lead = get_lead(sdb, lead_id)
    if not visible(ctx, lead):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return lead


def names_for(main_db: Session, *id_lists) -> dict[int, str]:
    ids: set[int] = set()
    for lst in id_lists:
        ids |= {i for i in lst if i}
    return crm_link.user_names(main_db, ids)


# ---------------- status ----------------
@router.get("/status")
def sales_status(ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db)):
    return {
        "enabled": True,
        "is_admin": ctx.is_admin,
        "ticks": sorted(ctx.ticks),
        "menu": menu_flags(ctx),
        "settings": {
            "fx_rate": float(L.get_setting(sdb, "fx_rate")), "discount_limit": float(L.get_setting(sdb, "discount_limit")),
            "home_state": L.get_setting(sdb, "home_state"), "company_name": L.get_setting(sdb, "company_name"),
            "company_address": L.get_setting(sdb, "company_address"), "company_gstin": L.get_setting(sdb, "company_gstin"),
        },
        "lead_types": [{"key": t["key"], "label": t["label"], "color": t["color"]} for t in T.active_types(sdb)],
        "statuses": STATUSES,
        "disposals": [{"key": k, "label": v[0], "needs_review": v[1], "crm_only": k in ("pr_won", "pr_can")} for k, v in DISPOSALS.items()],
        "heat_rules": [{"key": k, "label": lb, "points": pts} for k, lb, pts in HEAT_RULES],
        "quote_statuses": QUOTE_STATUSES,
    }


@router.get("/enabled")
def sales_enabled_flag(_: User = Depends(get_current_user)):
    from app.sales.db import sales_enabled
    return {"enabled": sales_enabled()}


# ---------------- leads ----------------
@router.get("/leads")
def list_leads(
    q: str = "", status_: str = Query("", alias="status"), lead_type: str = "", heat: str = "", priority: str = "", owner: str = "",
    source: str = "", kpi: str = "", sort: str = "pri", limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
    ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db),
):
    rows = list(sdb.scalars(select(SalesLead)))
    if not ctx.has("see_all"):
        rows = [r for r in rows if r.owner_user_id == ctx.user.id]
    today = date.today()
    now_ = L.now()

    def open_(r):
        return r.status not in CLOSED_STATUSES

    counts = {
        "all": len(rows),
        "open": len([r for r in rows if open_(r)]),
        "hot": len([r for r in rows if open_(r) and r.heat == "hot"]),
        "urgent": len([r for r in rows if open_(r) and r.priority in ("urgent", "high")]),
        "new": len([r for r in rows if r.status == "new"]),
        "unassigned": len([r for r in rows if open_(r) and r.owner_user_id is None]),
        "due_today": len([r for r in rows if open_(r) and r.follow_up_on == today]),
        "overdue": len([r for r in rows if open_(r) and r.follow_up_on and r.follow_up_on < today]),
        "first_overdue": len([r for r in rows if r.status == "new" and r.first_call_due_at and L.aware(r.first_call_due_at) < now_]),
        "not_attended": len([r for r in rows if open_(r) and r.owner_user_id is not None and r.last_action_at is None]),
        "quo": len([r for r in rows if r.status == "quo"]),
        "rev": len([r for r in rows if r.status == "rev"]),
    }

    def keep(r: SalesLead) -> bool:
        if q:
            hay = f"{r.name} {r.phone} {r.item} {r.place} {r.lead_no} {r.crm_ref}".lower()
            if q.lower() not in hay:
                return False
        if status_ == "open" and not open_(r):
            return False
        if status_ == "closed" and open_(r):
            return False
        if status_ in STATUSES and r.status != status_:
            return False
        if lead_type and r.lead_type != lead_type:
            return False
        if heat and (r.heat != heat or not open_(r)):
            return False
        if priority and (r.priority != priority or not open_(r)):
            return False
        if source and r.source != source:
            return False
        if owner == "none" and r.owner_user_id is not None:
            return False
        if owner == "me" and r.owner_user_id != ctx.user.id:
            return False
        if owner.isdigit() and r.owner_user_id != int(owner):
            return False
        if kpi == "hot" and not (open_(r) and r.heat == "hot"):
            return False
        if kpi == "urgent" and not (open_(r) and r.priority in ("urgent", "high")):
            return False
        if kpi == "new" and r.status != "new":
            return False
        if kpi == "unassigned" and not (open_(r) and r.owner_user_id is None):
            return False
        if kpi == "due_today" and not (open_(r) and r.follow_up_on == today):
            return False
        if kpi == "overdue" and not (open_(r) and r.follow_up_on and r.follow_up_on < today):
            return False
        if kpi == "first_overdue" and not (r.status == "new" and r.first_call_due_at and L.aware(r.first_call_due_at) < now_):
            return False
        if kpi == "quo" and r.status != "quo":
            return False
        if kpi == "not_attended" and not (open_(r) and r.owner_user_id is not None and r.last_action_at is None):
            return False
        if kpi == "rev" and r.status != "rev":
            return False
        return True

    rows = [r for r in rows if keep(r)]

    def rank(r: SalesLead):
        if r.status in CLOSED_STATUSES:
            return (99, 99, -r.id)
        if sort == "heat":
            return (HEAT_ORDER[r.heat], PRIORITY_ORDER[r.priority], -r.id)
        if sort == "new":
            return (0, 0, -r.id)
        return (PRIORITY_ORDER[r.priority], HEAT_ORDER[r.heat], -r.id)

    rows.sort(key=rank)
    total = len(rows)
    rows = rows[offset:offset + limit]
    names = names_for(main_db, [r.owner_user_id for r in rows])
    return {"total": total, "counts": counts, "items": [L.lead_out(r, names) for r in rows]}


@router.post("/leads", status_code=status.HTTP_201_CREATED)
def add_lead(body: LeadIn, ctx: Ctx = Depends(require("add_lead")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    data = body.model_dump()
    if data.get("lead_type") and not T.valid_type(sdb, data["lead_type"]):
        raise HTTPException(400, "Unknown lead type")
    data["source"] = data.get("source") or "Typed in"
    data["channel"] = "hand"
    # a team member's own lead is theirs; a manager's lead waits to be given by the rules
    if not ctx.has("see_all"):
        data["owner_user_id"] = ctx.user.id
    lead, created = L.create_lead(main_db, sdb, data, ctx.user)
    commit(main_db, sdb)
    return {"created": created, "lead": L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))}


@router.get("/leads/{lead_id}")
def lead_detail(lead_id: int, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    partner = None
    if lead.crm_kind == "partner" and ctx.has("pr_view"):
        partner = L.refresh_partner_lead(main_db, sdb, lead)
        commit(main_db, sdb)
    acts = list(sdb.scalars(select(SalesLeadActivity).where(SalesLeadActivity.lead_id == lead.id).order_by(SalesLeadActivity.id.desc())))
    quotes = list(sdb.scalars(select(SalesQuotation).where(SalesQuotation.lead_id == lead.id).order_by(SalesQuotation.id.desc())))
    names = names_for(main_db, [lead.owner_user_id])
    out = L.lead_out(lead, names)
    out["activities"] = [{"id": a.id, "kind": a.kind, "text": a.text, "by": a.by_name, "at": L.aware(a.at).isoformat() if a.at else None} for a in acts]
    out["quotations"] = [Q.quotation_out(sdb, x, with_lines=False) for x in quotes] if ctx.any("make_quote", "approve_quote") else []
    out["partner"] = partner
    out["can"] = {
        "work": ctx.has("see_all") or lead.owner_user_id == ctx.user.id,
        "give": ctx.has("give"), "rate": ctx.has("rate"), "set_priority": ctx.has("setpri"), "flag": ctx.has("flag"),
        "dispose": ctx.any("dispose", "dispose_lost", "approve_disp"), "approve_disposal": ctx.has("approve_disp"),
        "quote": ctx.has("make_quote"), "remind": ctx.has("pr_remind"), "cancel_request": ctx.has("pr_cancel_req"),
        "edit": ctx.has("see_all") or lead.owner_user_id == ctx.user.id,
    }
    return out


@router.patch("/leads/{lead_id}")
def patch_lead(lead_id: int, body: LeadPatch, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    data = body.model_dump(exclude_unset=True)
    if "lead_type" in data:
        if not T.valid_type(sdb, data["lead_type"]):
            raise HTTPException(400, "Unknown lead type")
        if not ctx.has("see_all"):
            raise HTTPException(403, "Only the manager changes the lead type")
    for k, v in data.items():
        setattr(lead, k, v)
    L.refresh_priority(lead)
    L.log(sdb, lead, "note", "Details changed: " + ", ".join(sorted(data)), ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/give")
def give_lead(lead_id: int, body: GiveIn, ctx: Ctx = Depends(require("give")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_lead(sdb, lead_id)
    owner_name = ""
    if body.owner_user_id:
        u = crm_link.user_basics(main_db, body.owner_user_id)
        if u is None or u["role"].strip().lower() not in ("sales", "sales_manager") or not u["active"]:
            raise HTTPException(400, "Choose an active Sales user")
        owner_name = u["name"]
    L.give(main_db, sdb, lead, body.owner_user_id, ctx.user, owner_name)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads-auto-give")
def auto_give(ctx: Ctx = Depends(require("autogive")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    L.sync_profiles(main_db, sdb)
    given = 0
    for lead in sdb.scalars(select(SalesLead).where(SalesLead.owner_user_id.is_(None), SalesLead.status == "new")):
        owner = L.pick_owner(sdb, lead)
        if owner:
            L.give(main_db, sdb, lead, owner, ctx.user, crm_link.user_names(main_db, {owner}).get(owner, ""))
            given += 1
    commit(main_db, sdb)
    return {"given": given}


@router.post("/leads/{lead_id}/call")
def log_call(lead_id: int, body: CallIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    L.log_call(main_db, sdb, lead, outcome=body.outcome, note=body.note, next_follow_up=body.next_follow_up, user=ctx.user)
    if body.answers is not None and ctx.has("rate"):
        L.rate_lead(sdb, lead, answers=body.answers, heat=body.heat, why=body.why, user=ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/rate")
def rate(lead_id: int, body: RateIn, ctx: Ctx = Depends(require("rate")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    if L.is_closed(lead):
        raise HTTPException(400, "This lead is closed")
    L.rate_lead(sdb, lead, answers=body.answers, heat=body.heat, why=body.why, user=ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/stage")
def stage(lead_id: int, body: StageIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    L.set_stage(sdb, lead, stage=body.stage, note=body.note, user=ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


class FollowUpIn(BaseModel):
    day: date


@router.post("/leads/{lead_id}/follow-up")
def follow_up(lead_id: int, body: FollowUpIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    if not (ctx.has("see_all") or lead.owner_user_id == ctx.user.id):
        raise HTTPException(403, "Only the person who has this lead can change its follow-up")
    L.set_follow_up(sdb, lead, day=body.day, user=ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/priority")
def priority(lead_id: int, body: PriorityIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    if body.flag:
        if not ctx.has("flag"):
            raise HTTPException(403, "You do not have this tick in Sales")
    elif not ctx.has("setpri"):
        raise HTTPException(403, "You do not have this tick in Sales")
    if L.is_closed(lead):
        raise HTTPException(400, "This lead is closed")
    L.set_priority(sdb, lead, level=body.level, why=body.why, user=ctx.user, flag=body.flag)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/dispose")
def dispose(lead_id: int, body: DisposeIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    review = DISPOSALS.get(body.reason, ("", False))[1]
    if not (ctx.has("dispose_lost") or ctx.has("approve_disp")) if review else not ctx.any("dispose", "approve_disp"):
        raise HTTPException(403, "You do not have this tick in Sales")
    new_status = L.dispose(main_db, sdb, lead, reason=body.reason, note=body.note, order_no=body.order_no, user=ctx.user, can_approve=ctx.has("approve_disp"))
    commit(main_db, sdb)
    return {"status": new_status, "lead": L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))}


@router.post("/leads/{lead_id}/disposal/approve")
def approve_disposal(lead_id: int, ctx: Ctx = Depends(require("approve_disp")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_lead(sdb, lead_id)
    L.approve_disposal(main_db, sdb, lead, ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/disposal/reopen")
def reopen(lead_id: int, ctx: Ctx = Depends(require("approve_disp")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_lead(sdb, lead_id)
    L.reopen(sdb, lead, ctx.user)
    commit(main_db, sdb)
    return L.lead_out(lead, names_for(main_db, [lead.owner_user_id]))


@router.post("/leads/{lead_id}/partner/remind")
def partner_remind(lead_id: int, ctx: Ctx = Depends(require("pr_remind")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    if lead.crm_kind != "partner":
        raise HTTPException(400, "This is not a partner registration lead")
    reg = crm_link.get_partner(main_db, lead.crm_ref or "")
    if reg is None:
        raise HTTPException(404, "The registration was not found in the CRM")
    missing = [i for i in crm_link.partner_papers(reg) if i["required"] and not i["ok"]]
    if not missing:
        raise HTTPException(400, "Nothing required is missing")
    ok, message = crm_link.remind_partner(main_db, reg)
    if not ok:
        raise HTTPException(400, message)
    L.log(sdb, lead, "crm", f"Reminder sent through the CRM mail: {len(missing)} paper{'s' if len(missing) > 1 else ''} missing ({', '.join(m['label'] for m in missing[:3])}{' ...' if len(missing) > 3 else ''})", ctx.user)
    commit(main_db, sdb)
    return {"ok": True, "message": message}


@router.post("/leads/{lead_id}/partner/cancel-request")
def partner_cancel_request(lead_id: int, body: ActionIn, ctx: Ctx = Depends(require("pr_cancel_req")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    if lead.crm_kind != "partner":
        raise HTTPException(400, "This is not a partner registration lead")
    if L.is_closed(lead):
        raise HTTPException(400, "This lead is already closed")
    n = crm_link.notify_partner_admins(
        main_db, lead_id=lead.id, lead_no=lead.lead_no or "", action_type="sales_cancel_request",
        title="Please cancel a partner registration",
        message=f"{lead.name} ({lead.crm_ref}) is not interested. Asked by {ctx.user.name}." + (f" {body.reason.strip()}" if body.reason.strip() else ""),
    )
    L.log(sdb, lead, "crm", "Asked the partner admin to cancel: the partner is not interested" + (f". {body.reason.strip()}" if body.reason.strip() else ""), ctx.user)
    commit(main_db, sdb)
    return {"ok": True, "told": n}


@router.get("/leads/{lead_id}/partner")
def partner_for_lead(lead_id: int, ctx: Ctx = Depends(require("pr_view")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    reg = crm_link.get_partner(main_db, lead.crm_ref or "") if lead.crm_kind == "partner" else None
    if reg is None:
        raise HTTPException(404, "No partner registration for this lead")
    return crm_link.partner_summary(reg)


# ---------------- sync and the registered-first log ----------------
@router.post("/sync")
def sync(body: SyncIn = SyncIn(), ctx: Ctx = Depends(require("give", "upload")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    return sync_now(main_db, sdb, backfill_days=body.backfill_days)


@router.get("/inbox-log")
def inbox_log(limit: int = Query(50, ge=1, le=200), ctx: Ctx = Depends(require("reglog")), sdb: Session = Depends(get_sales_db)):
    rows = sdb.scalars(select(SalesInboxLog).order_by(SalesInboxLog.id.desc()).limit(limit))
    return [{"at": L.aware(r.at).isoformat() if r.at else None, "source": r.source, "crm_ref": r.crm_ref, "lead_id": r.lead_id, "result": r.result} for r in rows]


# ---------------- quotations ----------------
@router.get("/items")
def items(q: str = "", ctx: Ctx = Depends(require("make_quote")), main_db: Session = Depends(get_db)):
    return crm_link.item_search(main_db, q)


def get_quote(sdb: Session, ctx: Ctx, qid: int) -> SalesQuotation:
    q = sdb.get(SalesQuotation, qid)
    if q is None:
        raise HTTPException(404, "Quotation not found")
    if not ctx.any("approve_quote", "approve_high", "override") and q.created_by != ctx.user.id:
        lead = sdb.get(SalesLead, q.lead_id) if q.lead_id else None
        if lead is None or lead.owner_user_id != ctx.user.id:
            raise HTTPException(404, "Quotation not found")
    return q


@router.get("/quotations")
def list_quotations(status_: str = Query("", alias="status"), ctx: Ctx = Depends(require("make_quote", "approve_quote", "approve_high", "override")), sdb: Session = Depends(get_sales_db)):
    rows = list(sdb.scalars(select(SalesQuotation).order_by(SalesQuotation.id.desc())))
    if not ctx.any("approve_quote", "approve_high", "override"):
        rows = [r for r in rows if r.created_by == ctx.user.id]
    if status_:
        rows = [r for r in rows if r.status == status_] if status_ != "waiting" else [r for r in rows if r.status in ("wait", "wadm")]
    return [Q.quotation_out(sdb, r, with_lines=False) for r in rows]


@router.post("/leads/{lead_id}/quotations", status_code=201)
def make_quotation(lead_id: int, body: QuoteIn, ctx: Ctx = Depends(require("make_quote")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    lead = get_visible_lead(sdb, ctx, lead_id)
    items_ = [i.model_dump() for i in body.items] if body.items else None
    q = Q.create_quotation(main_db, sdb, lead, ctx.user, items=items_)
    commit(main_db, sdb)
    return Q.quotation_out(sdb, q)


@router.get("/quotations/{qid}")
def quotation(qid: int, ctx: Ctx = Depends(require("make_quote", "approve_quote", "approve_high", "override")), sdb: Session = Depends(get_sales_db)):
    return Q.quotation_out(sdb, get_quote(sdb, ctx, qid))


@router.put("/quotations/{qid}")
def update_quotation(qid: int, body: QuotePatch, ctx: Ctx = Depends(require("make_quote")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    q = get_quote(sdb, ctx, qid)
    data = body.model_dump(exclude_unset=True)
    if "items" in data and data["items"] is not None:
        data["items"] = [i if isinstance(i, dict) else i.model_dump() for i in data["items"]]
    Q.update_quotation(main_db, sdb, q, data)
    commit(main_db, sdb)
    return Q.quotation_out(sdb, q)


@router.post("/quotations/{qid}/{action}")
def quotation_action(qid: int, action: str, body: ActionIn = ActionIn(), ctx: Ctx = Depends(require("make_quote", "approve_quote", "approve_high", "override")), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    q = get_quote(sdb, ctx, qid)
    Q.transition(sdb, q, action, ctx.user, ctx.ticks, reason=body.reason, is_admin=ctx.is_admin)
    lead = sdb.get(SalesLead, q.lead_id) if q.lead_id else None
    if lead is not None:
        if action == "send" and lead.status in ("new", "con", "int"):
            lead.status = "quo"
        if action == "accept":
            L.log(sdb, lead, "quotation", f"Customer accepted {q.quote_no}. Dispose the lead as Won and add the order number.", ctx.user)
        elif action in ("decline",):
            L.log(sdb, lead, "quotation", f"Customer declined {q.quote_no}. Dispose the lead as Lost.", ctx.user)
        elif action in ("submit", "approve", "return", "reject", "send", "cancel", "override_approve", "send_up"):
            L.log(sdb, lead, "quotation", f"{q.quote_no}: {Q.QUOTE_STATUSES.get(q.status, q.status)}", ctx.user)
    commit(main_db, sdb)
    return Q.quotation_out(sdb, q)


# ---------------- team, profiles and ticks ----------------
def _profile_out(p: SalesProfile, ticks: set[str] | None = None) -> dict:
    return {
        "crm_user_id": p.crm_user_id, "name": p.name_cache, "role": (p.role_cache or "").strip().lower(), "phone": p.phone, "pincode": p.pincode, "state": p.state,
        "district": p.district, "extra_pincodes": L.csv_list(p.extra_pincodes), "areas": L.csv_list(p.areas),
        "types_handled": L.csv_list(p.types_handled), "target_lakh": float(p.target_lakh) if p.target_lakh is not None else None,
        "is_active": p.is_active, **({"ticks": sorted(ticks)} if ticks is not None else {}),
    }


@router.get("/team")
def team(ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    profiles = L.sync_profiles(main_db, sdb)
    sdb.commit()
    if not (ctx.is_admin or ctx.any("others_profile", "targets", "give", "see_all", "types_edit")):
        profiles = [p for p in profiles if p.crm_user_id == ctx.user.id]
    users = {u.id: u for u in crm_link.sales_users(main_db)}
    out = []
    for p in profiles:
        u = users.get(p.crm_user_id)
        row = _profile_out(p, user_ticks(sdb, u) if (u is not None and ctx.is_admin) else None)
        row["email"] = u.email if u else None
        out.append(row)
    return out


@router.put("/team/{user_id}/profile")
def update_profile(user_id: int, body: ProfilePatch, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    u = main_db.get(User, user_id)
    if u is None or u.role.strip().lower() not in ("sales", "sales_manager"):
        raise HTTPException(404, "This person is not in the Sales roles")
    own = user_id == ctx.user.id
    if own and not ctx.has("own_profile") and not ctx.has("others_profile"):
        raise HTTPException(403, "You do not have this tick in Sales")
    if not own and not ctx.has("others_profile"):
        raise HTTPException(403, "You do not have this tick in Sales")
    p = L.ensure_profile(sdb, u)
    data = body.model_dump(exclude_unset=True)
    if ("types_handled" in data or "areas" in data) and not ctx.has("types_edit"):
        raise HTTPException(403, "Only the manager changes the lead types and areas")
    if "target_lakh" in data and not ctx.has("targets"):
        raise HTTPException(403, "You do not have this tick in Sales")
    if "is_active" in data and not ctx.has("others_profile"):
        raise HTTPException(403, "You do not have this tick in Sales")
    if data.get("pincode") not in (None, "") and not str(data["pincode"]).isdigit():
        raise HTTPException(400, "The pin code has digits only")
    if "types_handled" in data:
        bad = [t for t in L.csv_list(data["types_handled"]) if not T.valid_type(sdb, t, active_only=False)]
        if bad:
            raise HTTPException(400, f"Unknown lead type: {', '.join(bad)}")
    for k, v in data.items():
        setattr(p, k, v)
    commit(main_db, sdb)
    return _profile_out(p)


@router.get("/ticks")
def ticks_catalog(ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    users = crm_link.sales_users(main_db)
    return {
        "groups": [{"group": g, "ticks": [{"key": k, "label": lb, "locked": lk} for k, lb, lk in items]} for g, items in TICK_GROUPS],
        "defaults": {r: sorted(v) for r, v in TICK_DEFAULTS.items()},
        "roles": {r: sorted(role_ticks(sdb, r)) for r in ("team", "mgr")},
        "people": [
            {
                "user_id": u.id, "name": u.name, "role": u.role, "role_key": "mgr" if u.role.strip().lower() == "sales_manager" else "team",
                "ticks": sorted(user_ticks(sdb, u)),
                "overrides": {r.tick_key: r.allowed for r in sdb.scalars(select(SalesUserTick).where(SalesUserTick.crm_user_id == u.id))},
            }
            for u in users
        ],
    }


def _history(sdb: Session, ctx: Ctx, *, role_key=None, user_id=None, tick_key: str, allowed):
    sdb.add(SalesTickHistory(role_key=role_key, crm_user_id=user_id, tick_key=tick_key, allowed=allowed, by_user_id=ctx.user.id, by_name=ctx.user.name))


@router.put("/ticks/role/{role_key}")
def set_role_ticks(role_key: str, body: TicksIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    if role_key not in ("team", "mgr"):
        raise HTTPException(404, "Unknown role")
    for key, allowed in body.ticks.items():
        if key not in ALL_TICKS or key in LOCKED_TICKS:
            raise HTTPException(400, f"{key} cannot be ticked for a role")
        row = sdb.scalar(select(SalesRoleTick).where(SalesRoleTick.role_key == role_key, SalesRoleTick.tick_key == key))
        default = key in TICK_DEFAULTS[role_key]
        if allowed is None or allowed == default:
            if row is not None:
                sdb.delete(row)
        elif row is None:
            sdb.add(SalesRoleTick(role_key=role_key, tick_key=key, allowed=bool(allowed)))
        else:
            row.allowed = bool(allowed)
        _history(sdb, ctx, role_key=role_key, tick_key=key, allowed=allowed)
    commit(main_db, sdb)
    return {"role": role_key, "ticks": sorted(role_ticks(sdb, role_key))}


@router.put("/ticks/user/{user_id}")
def set_user_ticks(user_id: int, body: TicksIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change the ticks")
    if user_id == ctx.user.id:
        raise HTTPException(400, "Nobody can tick for themselves")
    u = main_db.get(User, user_id)
    if u is None or u.role.strip().lower() not in ("sales", "sales_manager"):
        raise HTTPException(404, "This person is not in the Sales roles")
    for key, allowed in body.ticks.items():
        if key not in ALL_TICKS or key in LOCKED_TICKS:
            raise HTTPException(400, f"{key} cannot be ticked for a person")
        row = sdb.scalar(select(SalesUserTick).where(SalesUserTick.crm_user_id == user_id, SalesUserTick.tick_key == key))
        if allowed is None:
            if row is not None:
                sdb.delete(row)
        elif row is None:
            sdb.add(SalesUserTick(crm_user_id=user_id, tick_key=key, allowed=bool(allowed)))
        else:
            row.allowed = bool(allowed)
        _history(sdb, ctx, user_id=user_id, tick_key=key, allowed=allowed)
    commit(main_db, sdb)
    return {"user_id": user_id, "ticks": sorted(user_ticks(sdb, u))}


@router.get("/ticks/history")
def ticks_history(limit: int = Query(100, ge=1, le=500), ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    if not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin see this")
    rows = list(sdb.scalars(select(SalesTickHistory).order_by(SalesTickHistory.id.desc()).limit(limit)))
    names = crm_link.user_names(main_db, {r.crm_user_id for r in rows if r.crm_user_id})
    return [{"at": L.aware(r.at).isoformat() if r.at else None, "role_key": r.role_key, "person": names.get(r.crm_user_id), "tick": r.tick_key, "allowed": r.allowed, "by": r.by_name} for r in rows]


# ---------------- settings and summary ----------------
@router.put("/settings")
def update_settings(body: SettingsIn, ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if "fx_rate" in data and not ctx.has("fx"):
        raise HTTPException(403, "You do not have this tick in Sales")
    if set(data) - {"fx_rate"} and not ctx.is_admin:
        raise HTTPException(403, "Only Admin and Sub Admin change these settings")
    for k, v in data.items():
        if v is not None:
            L.set_setting(sdb, k, str(v))
    commit(main_db, sdb)
    return {k: L.get_setting(sdb, k) for k in ("fx_rate", "discount_limit", "home_state", "company_name", "company_address", "company_gstin")}


@router.get("/summary")
def summary(ctx: Ctx = Depends(get_ctx), sdb: Session = Depends(get_sales_db), main_db: Session = Depends(get_db)):
    names = crm_link.user_names(main_db, {p.crm_user_id for p in sdb.scalars(select(SalesProfile))})
    out = build_summary(sdb, ctx, names)
    if out is None:
        raise HTTPException(403, "You do not have a Sales dashboard tick")
    return out
