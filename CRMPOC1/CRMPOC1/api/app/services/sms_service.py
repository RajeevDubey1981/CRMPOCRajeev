import logging
import re

import requests

from app.config import settings
from app.services.whatsapp_service import _normalize_indian_mobile

logger = logging.getLogger(__name__)


def _clean(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def sms_is_configured() -> bool:
    return bool(
        settings.sms_enabled
        and settings.sms_user.strip()
        and settings.sms_password.strip()
        and settings.sms_sender_id.strip()
        and settings.sms_pe_id.strip()
        and settings.sms_happy_code_template_id.strip()
    )


def send_sms(to_mobile: str | None, text: str, *, dlt_template_id: str) -> bool:
    """Send one SMS through SMS India Hub (GET /api/mt/SendSMS). The text must match the DLT-approved template."""
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient or not sms_is_configured():
        return False
    params = {
        "user": settings.sms_user.strip(),
        "password": settings.sms_password.strip(),
        "senderid": settings.sms_sender_id.strip(),
        "channel": (settings.sms_channel or "Trans").strip(),
        "DCS": "0",
        "flashsms": "0",
        "number": recipient,
        "text": text,
        "DLTTemplateId": dlt_template_id.strip(),
        "PEId": settings.sms_pe_id.strip(),
    }
    route = (settings.sms_route or "").strip()
    if route:
        params["route"] = route
    try:
        r = requests.get(settings.sms_api_url.strip(), params=params, timeout=30)
        try:
            data = r.json()
        except ValueError:
            data = {}
        if not r.ok or str(data.get("ErrorCode")) != "000":
            # never log the request URL: it carries the account password
            logger.error("sms rejected: to=%s status=%s code=%s message=%s", recipient, r.status_code, data.get("ErrorCode"), data.get("ErrorMessage"))
            return False
        logger.info("sms sent: to=%s job=%s", recipient, data.get("JobId"))
        return True
    except requests.RequestException:
        logger.exception("sms request failed: to=%s", recipient)
        return False


def send_service_happy_code_sms(
    to_mobile: str | None,
    *,
    customer_name: str | None,
    service_code: str,
    completion_code: str,
) -> bool:
    """SMS twin of the happy-code email. The wording comes from SMS_HAPPY_CODE_TEXT so it can match the DLT template
    exactly without a code change. Never raises: a failed SMS is logged and the email/WhatsApp still go out."""
    if not sms_is_configured():
        return False
    try:
        text = settings.sms_happy_code_text.format(
            name=_clean(customer_name, 30) or "Customer",
            service=_clean(service_code, 30),
            code=_clean(completion_code, 15),
        )
    except (KeyError, IndexError, ValueError):
        logger.error("sms happy code text is invalid: use only {name}, {service} and {code}")
        return False
    return send_sms(to_mobile, text, dlt_template_id=settings.sms_happy_code_template_id)
