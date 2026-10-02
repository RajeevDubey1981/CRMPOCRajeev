"""Public website (indcool.in) endpoints for the new CRM. Additive only."""
import hmac
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.complaint import Complaint, ComplaintStatusLog
from app.routers.complaints import _generate_access_code, _generate_comp_no
from app.routers.sarvam_api import _mobile10, _ok, _track_complaint
from app.services.complaint_whatsapp import send_complaint_registered_whatsapp
from app.services.email_service import send_complaint_created_email
from app.services.file_service import save_upload

router = APIRouter(prefix="/api/site", tags=["website"])

_TYPES = {"service": "Service", "installation": "Installation", "sales": "Sales",
          "partner": "Partner", "others": "Others"}

def require_site_key(x_site_key: Optional[str] = Header(None)) -> None:
    secret = os.environ.get("SITE_API_KEY", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Site API key is not configured")
    if not x_site_key or not hmac.compare_digest(x_site_key.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Invalid site key")

@router.post("/complaints", dependencies=[Depends(require_site_key)])
async def site_register(
    name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(""),
    query_type: str = Form("Service"),
    problem: str = Form(""),
    address: str = Form(""),
    model: str = Form(""),
    remark: str = Form(""),
    document_type: str = Form(""),
    document_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    name = name.strip()
    m = _mobile10(mobile)
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if not m:
        raise HTTPException(status_code=422, detail="A valid 10-digit mobile number is required")
    email = (email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    qtype = _TYPES.get((query_type or "").strip().lower(), "Others")
    problem = (problem or "").strip() or "-"
    remark = (remark or "").strip()
    if document_type.strip():
        remark = (remark + " | " if remark else "") + "Document: " + document_type.strip()

    since = datetime.now(timezone.utc) - timedelta(minutes=10)
    dup = db.execute(select(Complaint).where(
        Complaint.customer_mobile == m, Complaint.query_type == qtype,
        Complaint.source == "website", Complaint.problem_description == problem,
        Complaint.created_at >= since, Complaint.deleted_at.is_(None))).scalars().first()
    if dup is not None:
        return _ok("Registered earlier", {"comp_no": dup.comp_no, "comp_date": str(dup.comp_date), "duplicate": True})

    doc_path = None
    if document_file is not None and document_file.filename:
        doc_path = await save_upload(document_file, module="complaints")

    c = Complaint(
        comp_no=_generate_comp_no(), comp_date=date.today(), customer_name=name,
        customer_mobile=m, customer_email=email, customer_address=(address or "").strip() or None,
        model_details=(model or "").strip() or None, problem_description=problem,
        query_type=qtype, remark=remark or None, send_sms=True,
        access_code=_generate_access_code(), status="Pending", created_by=None,
        source="website", service_proof_path=doc_path)
    db.add(c)
    db.flush()
    db.add(ComplaintStatusLog(complaint_id=c.id, old_status=None, new_status="Pending",
                              changed_by=None, remark="Created from website indcool.in"))
    db.commit()
    db.refresh(c)
    try:
        threading.Thread(target=send_complaint_registered_whatsapp,
                         args=(m, name, qtype, c.comp_no, problem), daemon=True).start()
    except Exception:
        pass
    try:
        threading.Thread(target=send_complaint_created_email,
                         args=(email, name, c.comp_no, qtype, c.status, m, problem), daemon=True).start()
    except Exception:
        pass
    return _ok("Registered successfully", {"comp_no": c.comp_no, "comp_date": str(c.comp_date),
                                            "query_type": qtype, "status": c.status})

@router.get("/status", dependencies=[Depends(require_site_key)])
def site_status(comp_no: str, mobile: str, db: Session = Depends(get_db)):
    if not _mobile10(mobile):
        return {"success": False, "message": "Enter the 10-digit mobile number used for the request.", "data": {}}
    r = _track_complaint(comp_no.strip(), mobile, db)
    if not r.get("success"):
        return {"success": False, "message": "No request found for this ticket number and mobile number.", "data": {}}
    return r
