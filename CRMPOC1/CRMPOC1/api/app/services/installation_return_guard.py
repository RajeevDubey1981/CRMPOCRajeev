"""Keep returned installations out of ordinary mutation endpoints."""
import json
import re
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.installation import InstallationRequest

HELD = {"Return Approved - Closed", "Pending Return Approval", "Returned - Location Not Verified", "Return Location Verified"}

async def guard_installation_returns(request: Request, db: Session = Depends(get_db)):
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or not request.url.path.startswith("/api/installations/"):
        return
    match = re.match(r"/api/installations/(\d+)(?:/|$)", request.url.path)
    ids = [int(match.group(1))] if match else []
    if not match and "/bulk-" in request.url.path:
        if "application/json" in request.headers.get("content-type", ""):
            body = await request.json()
        else:
            body = await request.form()
        values = body.get("installation_ids", [])
        if isinstance(values, str):
            try:
                values = json.loads(values) if values.startswith("[") else values.split(",")
            except ValueError:
                return
        try:
            ids = [int(v) for v in values]
        except (TypeError, ValueError):
            return
    if ids:
        rows = db.scalars(select(InstallationRequest).where(InstallationRequest.id.in_(ids)).order_by(InstallationRequest.id).with_for_update()).all()
        if any(row.status in HELD for row in rows):
            raise HTTPException(409, "Selected installation has a location return. Review the return before continuing; approved returned rows remain archived.")
