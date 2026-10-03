from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.pending_action import UserPendingAction
from app.models.user import User
from app.schemas.pending_action import MarkPendingActionsReadIn, PendingActionOut, PendingActionsResponse
from app.services.pending_action_service import list_pending_actions, mark_actions_read
from app.services.pending_action_sync import backfill_all_pending_actions

router = APIRouter(prefix="/api/pending-actions", tags=["pending-actions"])


def _ensure_backfilled(db: Session) -> None:
    total = db.scalar(select(func.count()).select_from(UserPendingAction)) or 0
    if total == 0:
        backfill_all_pending_actions(db)
        db.commit()


@router.get("", response_model=PendingActionsResponse)
def get_pending_actions(
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_backfilled(db)
    total, items = list_pending_actions(db, user, limit=limit)
    return PendingActionsResponse(
        total=total,
        items=[PendingActionOut.model_validate(row) for row in items],
    )


@router.post("/mark-read")
def mark_pending_actions_read(
    body: MarkPendingActionsReadIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ids = body.ids if body else None
    mark_actions_read(db, user, ids)
    db.commit()
    return {"ok": True}
