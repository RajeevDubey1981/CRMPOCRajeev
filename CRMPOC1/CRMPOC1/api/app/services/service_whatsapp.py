import logging
import re

import requests

from app.config import settings
from app.services.whatsapp_service import GRAPH_API_VERSION, _normalize_indian_mobile

logger = logging.getLogger(__name__)


def _clean(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit] or "-"


def _post_template(recipient: str, template: str, components: list, what: str) -> bool:
    phone_number_id = (settings.wa_phone_number_id or "").strip()
    access_token = re.sub(r"^Bearer\s+", "", (settings.wa_access_token or "").strip(), flags=re.IGNORECASE)
    if not phone_number_id or not access_token:
        logger.error("whatsapp %s failed: WA_PHONE_NUMBER_ID / WA_ACCESS_TOKEN missing", what)
        return False
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": (settings.wa_happy_code_language or "en_US").strip()},
            "components": components,
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
            logger.error("whatsapp %s rejected: template=%s status=%s response=%s", what, template, r.status_code, r.text[:500])
            return False
        logger.info("whatsapp %s sent: to=%s template=%s", what, recipient, template)
        return True
    except requests.RequestException:
        logger.exception("whatsapp %s request failed: to=%s", what, recipient)
        return False


def send_service_visit_confirmed_whatsapp(to_mobile: str | None, *, customer_name: str | None, service_code: str) -> bool:
    """Utility template 'service_visit_confirmed' (2 body variables: name, service reference). Same facts as the email."""
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient or not settings.whatsapp_enabled:
        return False
    params = [_clean(customer_name, 60) if customer_name else "Sir/Ma'am", _clean(service_code, 40)]
    return _post_template(
        recipient,
        (settings.wa_visit_confirmed_template or "service_visit_confirmed").strip(),
        [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}],
        "visit confirmation",
    )


def send_service_happy_code_whatsapp(
    to_mobile: str | None,
    *,
    customer_name: str | None,
    service_code: str,
    completion_code: str,
) -> bool:
    """Send the happy (completion) code on WhatsApp with the approved Authentication template 'service_happy_code_otp'.

    The template text is fixed by Meta ("<code> is your verification code.") and has a Copy code button, so the
    code is the only variable (body + button). Mirrors the happy-code email. Never raises: a failed WhatsApp send is
    logged and the email still goes out.
    """
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient or not settings.whatsapp_enabled:
        return False
    code = _clean(completion_code, 15)
    return _post_template(
        recipient,
        (settings.wa_happy_code_template or "service_happy_code_otp").strip(),
        [
            {"type": "body", "parameters": [{"type": "text", "text": code}]},
            {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": code}]},
        ],
        "happy code",
    )


def send_service_happy_code_messages(
    to_mobile: str | None,
    *,
    customer_name: str | None,
    service_code: str,
    completion_code: str,
) -> None:
    """Same as the happy-code email: first the visit confirmation (service reference, 24-48 h visit), then the code.

    Each message is independent, so if one template is not approved yet the other still goes out.
    """
    send_service_visit_confirmed_whatsapp(to_mobile, customer_name=customer_name, service_code=service_code)
    send_service_happy_code_whatsapp(
        to_mobile, customer_name=customer_name, service_code=service_code, completion_code=completion_code
    )
