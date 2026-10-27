"""Gate for the /uploads static mount. It used to serve every stored file -- bank statements, Aadhaar/PAN
scans, bank-cancelled-cheque photos, agreement PDFs, complaint/installation photos -- to anyone on the
internet who had the URL, with zero authentication, forever. Random uuid4 filenames made it unguessable,
but obscurity is not access control: one leaked link (browser history, a screenshot, a forwarded chat) was
permanent, unauthenticated exposure of real KYC/financial documents.

Two valid ways to get a file now:
  1. A logged-in CRM user (the same JWT used for the API, read from the Authorization header or from the
     httpOnly session cookie login sets, since a plain <img>/<a> tag can't attach a bearer header).
  2. A partner mid-onboarding, who never has a CRM login: their access_token (already a bearer secret for
     full edit access to their own registration) is set as an httpOnly cookie when they load their public
     form, and only unlocks the specific files that belong to THAT registration -- not the whole bucket.
"""
from jose import JWTError
from starlette.requests import Request

from app.database import SessionLocal
from app.models.partner_registration import PartnerRegistration
from app.models.user import User
from app.schemas.partner_registration import DOCUMENT_FIELDS
from app.security import decode_token

SESSION_COOKIE = "indcool_session"
PARTNER_DOC_COOKIE = "indcool_partner_doc"


def _session_token_valid(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return False
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return bool(user and user.is_active and user.deleted_at is None)


def _partner_token_owns_path(token: str | None, upload_path: str) -> bool:
    if not token:
        return False
    with SessionLocal() as db:
        row = db.query(PartnerRegistration).filter(PartnerRegistration.access_token == token).first()
        if row is None:
            return False
        return any(getattr(row, field, None) == upload_path for field in DOCUMENT_FIELDS)


def is_authorized(path: str, scope) -> bool:
    """path is the sub-path StaticFiles resolved (e.g. "partners/2026/10/<uuid>.pdf", no leading
    /uploads/); scope is the raw ASGI scope so we can read headers/cookies without a receive channel."""
    request = Request(scope)

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer ") and _session_token_valid(auth_header[7:].strip()):
        return True
    if _session_token_valid(request.cookies.get(SESSION_COOKIE)):
        return True

    upload_path = "/uploads/" + path.replace("\\", "/").lstrip("/")
    return _partner_token_owns_path(request.cookies.get(PARTNER_DOC_COOKIE), upload_path)
