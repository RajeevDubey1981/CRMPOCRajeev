"""A public, no-login endpoint behind a campaign's personal interest link. The token identifies an
existing Sales lead; a submission writes onto that lead (an activity note + a heat bump) -- it never
creates a new lead and needs no phone-matching, because the recipient was already a known contact."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.marketing.db import get_marketing_db
from app.marketing.models import MkCampaign, MkLeadInterestToken
from app.sales.db import get_sales_db
from app.sales.leads import jdump, log
from app.sales.models import SalesLead

router = APIRouter(prefix="/api/public/lead-interest", tags=["public"])


def _campaign_asset_url(path: str | None) -> str | None:
    if not path:
        return None
    from app.config import settings

    base = (settings.app_public_url or "").rstrip("/")
    return f"{base}{path}" if base else path


def _load(mdb: Session, token: str) -> tuple[MkLeadInterestToken, MkCampaign]:
    row = mdb.get(MkLeadInterestToken, token)
    if row is None:
        raise HTTPException(404, "This link is not valid.")
    campaign = mdb.get(MkCampaign, row.campaign_id)
    if campaign is None:
        raise HTTPException(404, "This link is not valid.")
    return row, campaign


@router.get("/{token}")
def view_interest_form(token: str, mdb: Session = Depends(get_marketing_db), sdb: Session = Depends(get_sales_db)):
    row, campaign = _load(mdb, token)
    lead = sdb.get(SalesLead, row.lead_id)
    if lead is None:
        raise HTTPException(404, "This link is not valid.")
    return {
        "lead": {"name": lead.name, "phone": lead.phone},
        "product": {
            "name": campaign.offer_name, "price": campaign.offer_price, "mrp": campaign.offer_mrp,
            "image_url": _campaign_asset_url(campaign.offer_image_path),
        },
        "already_submitted": row.submitted_at is not None,
        "submitted_interest": row.submitted_interest,
    }


class InterestIn(BaseModel):
    interest: str  # "yes" | "maybe"
    quantity: str = ""
    capacity: str = ""
    note: str = ""


@router.post("/{token}")
def submit_interest_form(token: str, body: InterestIn, mdb: Session = Depends(get_marketing_db), sdb: Session = Depends(get_sales_db)):
    row, campaign = _load(mdb, token)
    if body.interest not in ("yes", "maybe"):
        raise HTTPException(422, "Pick Yes or Maybe.")
    if row.submitted_at is not None:
        return {"ok": True, "already_submitted": True}

    lead = sdb.get(SalesLead, row.lead_id)
    if lead is None:
        raise HTTPException(404, "This link is not valid.")

    interest_label = "Yes, interested" if body.interest == "yes" else "Maybe, send details"
    text = (
        f"Replied to the \"{campaign.offer_name}\" campaign link.\n"
        f"Interest: {interest_label}\n"
        f"Quantity: {body.quantity.strip() or 'Not specified'}\n"
        f"Capacity: {body.capacity.strip() or 'Any / not sure'}\n"
        f"Note: {body.note.strip() or 'None'}"
    )
    log(sdb, lead, "note", text)
    lead.last_action_at = datetime.now(timezone.utc)
    if body.interest == "yes":
        lead.heat = "hot"
        lead.heat_why = jdump([f"Confirmed interest in {campaign.offer_name} via campaign link"])
    elif lead.heat == "cold":
        lead.heat = "warm"
        lead.heat_why = jdump([f"Replied \"maybe\" to {campaign.offer_name} campaign link"])

    row.submitted_at = datetime.now(timezone.utc)
    row.submitted_interest = body.interest
    sdb.commit()
    mdb.commit()
    return {"ok": True, "already_submitted": False}
