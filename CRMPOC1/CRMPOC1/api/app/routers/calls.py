from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.call import Call, CallRecording
from app.models.user import User
from app.schemas.call import (
    CallCreate,
    CallListItem,
    CallListResponse,
    CallOut,
    CallTransfer,
    CallUpdate,
)
from app.services.permissions import can_act_on

router = APIRouter(prefix="/api/calls", tags=["calls"])

CALL_TYPES = ["Inbound", "Outbound", "Callback"]
STATUSES = ["Completed", "Busy", "No Answer", "Call Back", "Not Interested"]
PRIORITIES = ["Low", "Medium", "High"]
FOLLOWUP_STATUSES = ["Pending", "Completed"]


def _generate_ref_no(db: Session) -> str:
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y%m")

    # Get the count of calls created this month
    count = db.scalar(
        select(func.count(Call.id)).where(
            Call.ref_no.like(f"REF-{month_prefix}-%")
        )
    ) or 0

    # Format: REF-YYYYMM-XXXX (zero-padded)
    return f"REF-{month_prefix}-{(count + 1):04d}"


def _list_row(db: Session, call: Call) -> CallListItem:
    assigned_to_name = None
    if call.assigned_to:
        u = db.get(User, call.assigned_to)
        assigned_to_name = u.name if u else None
    transferred_to_name = None
    if call.transferred_to:
        u = db.get(User, call.transferred_to)
        transferred_to_name = u.name if u else None
    return CallListItem(
        id=call.id,
        ref_no=call.ref_no,
        customer_name=call.customer_name,
        phone=call.phone,
        call_type=call.call_type,
        status=call.status,
        priority=call.priority,
        assigned_to_name=assigned_to_name,
        transferred_to_name=transferred_to_name,
        is_transferred=call.is_transferred,
        call_datetime=call.call_datetime,
        duration_secs=call.duration_secs,
        followup_date=call.followup_date,
        follow_up_status=call.follow_up_status,
        complaint_id=call.complaint_id,
        has_recording=bool(call.sarvam_interaction_id),
    )


def _hydrate(db: Session, call: Call) -> dict:
    assigned_to_name = None
    if call.assigned_to:
        u = db.get(User, call.assigned_to)
        assigned_to_name = u.name if u else None
    transferred_to_name = None
    if call.transferred_to:
        u = db.get(User, call.transferred_to)
        transferred_to_name = u.name if u else None
    return {
        **{k: getattr(call, k) for k in (
            "id", "ref_no", "customer_name", "customer_email", "phone", "call_type",
            "status", "priority", "assigned_to", "transferred_to", "is_transferred",
            "duration_secs", "call_datetime", "followup_date", "notes", "follow_up_notes",
            "follow_up_status", "complaint_id", "created_at", "updated_at",
        )},
        "assigned_to_name": assigned_to_name,
        "transferred_to_name": transferred_to_name,
        "has_recording": bool(call.sarvam_interaction_id),
    }


@router.get("", response_model=CallListResponse)
def list_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    call_type_filter: str | None = Query(None, alias="call_type"),
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    complaint_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "calls", "can_view", None):
        return CallListResponse(items=[], total=0, page=page, per_page=per_page, stats={})

    stmt = select(Call)

    if status_filter and status_filter in STATUSES:
        stmt = stmt.where(Call.status == status_filter)
    if call_type_filter and call_type_filter in CALL_TYPES:
        stmt = stmt.where(Call.call_type == call_type_filter)
    if complaint_id:
        stmt = stmt.where(Call.complaint_id == complaint_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Call.customer_name.ilike(like),
                Call.phone.ilike(like),
                Call.ref_no.ilike(like),
            )
        )
    if date_from:
        stmt = stmt.where(Call.call_datetime >= datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(Call.call_datetime <= datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc))

    # Calculate stats on the filtered dataset
    stats = {
        "total": db.scalar(select(func.count()).select_from(stmt.subquery())) or 0,
        "completed": db.scalar(select(func.count()).select_from(stmt.where(Call.status == "Completed").subquery())) or 0,
        "call_backs": db.scalar(select(func.count()).select_from(stmt.where(Call.status == "Call Back").subquery())) or 0,
        "busy": db.scalar(select(func.count()).select_from(stmt.where(Call.status == "Busy").subquery())) or 0,
        "no_answer": db.scalar(select(func.count()).select_from(stmt.where(Call.status == "No Answer").subquery())) or 0,
        "transferred": db.scalar(select(func.count()).select_from(stmt.where(Call.is_transferred == True).subquery())) or 0,
    }

    stmt = stmt.order_by(desc(Call.call_datetime))
    total = stats["total"]
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    return CallListResponse(
        items=[_list_row(db, call) for call in rows],
        total=total,
        page=page,
        per_page=per_page,
        stats=stats,
    )


