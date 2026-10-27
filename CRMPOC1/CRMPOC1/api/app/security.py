import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# A real bcrypt hash of a throwaway secret, never a real user's. Run password verification against this
# when the email in a login attempt doesn't exist, so "no such user" and "wrong password" take the same
# time -- bcrypt's own cost dominates the response either way, instead of a login with a bad email
# returning near-instantly and a login with a real one taking ~100ms, which is enough of a gap to
# enumerate which emails have accounts (security review, 2026-10-27).
DUMMY_PASSWORD_HASH = pwd_context.hash(secrets.token_urlsafe(24))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
