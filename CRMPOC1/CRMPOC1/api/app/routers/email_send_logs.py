from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.email_send_log import EmailSendLog
from app.models.user import User
from app.schemas.email_send_log import EmailSendLogListResponse, EmailSendLogOut, EmailSendLogSummary
from app.services.email_send_log import email_send_summary
from app.services.role_access import is_system_admin

router = APIRouter(prefix="/api/email-send-logs", tags=["email-send-logs"])


def _require_system_admin(user: User) -> None:
    if not is_system_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only system administrators can view email send logs")


@router.get("/summary", response_model=EmailSendLogSummary)
def send_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_system_admin(user)
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
    _require_system_admin(user)
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
