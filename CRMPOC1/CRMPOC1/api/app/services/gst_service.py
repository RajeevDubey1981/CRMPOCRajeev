"""GSTIN validation against a GST Suvidha Provider (GSP) search API."""
from __future__ import annotations

import re
import threading
import time
import os

import requests


class GSTINValidator:

    BASE_URL = "https://www.gst.gov.in/api/search/taxpayers"
    # GST's public web search is CAPTCHA protected.  For a server-to-server
    # lookup, configure a GST Suvidha Provider (GSP) endpoint instead.  The
    # endpoint must accept POST JSON: {"gstin": "..."} and return the GSTN
    # taxpayer payload (optionally wrapped in one or more `data` objects).
    PROVIDER_URL_ENV = "GST_PROVIDER_URL"
    PROVIDER_API_KEY_ENV = "GST_PROVIDER_API_KEY"
    PROVIDER_API_SECRET_ENV = "GST_PROVIDER_API_SECRET"
    PROVIDER_AUTH_ENV = "GST_PROVIDER_AUTHORIZATION"
    LOOKUP_ENABLED_ENV = "GST_LOOKUP_ENABLED"

    # sandbox.co.in issues short-lived bearer tokens from a separate
    # authenticate endpoint keyed by api key + api secret; cache the token
    # in-process until shortly before it expires instead of fetching one per
    # lookup.
    AUTHENTICATE_URL = "https://api.sandbox.co.in/authenticate"
    _token_lock = threading.Lock()
    _cached_token: str | None = None
    _cached_token_expiry: float = 0.0

    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.gst.gov.in/",
        "Origin": "https://www.gst.gov.in",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Connection": "keep-alive",
    }

    GSTIN_PATTERN = re.compile(
        r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
    )

    STATE_CODES = {
        "01": "Jammu and Kashmir", "02": "Himachal Pradesh",
        "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana",
        "07": "Delhi", "08": "Rajasthan",
        "09": "Uttar Pradesh", "10": "Bihar",
        "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur",
        "15": "Mizoram", "16": "Tripura",
        "17": "Meghalaya", "18": "Assam",
        "19": "West Bengal", "20": "Jharkhand",
        "21": "Odisha", "22": "Chhattisgarh",
        "23": "Madhya Pradesh", "24": "Gujarat",
        "26": "Dadra and Nagar Haveli and Daman and Diu",
        "27": "Maharashtra", "28": "Andhra Pradesh (old)",
        "29": "Karnataka", "30": "Goa",
        "31": "Lakshadweep", "32": "Kerala",
        "33": "Tamil Nadu", "34": "Puducherry",
        "35": "Andaman and Nicobar Islands",
        "36": "Telangana", "37": "Andhra Pradesh",
        "38": "Ladakh", "97": "Other Territory",
        "99": "Centre Jurisdiction",
    }

    def validate_format(self, gstin: str) -> dict:
        """Step 1: Local format validation before API call."""
        gstin = (gstin or "").upper().strip()

        if len(gstin) != 15:
            return {"valid": False, "error": f"Length must be 15, got {len(gstin)}"}

        if not self.GSTIN_PATTERN.match(gstin):
            return {"valid": False, "error": "Invalid GSTIN format"}

        state_code = gstin[:2]
        if state_code not in self.STATE_CODES:
            return {"valid": False, "error": f"Invalid state code: {state_code}"}

        return {
            "valid": True,
            "gstin": gstin,
            "state_code": state_code,
            "state": self.STATE_CODES[state_code],
            "pan": gstin[2:12],
            "entity_no": gstin[12],
        }

    def _get_access_token(self, api_key: str, api_secret: str) -> str:
        """Fetch (and cache) a bearer token from the GSP's authenticate endpoint."""
        with self._token_lock:
            if self._cached_token and time.time() < self._cached_token_expiry:
                return self._cached_token

            resp = requests.post(
                self.AUTHENTICATE_URL,
                headers={
                    "x-api-key": api_key,
                    "x-api-secret": api_secret,
                    "x-api-version": "1.0",
                },
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()
            token = body.get("access_token") or (body.get("data") or {}).get("access_token")
            if not token:
                raise ValueError("GST provider authenticate response had no access_token")

            # Tokens are short-lived; refresh a little early rather than
            # tracking the exact JWT expiry.
            GSTINValidator._cached_token = token
            GSTINValidator._cached_token_expiry = time.time() + 15 * 60
            return token

    def lookup(self, gstin: str, retries: int = 2) -> dict:
        """Look up a GSTIN through a configured, authorised GST provider.

        The public GST portal is deliberately not used as a production API:
        its anonymous search requires a CAPTCHA and can block automated
        requests.  Keeping that behaviour out of this service prevents an
        intermittent, misleading "valid" result in the partner form.
        """
        fmt = self.validate_format(gstin)
        if not fmt["valid"]:
            return fmt

        gstin = fmt["gstin"]
        lookup_enabled = os.getenv(self.LOOKUP_ENABLED_ENV, "false").strip().lower()
        if lookup_enabled not in {"1", "true", "yes", "on"}:
            return {
                "valid": False,
                "gstin": gstin,
                "error": "GST live validation is currently disabled.",
            }

        provider_url = os.getenv(self.PROVIDER_URL_ENV, "").strip()
        if not provider_url:
            return {
                "valid": False,
                "gstin": gstin,
                "error": "GST live lookup is not configured. Set GST_PROVIDER_URL and provider credentials.",
            }

        api_key = os.getenv(self.PROVIDER_API_KEY_ENV, "").strip()
        api_secret = os.getenv(self.PROVIDER_API_SECRET_ENV, "").strip()
        authorization = os.getenv(self.PROVIDER_AUTH_ENV, "").strip()

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        headers["x-api-version"] = "1.0"

        if authorization:
            headers["Authorization"] = authorization
        elif api_key and api_secret:
            try:
                headers["Authorization"] = self._get_access_token(api_key, api_secret)
            except (requests.exceptions.RequestException, ValueError) as exc:
                return {
                    "valid": False,
                    "gstin": gstin,
                    "error": f"GST provider authentication failed: {exc}",
                }
        else:
            return {
                "valid": False,
                "gstin": gstin,
                "error": "GST live lookup is not configured. Set GST_PROVIDER_API_KEY and GST_PROVIDER_API_SECRET.",
            }

        for attempt in range(retries + 1):
            try:
                resp = requests.post(
                    provider_url,
                    json={"gstin": gstin},
                    headers=headers,
                    timeout=15,
                    verify=True,
                )

                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue

                if resp.status_code == 401:
                    # Cached token may have expired early; drop it and retry once.
                    GSTINValidator._cached_token = None
                    if authorization or attempt == retries:
                        return {
                            "valid": False,
                            "gstin": gstin,
                            "error": "Access denied by GST provider (check configured credentials)",
                        }
                    try:
                        headers["Authorization"] = self._get_access_token(api_key, api_secret)
                    except (requests.exceptions.RequestException, ValueError) as exc:
                        return {
                            "valid": False,
                            "gstin": gstin,
                            "error": f"GST provider authentication failed: {exc}",
                        }
                    continue

                if resp.status_code == 403:
                    return {
                        "valid": False,
                        "gstin": gstin,
                        "error": "Access denied by GST provider (check configured credentials)",
                    }

                if resp.status_code >= 400:
                    return {
                        "valid": False,
                        "gstin": gstin,
                        "error": f"GST provider returned {resp.status_code}: {resp.text[:500]}",
                    }

                data = resp.json()

                # GSPs commonly envelope the GSTN result as {data: {data:
                # {...}}}; unwrap that without coupling the CRM to one vendor.
                while isinstance(data, dict) and isinstance(data.get("data"), dict):
                    data = data["data"]

                if not data or data == {}:
                    return {
                        "valid": False,
                        "gstin": gstin,
                        "error": "GSTIN not found by GST provider",
                    }

                return self._parse(gstin, data)

            except requests.exceptions.Timeout:
                if attempt == retries:
                    return {"valid": False, "gstin": gstin, "error": "GST provider timed out"}
                time.sleep(1)

            except requests.exceptions.RequestException as exc:
                return {"valid": False, "gstin": gstin, "error": f"GST provider request failed: {exc}"}

        return {"valid": False, "error": "Max retries exceeded"}

    @staticmethod
    def _map_business_type(ctb: str | None) -> str | None:
        """Map GST portal 'Constitution of Business' to CRM business types."""
        value = (ctb or "").strip().lower()
        if not value:
            return None
        if "proprietor" in value:
            return "Proprietorship"
        if "limited liability" in value or value == "llp":
            return "LLP"
        if "partnership" in value:
            return "Partnership"
        if "private" in value:
            return "Private Limited"
        if "public" in value:
            return "Public Limited"
        if "trust" in value or "society" in value:
            return "Trust / Society"
        return "Other"

    def _parse(self, gstin: str, data: dict) -> dict:
        """Parse and normalise the API response."""
        status = (data.get("sts") or "").strip()
        pradr = data.get("pradr") or {}
        addr = pradr.get("addr") or {}

        address_parts = list(filter(None, [
            addr.get("bno"), addr.get("flno"),
            addr.get("bnm"), addr.get("st"),
            addr.get("loc"), addr.get("dst"),
            addr.get("stcd"), addr.get("pncd"),
        ]))
        full_address = ", ".join(address_parts)

        state_code = gstin[:2]
        state = addr.get("stcd") or self.STATE_CODES.get(state_code)

        return {
            "valid": status == "Active",
            "gstin": gstin,
            "status": status,
            "legal_name": data.get("lgnm"),
            "trade_name": data.get("tradeNam"),
            "business_type": data.get("ctb"),
            "business_type_mapped": self._map_business_type(data.get("ctb")),
            "dealer_type": data.get("dty"),
            "registration_date": data.get("rgdt"),
            "state_jurisdiction": data.get("stj"),
            "state_code": state_code,
            "state": state,
            "address": full_address,
            "pincode": addr.get("pncd"),
            "city": addr.get("loc") or addr.get("dst"),
            "district": addr.get("dst"),
            "address_type": pradr.get("ntr"),
            "business_activities": data.get("nba", []),
            "einvoice_applicable": data.get("einvoiceStatus") == "Yes",
            "additional_places": len(data.get("adadr", [])),
            "pan": gstin[2:12],
        }


def validate_gstin(gstin: str) -> dict:
    return GSTINValidator().lookup(gstin)
