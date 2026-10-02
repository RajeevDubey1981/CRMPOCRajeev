"""Make complaints registered by Sarvam / the website behave exactly like POST /api/complaints.

The CRM screen, after creating a complaint, (1) creates the linked service request for Service
complaints, (2) syncs pending actions / in-app alerts and (3) emails the customer. Sarvam and the
website insert the complaint directly, so they call these helpers to get the same side effects.
It reuses the CRM's own functions, so any later change to the CRM flow is picked up automatically.
"""
import logging
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.routers.complaints import _ensure_service_request_for_complaint
from app.services.email_service import (
    send_complaint_created_email,
    send_service_request_acknowledgment_email,
)
from app.services.pending_action_sync import sync_complaint_pending_actions

logger = logging.getLogger(__name__)

# No logged-in CRM user exists for an automated registration; service requests allow created_by = NULL.
_AUTOMATION_USER = SimpleNamespace(id=None)


def link_and_sync(db: Session, complaint: Complaint):
    """Call after db.flush() and before db.commit().

    Returns the linked ServiceRequest for Service complaints, otherwise None. Runs inside a
    savepoint so that a problem here can never stop the complaint itself from being registered.
    """
    linked = None
    try:
        with db.begin_nested():
            if (complaint.query_type or "").lower() == "service":
                linked = _ensure_service_request_for_complaint(db, complaint, _AUTOMATION_USER)
            sync_complaint_pending_actions(db, complaint)
    except Exception:
        logger.exception("linking service request / pending actions failed for %s", complaint.comp_no)
        linked = None
    return linked


def send_confirmation_email(
    to_email,
    customer_name,
    comp_no,
    query_type,
    status,
    customer_mobile,
    problem,
    service_request_no=None,
) -> bool:
    """Same choice the CRM makes: service acknowledgment for Service, otherwise 'complaint created'.

    The ticket number shown to the customer is always the complaint REFERENCE number (comp_no, IDC_...),
    the same number WhatsApp sends and the voice agent reads out - not the internal SRV_ number.
    """
    if not (to_email or "").strip():
        return False
    try:
        if service_request_no:
            return send_service_request_acknowledgment_email(to_email, comp_no)
        return send_complaint_created_email(
            to_email, customer_name, comp_no, query_type, status, customer_mobile, problem
        )
    except Exception:
        logger.exception("confirmation email failed for %s", comp_no)
        return False
