import logging
import re

import requests

from app.config import settings
from app.services.whatsapp_service import GRAPH_API_VERSION, _normalize_indian_mobile

logger = logging.getLogger(__name__)


def _clean(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit] or "-"


def send_service_happy_code_whatsapp(
    to_mobile: str | None,
    *,
    customer_name: str | None,
    service_code: str,
    completion_code: str,
) -> bool:
    """Send the 'service_happy_code' template (3 body variables: name, service code, completion code).

    Mirrors the happy-code email. Never raises: a failed WhatsApp send is logged and the email still goes out.
    """
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient or not settings.whatsapp_enabled:
        return False
    phone_number_id = (settings.wa_phone_number_id or "").strip()
    access_token = re.sub(r"^Bearer\s+", "", (settings.wa_access_token or "").strip(), flags=re.IGNORECASE)
    if not phone_number_id or not access_token:
        logger.error("whatsapp happy code failed: WA_PHONE_NUMBER_ID / WA_ACCESS_TOKEN missing")
        return False

    params = [_clean(customer_name, 60) if customer_name else "Sir/Ma'am", _clean(service_code, 40), _clean(completion_code, 20)]
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": (settings.wa_happy_code_template or "service_happy_code").strip(),
            "language": {"code": (settings.wa_happy_code_language or "en_US").strip()},
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
            logger.error("whatsapp happy code rejected: status=%s response=%s", r.status_code, r.text[:500])
            return False
        logger.info("whatsapp happy code sent: to=%s service=%s", recipient, service_code)
        return True
    except requests.RequestException:
        logger.exception("whatsapp happy code request failed: to=%s", recipient)
        return False