@router.post("", response_model=CallOut, status_code=status.HTTP_201_CREATED)
def create_call(
    body: CallCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "calls", "can_create", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create calls")

    call = Call(
        ref_no=_generate_ref_no(db),
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        phone=body.phone,
        call_type=body.call_type or "Outbound",
        status=body.status or "Completed",
        priority=body.priority or "medium",
        call_datetime=body.call_datetime,
        duration_secs=body.duration_secs,
        followup_date=body.followup_date,
        notes=body.notes,
        follow_up_notes=body.follow_up_notes,
        follow_up_status="Pending" if body.followup_date else None,
        complaint_id=body.complaint_id,
        assigned_to=user.id,
    )
    db.add(call)
    try:
        db.flush()
        from app.services.pending_action_sync import sync_call_pending_actions

        sync_call_pending_actions(db, call)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Complaint ID does not exist")
    db.refresh(call)
    return CallOut(**_hydrate(db, call))


def _load_visible(db: Session, user: User, call_id: int) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    if not can_act_on(db, user, "calls", "can_view", None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    return call


@router.get("/pending-follow-ups", response_model=CallListResponse)
def pending_followups(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    complaint_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "calls", "can_view", None):
        return CallListResponse(items=[], total=0, page=page, per_page=per_page)

    stmt = select(Call).where(
        and_(
            Call.followup_date.isnot(None),
            Call.follow_up_status == "Pending"
        )
    )
    if complaint_id:
        stmt = stmt.where(Call.complaint_id == complaint_id)
    stmt = stmt.order_by(Call.followup_date.asc())

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    return CallListResponse(
        items=[_list_row(db, call) for call in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/calendar-events", response_model=list[dict])
def calendar_events(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_act_on(db, user, "calls", "can_view", None):
        return []

    stmt = select(Call).where(Call.followup_date.isnot(None))

    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            stmt = stmt.where(Call.followup_date >= start_dt)
        except:
            pass

    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            stmt = stmt.where(Call.followup_date <= end_dt)
        except:
            pass

    calls = db.scalars(stmt).all()

    events = []
    for call in calls:
        events.append({
            "id": call.id,
            "title": f"{call.ref_no} - {call.customer_name or 'Unknown'}",
            "start": call.followup_date.isoformat() if call.followup_date else None,
            "url": f"/calls/{call.id}",
            "status": call.follow_up_status or "pending",
        })

    return events


@router.get("/{call_id}/recording")
def get_call_recording(
    call_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The call's audio. Kept in the CRM on first play: the first request downloads it from Sarvam."""
    from app.services.sarvam_recordings import store_recording

    call = _load_visible(db, user, call_id)
    row = db.query(CallRecording).filter(CallRecording.call_id == call.id).first()
    if row is None:
        row = store_recording(db, call)
        if row is not None:
            db.commit()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No recording is available for this call yet")
    return Response(
        content=row.audio,
        media_type=row.content_type,
        headers={"Cache-Control": "private, max-age=3600", "Content-Disposition": f'inline; filename="{call.ref_no}.wav"'},
    )


@router.get("/{call_id}", response_model=CallOut)
def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    call = _load_visible(db, user, call_id)
    return CallOut(**_hydrate(db, call))


@router.put("/{call_id}", response_model=CallOut)
def update_call(
    call_id: int,
    body: CallUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    call = _load_visible(db, user, call_id)
    if not can_act_on(db, user, "calls", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit calls")

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(call, field, value)
    db.commit()
    db.refresh(call)
    return CallOut(**_hydrate(db, call))


@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_call(
    call_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    call = _load_visible(db, user, call_id)
    if not can_act_on(db, user, "calls", "can_delete", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot delete calls")
    db.delete(call)
    db.commit()


@router.post("/{call_id}/transfer", response_model=CallOut)
def transfer_call(
    call_id: int,
    body: CallTransfer,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    call = _load_visible(db, user, call_id)
    if not can_act_on(db, user, "calls", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot transfer calls")

    transferred_user = db.get(User, body.transferred_to)
    if not transferred_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User not found")

    old_assigned = db.get(User, call.assigned_to) if call.assigned_to else None
    call.transferred_to = body.transferred_to
    call.is_transferred = True
    call.assigned_to = body.transferred_to

    transfer_msg = f"[TRANSFER] {datetime.now(timezone.utc).isoformat()} - Call transferred from {old_assigned.name if old_assigned else 'Unassigned'} to {transferred_user.name}"
    if body.transfer_notes:
        transfer_msg += f" | Notes: {body.transfer_notes}"

    call.notes = (call.notes or "") + ("\n" if call.notes else "") + transfer_msg
    db.commit()
    db.refresh(call)
    return CallOut(**_hydrate(db, call))


@router.post("/{call_id}/complete-followup", response_model=CallOut)
def complete_followup(
    call_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    call = _load_visible(db, user, call_id)
    if not can_act_on(db, user, "calls", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot update calls")

    if not call.followup_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No follow-up date set for this call")

    call.follow_up_status = "Completed"
    from app.services.pending_action_sync import sync_call_pending_actions

    sync_call_pending_actions(db, call)
    db.commit()
    db.refresh(call)
    return CallOut(**_hydrate(db, call))
