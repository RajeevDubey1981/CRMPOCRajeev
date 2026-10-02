import logging
import re

import requests

from app.config import settings
from app.services.whatsapp_service import GRAPH_API_VERSION, _normalize_indian_mobile

logger = logging.getLogger(__name__)


def send_complaint_registered_whatsapp(to_mobile, name, query_type, comp_no, description) -> bool:
    """Send the approved 'complaint_registered' template (4 body variables)."""
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient or not settings.whatsapp_enabled:
        return False
    phone_number_id = (settings.wa_phone_number_id or "").strip()
    access_token = re.sub(r"^Bearer\s+", "", (settings.wa_access_token or "").strip(), flags=re.IGNORECASE)
    if not phone_number_id or not access_token:
        logger.error("whatsapp complaint failed: WA_PHONE_NUMBER_ID / WA_ACCESS_TOKEN missing")
        return False

    def clean(v, n):
        return re.sub(r"\s+", " ", str(v or "")).strip()[:n] or "-"

    params = [clean(name, 60), clean(query_type, 30), clean(comp_no, 40), clean(description, 300)]
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": "complaint_registered",
            "language": {"code": "en_US"},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}],
        },
    }
    try:
        r = requests.post(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        if not r.ok:
            logger.error("whatsapp complaint rejected: status=%s response=%s", r.status_code, r.text[:500])
            return False
        logger.info("whatsapp complaint sent: to=%s comp=%s", recipient, comp_no)
        return True
    except requests.RequestException:
        logger.exception("whatsapp complaint request failed: to=%s", recipient)
        return False
