"""Queries: any user can raise a question to the Admin and Sub Admin and talk it through in a thread.

An Admin / Sub Admin sees every query, answers, closes, and can also write to a user first. Everyone else only ever sees
their own threads. "Unread" is kept per person.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.user_query import UserQuery, UserQueryMessage, UserQueryRead
from app.schemas.user_query import (
    QueryCreate,
    QueryDetail,
    QueryListItem,
    QueryMessageOut,
    QueryReply,
    QuerySummary,
)
from app.services.role_access import role_key

router = APIRouter(prefix="/api/queries", tags=["queries"])

STAFF_ROLES = frozenset({"admin", "incool", "sub_admin"})


def is_staff(user: User) -> bool:
    return role_key(user.role) in STAFF_ROLES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(db: Session, user: User, query_id: int) -> UserQuery:
    q = db.get(UserQuery, query_id)
    if q is None or (not is_staff(user) and q.owner_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Query not found")
    return q


def _unread_counts(db: Session, user: User, ids: list[int]) -> dict[int, int]:
    """For each thread, how many messages from other people this person has not read yet."""
    if not ids:
        return {}
    read = (
        select(UserQueryRead.query_id.label("qid"), UserQueryRead.last_read_message_id.label("last_id"))
        .where(UserQueryRead.user_id == user.id, UserQueryRead.query_id.in_(ids))
        .subquery()
    )
    rows = db.execute(
        select(UserQueryMessage.query_id, func.count(UserQueryMessage.id))
        .select_from(UserQueryMessage)
        .outerjoin(read, read.c.qid == UserQueryMessage.query_id)
        .where(
            UserQueryMessage.query_id.in_(ids),
            UserQueryMessage.sender_id != user.id,
            UserQueryMessage.id > func.coalesce(read.c.last_id, 0),
        )
        .group_by(UserQueryMessage.query_id)
    ).all()
    return {qid: int(n) for qid, n in rows}


def _list_items(db: Session, user: User, rows: list[UserQuery]) -> list[QueryListItem]:
    if not rows:
        return []
    ids = [q.id for q in rows]
    unread = _unread_counts(db, user, ids)
    counts = dict(
        db.execute(
            select(UserQueryMessage.query_id, func.count(UserQueryMessage.id))
            .where(UserQueryMessage.query_id.in_(ids))
            .group_by(UserQueryMessage.query_id)
        ).all()
    )
    latest_ids = select(func.max(UserQueryMessage.id)).where(UserQueryMessage.query_id.in_(ids)).group_by(UserQueryMessage.query_id)
    last = {m.query_id: m for m in db.scalars(select(UserQueryMessage).where(UserQueryMessage.id.in_(latest_ids))).all()}
    wanted = {q.owner_id for q in rows} | {m.sender_id for m in last.values()}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(wanted))).all()}
    out = []
    for q in rows:
        m = last.get(q.id)
        owner = people.get(q.owner_id)
        sender = people.get(m.sender_id) if m else None
        out.append(QueryListItem(
            id=q.id, subject=q.subject, category=q.category, related_to=q.related_to, status=q.status,
            owner_id=q.owner_id, owner_name=owner.name if owner else None, owner_role=owner.role if owner else None,
            created_at=q.created_at, last_message_at=q.last_message_at,
            last_message_preview=" ".join(m.body.split())[:160] if m else "",
            last_sender_name=sender.name if sender else None,
            message_count=int(counts.get(q.id, 0)), unread_count=int(unread.get(q.id, 0)),
        ))
    return out


def _mark_read(db: Session, user: User, q: UserQuery) -> None:
    newest = db.scalar(select(func.max(UserQueryMessage.id)).where(UserQueryMessage.query_id == q.id)) or 0
    row = db.scalar(select(UserQueryRead).where(UserQueryRead.query_id == q.id, UserQueryRead.user_id == user.id))
    if row is None:
        db.add(UserQueryRead(query_id=q.id, user_id=user.id, last_read_message_id=newest))
    elif row.last_read_message_id < newest:
        row.last_read_message_id = newest


def _detail(db: Session, user: User, q: UserQuery, unread_before: int | None = None) -> QueryDetail:
    item = _list_items(db, user, [q])[0]
    if unread_before is not None:
        item.unread_count = unread_before  # what was new when it was opened, so the page can mark it
    msgs = db.scalars(select(UserQueryMessage).where(UserQueryMessage.query_id == q.id).order_by(UserQueryMessage.id)).all()
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({m.sender_id for m in msgs}))).all()} if msgs else {}
    staff = is_staff(user)
    return QueryDetail(
        **item.model_dump(),
        messages=[
            QueryMessageOut(
                id=m.id,
                sender_id=m.sender_id,
                sender_name=people[m.sender_id].name if m.sender_id in people else None,
                sender_role=people[m.sender_id].role if m.sender_id in people else None,
                from_staff=m.sender_id in people and role_key(people[m.sender_id].role) in STAFF_ROLES,
                mine=m.sender_id == user.id,
                body=m.body,
                created_at=m.created_at,
            )
            for m in msgs
        ],
        can_reply=q.status != "Closed" or staff,
        can_close=q.status != "Closed",
        can_reopen=q.status == "Closed",
    )


@router.get("/summary", response_model=QuerySummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff = is_staff(user)
    counted = select(UserQuery.status, func.count(UserQuery.id))
    ids_stmt = select(UserQuery.id)
    if not staff:
        counted = counted.where(UserQuery.owner_id == user.id)
        ids_stmt = ids_stmt.where(UserQuery.owner_id == user.id)
    counts = {s: int(n) for s, n in db.execute(counted.group_by(UserQuery.status)).all()}
    unread = _unread_counts(db, user, list(db.scalars(ids_stmt).all()))
    return QuerySummary(
        open=counts.get("Open", 0),
        answered=counts.get("Answered", 0),
        closed=counts.get("Closed", 0),
        unread=sum(1 for n in unread.values() if n > 0),
        staff=staff,
    )


@router.get("", response_model=list[QueryListItem])
def list_queries(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(UserQuery)
    if not is_staff(user):
        stmt = stmt.where(UserQuery.owner_id == user.id)
    if status_filter in {"Open", "Answered", "Closed"}:
        stmt = stmt.where(UserQuery.status == status_filter)
    elif status_filter == "Active":
        stmt = stmt.where(UserQuery.status != "Closed")
    if search and search.strip():
        like = f"%{search.strip()}%"
        owners = select(User.id).where(or_(User.name.ilike(like), User.email.ilike(like)))
        stmt = stmt.where(or_(UserQuery.subject.ilike(like), UserQuery.related_to.ilike(like), UserQuery.owner_id.in_(owners)))
    rows = db.scalars(stmt.order_by(UserQuery.last_message_at.desc(), UserQuery.id.desc()).limit(limit)).all()
    return _list_items(db, user, list(rows))


@router.post("", response_model=QueryDetail, status_code=status.HTTP_201_CREATED)
def create_query(body: QueryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff = is_staff(user)
    owner = user
    if body.to_user_id is not None:
        if not staff:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an Admin or Sub Admin can write to someone first")
        owner = db.get(User, body.to_user_id)
        if owner is None or owner.deleted_at is not None or not owner.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if owner.id == user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose someone else to write to")
    elif staff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose the user you are writing to")
    now = _now()
    q = UserQuery(
        subject=body.subject,
        category=body.category,
        related_to=body.related_to,
        status="Answered" if owner.id != user.id else "Open",
        owner_id=owner.id,
        created_by=user.id,
        last_message_at=now,
    )
    db.add(q)
    db.flush()
    db.add(UserQueryMessage(query_id=q.id, sender_id=user.id, body=body.message, created_at=now))
    db.flush()
    _mark_read(db, user, q)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.get("/{query_id}", response_model=QueryDetail)
def get_query(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    before = _unread_counts(db, user, [q.id]).get(q.id, 0)
    _mark_read(db, user, q)
    db.commit()
    return _detail(db, user, q, unread_before=before)


@router.post("/{query_id}/messages", response_model=QueryDetail)
def reply(query_id: int, body: QueryReply, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    staff = is_staff(user)
    if q.status == "Closed" and not staff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This query is closed. Reopen it, or raise a new query")
    now = _now()
    db.add(UserQueryMessage(query_id=q.id, sender_id=user.id, body=body.body, created_at=now))
    q.last_message_at = now
    q.status = "Answered" if (staff and q.owner_id != user.id) else "Open"
    q.closed_at = None
    q.closed_by = None
    db.flush()
    _mark_read(db, user, q)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/close", response_model=QueryDetail)
def close_query(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    if q.status != "Closed":
        q.status = "Closed"
        q.closed_at = _now()
        q.closed_by = user.id
        db.commit()
        db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/reopen", response_model=QueryDetail)
def reopen_query(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    if q.status == "Closed":
        q.status = "Open"
        q.closed_at = None
        q.closed_by = None
        q.last_message_at = _now()
        db.commit()
        db.refresh(q)
    return _detail(db, user, q)
