"""Public, no-login page endpoint: the caller types the email and the 6-digit code from the SMS."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.email_confirmation import confirm

router = APIRouter(prefix="/api/public/email-confirm", tags=["public"])

_hits: dict[str, deque] = defaultdict(deque)


def _throttle(ip: str, limit: int = 12, window: int = 600) -> None:
    now = time.time()
    q = _hits[ip]
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many tries. Please wait a few minutes.")
    q.append(now)


class ConfirmIn(BaseModel):
    code: str
    email: str


@router.post("")
def confirm_email(body: ConfirmIn, request: Request, db: Session = Depends(get_db)):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "x")).split(",")[0].strip()
    _throttle(ip)
    ok, message = confirm(db, body.code, body.email)
    if not ok:
        raise HTTPException(400, message)
    return {"ok": True, "message": message}
