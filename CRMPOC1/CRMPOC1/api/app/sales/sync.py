"""Registered first, then lead. The CRM already registers every Sales enquiry and every partner registration. Sales
asks the CRM for the ones newer than the last it saw (so nothing is lost when either side is offline), makes a lead
of each, and keeps only the reference number and a copy of the message."""

from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.sales import crm_link
from app.sales.leads import (
    aware, create_lead, get_setting, jdump, log, now, refresh_partner_lead, set_setting, sync_profiles,
)
from app.sales.models import SalesInboxLog, SalesLead
from app.sales.rules import CLOSED_STATUSES

logger = logging.getLogger("sales.sync")
_started = False


def _inbox(sdb: Session, source: str, ref: str | None, lead: SalesLead | None, result: str) -> None:
    sdb.add(SalesInboxLog(source=source, crm_ref=ref, lead_id=lead.id if lead else None, result=result))


def _pointer(sdb: Session, key: str) -> int | None:
    value = get_setting(sdb, key, "")
    return int(value) if value.strip().isdigit() else None


def _complaint_data(c) -> dict:
    place = ", ".join(x for x in (c.district, c.state) if x) or (c.customer_address or "")[:120]
    src = "Website form" if (c.source or "").lower() == "public" else "Call-centre desk" if (c.source or "").lower() == "callcenter" else (c.source or "CRM").title()
    return {
        "name": c.customer_name, "phone": c.customer_mobile, "email": c.customer_email, "item": c.model_details or (c.problem_description or "")[:200],
        "message": c.problem_description, "place": place, "state": c.state, "district": c.district, "pincode": c.pincode,
        "source": src, "channel": "website" if (c.source or "").lower() == "public" else "desk",
        "crm_kind": "complaint", "crm_ref": c.comp_no, "crm_id": c.id,
    }


def _partner_data(r) -> dict | None:
    phone = r.mobile or r.alternate_mobile
    if not phone:
        return None
    return {
        "name": r.name or r.contact_person_name or "Partner", "phone": phone, "email": r.email,
        "item": f"Wants to become a {r.partner_type}", "place": ", ".join(x for x in (r.city or r.district, r.state) if x),
        "state": r.state, "district": r.district or r.city, "pincode": r.pincode, "source": "Partner form", "channel": "partner",
        "lead_type": "dealer", "details": " · ".join(x for x in (f"GST {r.gst_no}" if r.gst_no else "", f"sells in {r.operating_states}" if r.operating_states else "") if x) or None,
        "crm_kind": "partner", "crm_ref": r.registration_no, "crm_id": r.id,
        "heat": "warm", "heat_why": ["Filled in the long partner form"], "message": f"Partner form {r.registration_no} ({r.partner_type}, {r.business_type or 'type not given'})",
    }


def run_sync(main_db: Session, sdb: Session, *, backfill_days: int | None = None) -> dict:
    stats = {"complaints": 0, "partners": 0, "again": 0, "started": False, "refreshed": 0, "closed_retried": 0}
    sync_profiles(main_db, sdb)

    since = now() - timedelta(days=backfill_days) if backfill_days else None
    last_c, last_p = _pointer(sdb, "last_complaint_id"), _pointer(sdb, "last_partner_id")
    if last_c is None or last_p is None:
        # first run: start from now. Older enquiries are brought in only when someone asks (backfill).
        if last_c is None:
            set_setting(sdb, "last_complaint_id", str(crm_link.max_complaint_id(main_db)))
        if last_p is None:
            set_setting(sdb, "last_partner_id", str(crm_link.max_partner_id(main_db)))
        stats["started"] = True
        sdb.flush()
        last_c = _pointer(sdb, "last_complaint_id") if last_c is None else last_c
        last_p = _pointer(sdb, "last_partner_id") if last_p is None else last_p

    after_c = 0 if since else (last_c or 0)
    after_p = 0 if since else (last_p or 0)
    top_c, top_p = last_c or 0, last_p or 0

    for c in crm_link.sales_complaints(main_db, after_id=after_c, since=since):
        top_c = max(top_c, c.id)
        if sdb.scalar(select(SalesLead.id).where(SalesLead.crm_kind == "complaint", SalesLead.crm_ref == c.comp_no)):
            continue
        lead, created = create_lead(main_db, sdb, _complaint_data(c))
        if created:
            stats["complaints"] += 1
            _inbox(sdb, lead.source, c.comp_no, lead, f"Registered, lead {lead.lead_no} made for {lead.name} ({lead.lead_type})")
        else:
            stats["again"] += 1
            _inbox(sdb, lead.source, c.comp_no, lead, f"Registered. Same phone as lead {lead.lead_no}: added to its history, no new lead")

    for r in crm_link.partner_registrations(main_db, after_id=after_p, since=since):
        top_p = max(top_p, r.id)
        if sdb.scalar(select(SalesLead.id).where(SalesLead.crm_kind == "partner", SalesLead.crm_ref == r.registration_no)):
            continue
        data = _partner_data(r)
        if data is None:
            _inbox(sdb, "Partner form", r.registration_no, None, "No phone number on the registration: no lead made")
            continue
        lead, created = create_lead(main_db, sdb, data)
        stats["partners"] += 1
        refresh_partner_lead(main_db, sdb, lead)
        _inbox(sdb, "Partner form", r.registration_no, lead, f"Registered, lead {lead.lead_no} made for {lead.name} (Dealer)")

    if top_c > (last_c or 0):
        set_setting(sdb, "last_complaint_id", str(top_c))
    if top_p > (last_p or 0):
        set_setting(sdb, "last_partner_id", str(top_p))
    sdb.flush()

    # partner leads follow the CRM; closes the CRM did not take are sent again
    for lead in sdb.scalars(select(SalesLead).where(SalesLead.crm_kind == "partner", SalesLead.status.notin_(("won", "dis")))):
        refresh_partner_lead(main_db, sdb, lead)
        stats["refreshed"] += 1
    for lead in sdb.scalars(select(SalesLead).where(SalesLead.crm_close_pending.isnot(None), SalesLead.crm_kind == "complaint")):
        by = main_db.get(User, lead.disposal_by) if lead.disposal_by else None
        if by is not None and crm_link.close_complaint(main_db, lead.crm_ref, won=lead.crm_close_pending == "won", note=lead.disposal_note or "", by=by):
            lead.crm_close_pending = None
            log(sdb, lead, "crm", "The CRM took the close")
            stats["closed_retried"] += 1
    return stats


def sync_now(main_db: Session, sdb: Session, **kwargs) -> dict:
    try:
        stats = run_sync(main_db, sdb, **kwargs)
        sdb.commit()
        main_db.commit()
        return stats
    except Exception:
        sdb.rollback()
        main_db.rollback()
        raise


def _loop() -> None:
    from app.database import SessionLocal
    from app.sales.db import new_sales_session, sales_enabled

    time.sleep(20)
    while True:
        try:
            if sales_enabled():
                with SessionLocal() as main_db, new_sales_session() as sdb:
                    sync_now(main_db, sdb)
                with SessionLocal() as main_db, new_sales_session() as sdb:
                    from app.sales.sources import run_due_sources

                    run_due_sources(main_db, sdb)
        except Exception:
            logger.exception("Sales sync failed")
        time.sleep(max(15, int(settings.sales_sync_seconds or 60)))


def start_sales_runner() -> None:
    global _started
    from app.sales.db import sales_enabled

    if _started or not sales_enabled() or not settings.sales_sync_enabled:
        return
    _started = True
    threading.Thread(target=_loop, name="sales-sync", daemon=True).start()
