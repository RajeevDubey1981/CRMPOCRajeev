import logging
import re

import requests

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"


def _normalize_indian_mobile(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("91") and len(digits) == 12:
        return digits
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def send_partner_agreement_otp_whatsapp(
    to_mobile: str,
    otp: str,
) -> bool:
    recipient = _normalize_indian_mobile(to_mobile)
    if not recipient:
        logger.warning("whatsapp otp skipped: empty recipient")
        return False

    if not settings.whatsapp_enabled:
        logger.info("whatsapp otp skipped (WHATSAPP_ENABLED=false): to=%s", recipient)
        return False

    phone_number_id = (settings.wa_phone_number_id or "").strip()
    access_token = re.sub(r"^Bearer\s+", "", (settings.wa_access_token or "").strip(), flags=re.IGNORECASE)
    template_name = (settings.wa_template_name or "otp_verification").strip()
    language = (settings.wa_template_language or "en_US").strip()

    if not phone_number_id or not access_token:
        logger.error(
            "whatsapp otp failed: WA_PHONE_NUMBER_ID and WA_ACCESS_TOKEN are required when WHATSAPP_ENABLED=true"
        )
        return False

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": otp},
                    ],
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {"type": "text", "text": otp},
                    ],
                },
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if not response.ok:
            logger.error(
                "whatsapp otp rejected: status=%s response=%s",
                response.status_code,
                response.text[:500],
            )
            return False
        logger.info("whatsapp otp sent: to=%s", recipient)
        return True
    except requests.RequestException:
        logger.exception("whatsapp otp request failed: to=%s", recipient)
        return False