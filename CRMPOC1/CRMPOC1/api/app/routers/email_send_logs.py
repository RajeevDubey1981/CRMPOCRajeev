from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.email_send_log import EmailSendLog
from app.models.user import User
from app.schemas.email_send_log import EmailSendLogListResponse, EmailSendLogOut, EmailSendLogSummary
from app.models.email_bounce import EmailBounce
from app.services.email_bounce import poll_bounces_once
from app.services.email_send_log import email_send_summary
from app.services.permissions import can_act_on
from app.services.role_access import is_system_admin

router = APIRouter(prefix="/api/email-send-logs", tags=["email-send-logs"])


def _require_log_access(db: Session, user: User) -> None:
    """System admins always; any other role only when the role table gives it email_logs -> view (Sub Admin)."""
    if is_system_admin(user) or can_act_on(db, user, "email_logs", "can_view", None):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view email send logs")


@router.get("/summary", response_model=EmailSendLogSummary)
def send_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_log_access(db, user)
    summary = email_send_summary(db, date_from=date_from, date_to=date_to)
    return EmailSendLogSummary(
        **summary,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("", response_model=EmailSendLogListResponse)
def list_send_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_log_access(db, user)
    filters = []
    if status_filter:
        filters.append(EmailSendLog.status == status_filter)
    total = db.scalar(select(func.count()).select_from(EmailSendLog).where(*filters)) or 0
    rows = db.scalars(
        select(EmailSendLog)
        .where(*filters)
        .order_by(desc(EmailSendLog.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return EmailSendLogListResponse(
        items=[EmailSendLogOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/check-bounces")
def check_bounces_now(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Read the sending mailbox for delivery-failure reports right now (system admin only)."""
    _require_log_access(db, user)
    try:
        new = poll_bounces_once()
    except Exception as exc:  # network / login problems are shown, not hidden
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not read the mailbox: {type(exc).__name__}: {exc}")
    return {"new_bounces": new}


@router.get("/bounces")
def list_bounces(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_log_access(db, user)
    rows = db.scalars(select(EmailBounce).order_by(desc(EmailBounce.created_at)).limit(limit)).all()
    return [
        {"id": r.id, "to_email": r.to_email, "reason": r.reason, "status_code": r.status_code, "source": r.source, "at": r.created_at}
        for r in rows
    ]
