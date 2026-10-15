"""Queries: a question raised to the Admin team, talked through in a thread that can grow into a group conversation.

Admin and Sub Admin see every query. Everybody else sees the queries they are in (they raised it, were forwarded it, or were
added as a member or in CC). The person who holds a query (or Admin / Sub Admin) can forward it, add people, put people in
CC, and take people out for a private talk and add them back. Only Admin and Sub Admin set the priority. A query nobody
answers in 24 hours rings an alarm for the person who has to answer it. Every step is kept in the history.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.user_query import UserQuery, UserQueryEvent, UserQueryMember, UserQueryMessage, UserQueryRead
from app.schemas.user_query import (
    ForwardIn,
    MemberIn,
    PriorityIn,
    QueryCreate,
    QueryDetail,
    QueryDetailsIn,
    QueryEventOut,
    QueryListItem,
    QueryMemberOut,
    QueryMessageOut,
    QueryPerson,
    QueryReply,
    QuerySummary,
)
from app.services import queries_service as qs
from app.services.date_range import IST
from app.services.queries_service import STAFF_ROLES, aware, is_staff, now
from app.services.role_access import role_key

router = APIRouter(prefix="/api/queries", tags=["queries"])

# who a query can be forwarded to, or who can be added to a conversation
FORWARD_ROLES = frozenset({"service_manager", "sales_manager", "service", "sales", "engineer", "vendor", "admin", "sub_admin", "incool"})


def _load(db: Session, user: User, query_id: int) -> UserQuery:
    q = db.get(UserQuery, query_id)
    if q is None or not qs.can_view(db, user, q):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Query not found")
    return q


def _can_manage(user: User, q: UserQuery) -> bool:
    """Forward, add, CC and take out: Admin and Sub Admin, or the person who holds the query."""
    return is_staff(user) or q.holder_id == user.id


def _can_edit_details(user: User, q: UserQuery) -> bool:
    """Serial number and date: Admin, Sub Admin, and the person who raised the query."""
    return is_staff(user) or user.id in (q.owner_id, q.created_by)


def _must_manage(user: User, q: UserQuery) -> None:
    if not _can_manage(user, q):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who has this query, or the Admin team, can do that")


def _active_user(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None or u.deleted_at is not None or not u.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return u


def _unread(db: Session, user: User, queries: list[UserQuery]) -> dict[int, int]:
    """For each thread, the messages from other people this person can read and has not read yet."""
    if not queries:
        return {}
    ids = [q.id for q in queries]
    last_read = {r.query_id: r.last_read_message_id for r in db.scalars(select(UserQueryRead).where(UserQueryRead.user_id == user.id, UserQueryRead.query_id.in_(ids)))}
    staff = is_staff(user)
    mine = {} if staff else qs.stretches(db, ids, user.id)
    out: dict[int, int] = {}
    rows = db.scalars(select(UserQueryMessage).where(UserQueryMessage.query_id.in_(ids), UserQueryMessage.sender_id != user.id).order_by(UserQueryMessage.id))
    for m in rows:
        if m.id <= last_read.get(m.query_id, 0):
            continue
        if not staff and not qs.message_visible(m, mine.get(m.query_id, [])):
            continue
        out[m.query_id] = out.get(m.query_id, 0) + 1
    return out


def _alarm_for(user: User, q: UserQuery) -> bool:
    return qs.is_overdue(q) and (q.holder_id == user.id or (q.holder_id is None and is_staff(user)))


def _list_items(db: Session, user: User, rows: list[UserQuery]) -> list[QueryListItem]:
    if not rows:
        return []
    ids = [q.id for q in rows]
    unread = _unread(db, user, rows)
    counts = dict(db.execute(select(UserQueryMessage.query_id, func.count(UserQueryMessage.id)).where(UserQueryMessage.query_id.in_(ids)).group_by(UserQueryMessage.query_id)).all())
    latest_ids = select(func.max(UserQueryMessage.id)).where(UserQueryMessage.query_id.in_(ids)).group_by(UserQueryMessage.query_id)
    last = {m.query_id: m for m in db.scalars(select(UserQueryMessage).where(UserQueryMessage.id.in_(latest_ids)))}
    wanted = {q.owner_id for q in rows} | {q.holder_id for q in rows if q.holder_id} | {m.sender_id for m in last.values()}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(wanted)))}
    members = {}
    for qid, ms in qs.stretches(db, ids).items():
        members[qid] = len({m.user_id for m in ms if m.left_at is None})
    staff = is_staff(user)
    mine = {} if staff else qs.stretches(db, ids, user.id)
    out = []
    for q in rows:
        m = last.get(q.id)
        # a person must not read the preview of a message that was kept from them
        if m is not None and not staff and not qs.message_visible(m, mine.get(q.id, [])):
            m = None
        owner, holder = people.get(q.owner_id), people.get(q.holder_id) if q.holder_id else None
        sender = people.get(m.sender_id) if m else None
        out.append(QueryListItem(
            id=q.id, subject=q.subject, category=q.category, related_to=q.related_to, serial_no=q.serial_no, query_date=q.query_date, status=q.status,
            owner_id=q.owner_id, owner_name=owner.name if owner else None, owner_role=owner.role if owner else None,
            created_at=q.created_at, last_message_at=q.last_message_at,
            last_message_preview=" ".join(m.body.split())[:160] if m else "",
            last_sender_name=sender.name if sender else None,
            message_count=int(counts.get(q.id, 0)), unread_count=int(unread.get(q.id, 0)),
            priority=q.priority or "normal", holder_id=q.holder_id, holder_name=holder.name if holder else None, holder_role=holder.role if holder else None,
            hours_left=qs.hours_left(q), overdue=qs.is_overdue(q), alarm_for_me=_alarm_for(user, q), member_count=members.get(q.id, 0),
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
        item.unread_count = unread_before
    staff = is_staff(user)
    holder_or_staff = _can_manage(user, q)
    all_stretches = qs.stretches(db, [q.id]).get(q.id, [])
    mine = [m for m in all_stretches if m.user_id == user.id]
    msgs = [m for m in db.scalars(select(UserQueryMessage).where(UserQueryMessage.query_id == q.id).order_by(UserQueryMessage.id)) if staff or qs.message_visible(m, mine)]
    wanted = {m.sender_id for m in msgs} | {m.user_id for m in all_stretches} | {m.added_by for m in all_stretches if m.added_by}
    events = list(db.scalars(select(UserQueryEvent).where(UserQueryEvent.query_id == q.id).order_by(UserQueryEvent.id)))
    wanted |= {e.by_user_id for e in events if e.by_user_id}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(wanted)))} if wanted else {}

    by_user: dict[int, list[UserQueryMember]] = {}
    for m in all_stretches:
        by_user.setdefault(m.user_id, []).append(m)

    def hidden_from(msg: UserQueryMessage) -> list[str]:
        if not msg.is_private:
            return []
        return [people[uid].name for uid, rows in by_user.items() if uid in people and not is_staff(people[uid]) and not qs.message_visible(msg, rows)]

    out_msgs = [
        QueryMessageOut(
            id=m.id, sender_id=m.sender_id, sender_name=people[m.sender_id].name if m.sender_id in people else None,
            sender_role=people[m.sender_id].role if m.sender_id in people else None,
            from_staff=m.sender_id in people and role_key(people[m.sender_id].role) in STAFF_ROLES, mine=m.sender_id == user.id,
            body=m.body, created_at=m.created_at, is_private=bool(m.is_private), hidden_from=hidden_from(m) if staff else [],
        )
        for m in msgs
    ]
    member_rows = []
    for uid, rows in by_user.items():
        cur = qs.active_stretch(rows)
        if not (holder_or_staff or cur is not None):
            continue  # a person who is out is listed only for the people who can add them back
        shown = cur or rows[-1]
        u = people.get(uid)
        member_rows.append(QueryMemberOut(
            user_id=uid, name=u.name if u else None, role=u.role if u else None, kind=rows[0].kind if rows[0].kind == "owner" else shown.kind,
            active=cur is not None, is_holder=q.holder_id == uid, joined_at=shown.joined_at, left_at=None if cur else shown.left_at,
        ))
    member_rows.sort(key=lambda r: (not r.active, not r.is_holder, r.kind != "owner", r.name or ""))

    history: list[QueryEventOut] = []
    if holder_or_staff:
        owner = people.get(q.owner_id) or db.get(User, q.owner_id)
        if not any(e.kind == "start" for e in events):
            history.append(QueryEventOut(id=0, kind="start", text=f"Query started by {owner.name if owner else 'someone'}", by_name=owner.name if owner else None, at=q.created_at))
        history += [QueryEventOut(id=e.id, kind=e.kind, text=e.text, by_name=people[e.by_user_id].name if e.by_user_id in people else None, at=e.at) for e in events]

    can_reply = q.status != "Closed" or staff
    return QueryDetail(
        **item.model_dump(), messages=out_msgs, members=member_rows, events=history, can_reply=can_reply, can_close=q.status != "Closed",
        can_reopen=q.status == "Closed", can_forward=holder_or_staff and q.status != "Closed", can_manage=holder_or_staff and q.status != "Closed",
        can_set_priority=staff, can_ring=staff and q.status == "Open", can_see_history=holder_or_staff, alarm_count=q.alarm_count or 0,
        can_edit_details=_can_edit_details(user, q),
        private_now=bool(qs.people_out(db, q)),
    )


def _visible_stmt(user: User):
    stmt = select(UserQuery)
    if not is_staff(user):
        mine = select(UserQueryMember.query_id).where(UserQueryMember.user_id == user.id, UserQueryMember.left_at.is_(None))
        stmt = stmt.where(UserQuery.id.in_(mine))
    return stmt


@router.get("/summary", response_model=QuerySummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = list(db.scalars(_visible_stmt(user)))
    counts: dict[str, int] = {}
    for q in rows:
        counts[q.status] = counts.get(q.status, 0) + 1
    unread = _unread(db, user, rows)
    return QuerySummary(
        open=counts.get("Open", 0), answered=counts.get("Answered", 0), closed=counts.get("Closed", 0),
        unread=sum(1 for n in unread.values() if n > 0), staff=is_staff(user), alarms=sum(1 for q in rows if _alarm_for(user, q)),
    )


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The numbers for the dashboard strip on the Queries page: what the person looking can see, and nothing else."""
    rows = list(db.scalars(_visible_stmt(user)))
    unread = _unread(db, user, rows)
    active = [q for q in rows if q.status != "Closed"]
    waiting = [q for q in rows if q.status == "Open"]
    late = [q for q in waiting if qs.is_overdue(q)]
    tiles = {
        "new": sum(1 for q in rows if unread.get(q.id, 0) > 0),
        "active": len(active),
        "waiting": len(waiting),
        "late": len(late),
        "late_for_me": sum(1 for q in rows if _alarm_for(user, q)),
        "priority": sum(1 for q in active if q.priority in ("high", "urgent")),
        "done": sum(1 for q in rows if q.status in ("Answered", "Closed")),
    }
    today = now().astimezone(IST).date()
    days = [today - timedelta(days=6 - i) for i in range(7)]
    opened = [sum(1 for q in rows if aware(q.created_at).astimezone(IST).date() == d) for d in days]
    solved = [sum(1 for q in rows if q.closed_at and aware(q.closed_at).astimezone(IST).date() == d) for d in days]
    by_kind: dict[str, int] = {}
    for q in active:
        by_kind[q.category] = by_kind.get(q.category, 0) + 1
    names = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_({q.holder_id for q in waiting if q.holder_id})))} if waiting else {}
    by_holder: dict[str, dict] = {}
    for q in waiting:
        who = names.get(q.holder_id) if q.holder_id else "Admin team"
        row = by_holder.setdefault(who or "Admin team", {"name": who or "Admin team", "holder_id": q.holder_id, "waiting": 0, "late": 0})
        row["waiting"] += 1
        if qs.is_overdue(q):
            row["late"] += 1
    # how long the first answer takes: the first message from someone other than the one who asked
    first_hours = []
    recent = [q for q in rows if aware(q.created_at) >= now() - timedelta(days=60)]
    if recent:
        msgs: dict[int, list] = {}
        for m in db.scalars(select(UserQueryMessage).where(UserQueryMessage.query_id.in_([q.id for q in recent])).order_by(UserQueryMessage.id)):
            msgs.setdefault(m.query_id, []).append(m)
        for q in recent:
            first = next((m for m in msgs.get(q.id, []) if m.sender_id != q.owner_id), None)
            if first is not None:
                first_hours.append((aware(first.created_at) - aware(q.created_at)).total_seconds() / 3600)
    return {
        "tiles": tiles,
        "week": {"days": [d.strftime("%a") for d in days], "opened": opened, "solved": solved},
        "by_kind": sorted(({"kind": k, "count": v} for k, v in by_kind.items()), key=lambda r: -r["count"]),
        "by_holder": sorted(by_holder.values(), key=lambda r: (-r["late"], -r["waiting"]))[:6],
        "first_answer_hours": round(sum(first_hours) / len(first_hours), 1) if first_hours else None,
        "staff": is_staff(user),
    }


@router.get("/people", response_model=list[QueryPerson])
def people_to_add(search: str | None = Query(None, max_length=60), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The people a query can be forwarded to or opened up to: only for those who may forward (Admin team, or a holder)."""
    if not is_staff(user) and not db.scalar(select(func.count(UserQuery.id)).where(UserQuery.holder_id == user.id)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot forward queries")
    stmt = select(User).where(User.is_active.is_(True), User.deleted_at.is_(None), User.id != user.id)
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    rows = [u for u in db.scalars(stmt.order_by(User.name).limit(400)) if role_key(u.role) in FORWARD_ROLES]
    return [QueryPerson(id=u.id, name=u.name, role=u.role) for u in rows]


@router.get("", response_model=list[QueryListItem])
def list_queries(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = _visible_stmt(user)
    if status_filter in {"Open", "Answered", "Closed"}:
        stmt = stmt.where(UserQuery.status == status_filter)
    elif status_filter == "Active":
        stmt = stmt.where(UserQuery.status != "Closed")
    if search and search.strip():
        like = f"%{search.strip()}%"
        owners = select(User.id).where(or_(User.name.ilike(like), User.email.ilike(like)))
        clauses = [UserQuery.subject.ilike(like), UserQuery.related_to.ilike(like), UserQuery.serial_no.ilike(like), UserQuery.owner_id.in_(owners)]
        typed_day = qs.search_date(search)  # 15/10/2026, 2026-10-15, 15 Oct, 15 Oct 2026
        if typed_day is not None:
            year, month, day = typed_day
            on_day = [extract("day", UserQuery.query_date) == day, extract("month", UserQuery.query_date) == month]
            if year is not None:
                on_day.append(extract("year", UserQuery.query_date) == year)
            clauses.append(and_(*on_day))
        stmt = stmt.where(or_(*clauses))
    rows = list(db.scalars(stmt.order_by(UserQuery.last_message_at.desc(), UserQuery.id.desc()).limit(limit)))
    items = _list_items(db, user, rows)
    # the alarm first, then urgent and high, then the newest
    rank = {"urgent": 0, "high": 1, "normal": 2}
    items.sort(key=lambda i: (not i.alarm_for_me, rank.get(i.priority, 2)))
    return items


@router.post("", response_model=QueryDetail, status_code=status.HTTP_201_CREATED)
def create_query(body: QueryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff = is_staff(user)
    owner = user
    if body.to_user_id is not None:
        if not staff:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an Admin or Sub Admin can write to someone first")
        owner = _active_user(db, body.to_user_id)
        if owner.id == user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose someone else to write to")
    elif staff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose the user you are writing to")
    stamp = now()
    q = UserQuery(
        subject=body.subject, category=body.category, related_to=body.related_to, serial_no=body.serial_no, query_date=body.query_date,
        status="Answered" if owner.id != user.id else "Open",
        owner_id=owner.id, created_by=user.id, last_message_at=stamp, awaiting_since=stamp if owner.id == user.id else None,
    )
    db.add(q)
    db.flush()
    db.add(UserQueryMember(query_id=q.id, user_id=owner.id, kind="owner", share_history=True, joined_at=stamp))
    db.add(UserQueryMessage(query_id=q.id, sender_id=user.id, body=body.message, created_at=stamp))
    qs.log_event(db, q, "start", f"Query started by {user.name}" + (f" for {owner.name}" if owner.id != user.id else ""), user)
    db.flush()
    _mark_read(db, user, q)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.get("/{query_id}", response_model=QueryDetail)
def get_query(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    before = _unread(db, user, [q]).get(q.id, 0)
    _mark_read(db, user, q)
    qs.resolve_cards(db, q, user_ids=[user.id], action_types=["query_member", "query_cc"])  # told, and now they have seen it
    db.commit()
    return _detail(db, user, q, unread_before=before)


@router.post("/{query_id}/messages", response_model=QueryDetail)
def reply(query_id: int, body: QueryReply, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    staff = is_staff(user)
    if q.status == "Closed" and not staff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This query is closed. Reopen it, or raise a new query")
    stamp = now()
    private = bool(qs.people_out(db, q))
    db.add(UserQueryMessage(query_id=q.id, sender_id=user.id, body=body.body, created_at=stamp, is_private=private))
    q.last_message_at = stamp
    mine = qs.active_stretch(qs.stretches(db, [q.id], user.id).get(q.id, []))
    is_cc = mine is not None and mine.kind == "cc" and not staff and q.holder_id != user.id
    answering = staff or q.holder_id == user.id
    if answering and q.owner_id != user.id:
        qs.answered(q)
        qs.resolve_cards(db, q, action_types=["query_overdue", "query_forward"])
    elif not is_cc:
        qs.start_waiting(q)  # someone else wrote: it waits for the holder again
    q.closed_at = None
    q.closed_by = None
    qs.log_event(db, q, "reply", f"{'Private reply' if private else 'Reply'} by {user.name}", user)
    db.flush()
    _mark_read(db, user, q)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/forward", response_model=QueryDetail)
def forward(query_id: int, body: ForwardIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    _must_manage(user, q)
    if q.status == "Closed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This query is closed. Reopen it first")
    target = _active_user(db, body.to_user_id)
    if role_key(target.role) not in FORWARD_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A query cannot be forwarded to that kind of user")
    if target.id == q.holder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "It is with them already")
    old = db.get(User, q.holder_id) if q.holder_id else None
    qs.join(db, q, target, kind="member", added_by=user, share_history=True)
    qs.resolve_cards(db, q, user_ids=[q.holder_id] if q.holder_id else [u.id for u in qs.answerers(db, q)], action_types=["query_overdue", "query_forward"])
    q.holder_id = target.id
    q.status = "Open"
    q.awaiting_since = now()
    q.last_alarm_at = None
    note = (body.note or "").strip()
    qs.log_event(db, q, "forward", f"Forwarded to {target.name} ({target.role}) by {user.name}" + (f", from {old.name}" if old else "") + (f". Note: {note}" if note else ""), user)
    qs.tell_about(db, q, target, kind="forward", text=(f"{user.name} forwarded this to you. {note}" if note else f"{user.name} forwarded this to you."))
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/members", response_model=QueryDetail)
def add_member(query_id: int, body: MemberIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    _must_manage(user, q)
    if q.status == "Closed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This query is closed. Reopen it first")
    person = _active_user(db, body.user_id)
    if is_staff(person):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The Admin team already sees every query")
    if qs.is_member_now(db, q, person):
        raise HTTPException(status.HTTP_409_CONFLICT, "They are in this conversation already")
    back = bool(qs.stretches(db, [q.id], person.id).get(q.id))
    qs.join(db, q, person, kind=body.kind, added_by=user, share_history=body.share_history)
    word = "CC" if body.kind == "cc" else "member"
    qs.log_event(db, q, "cc" if body.kind == "cc" else "member", f"{person.name} {'added back' if back else 'added'} as {word} by {user.name}", user)
    qs.tell_about(db, q, person, kind="cc" if body.kind == "cc" else "member", text=f"{user.name} {'added you back' if back else 'added you'} as {word}.")
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.delete("/{query_id}/members/{user_id}", response_model=QueryDetail)
def remove_member(query_id: int, user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    _must_manage(user, q)
    person = db.get(User, user_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if person.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot take yourself out")
    if person.id == q.holder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "They hold this query. Forward it to someone else first")
    if is_staff(person):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The Admin team always sees every query")
    if not qs.leave(db, q, person, by=user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "They are not in this conversation")
    qs.resolve_cards(db, q, user_ids=[person.id])
    qs.log_event(db, q, "removed", f"{person.name} taken out of the conversation by {user.name}. What is said now stays private until they are added back", user)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.put("/{query_id}/priority", response_model=QueryDetail)
def set_priority(query_id: int, body: PriorityIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not is_staff(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin and Sub Admin set the priority")
    q = _load(db, user, query_id)
    if q.priority != body.priority:
        q.priority = body.priority
        qs.log_event(db, q, "priority", f"Priority set to {body.priority.capitalize()} by {user.name}", user)
        db.commit()
        db.refresh(q)
    return _detail(db, user, q)


@router.put("/{query_id}/details", response_model=QueryDetail)
def set_details(query_id: int, body: QueryDetailsIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    if not _can_edit_details(user, q):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who raised this query, or the Admin team, can change the serial number and date")
    if (q.serial_no, q.query_date) != (body.serial_no, body.query_date):
        qs.log_event(
            db, q, "details",
            f"Serial number and date changed by {user.name}: serial number {body.serial_no or 'not set'} (was {q.serial_no or 'not set'}), "
            f"date {qs.format_day(body.query_date)} (was {qs.format_day(q.query_date)})",
            user,
        )
        q.serial_no, q.query_date = body.serial_no, body.query_date
        db.commit()
        db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/ring", response_model=QueryDetail)
def ring_again(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not is_staff(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin and Sub Admin can ring the alarm again")
    q = _load(db, user, query_id)
    if q.status != "Open":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This query is not waiting for an answer")
    qs.ring(db, q, by=user, again=True)
    db.commit()
    db.refresh(q)
    return _detail(db, user, q)


@router.post("/{query_id}/close", response_model=QueryDetail)
def close_query(query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _load(db, user, query_id)
    if q.status != "Closed":
        q.status = "Closed"
        q.closed_at = now()
        q.closed_by = user.id
        q.awaiting_since = None
        qs.resolve_cards(db, q)
        qs.log_event(db, q, "closed", f"Marked as solved by {user.name}", user)
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
        q.last_message_at = now()
        q.awaiting_since = now()
        q.last_alarm_at = None
        qs.log_event(db, q, "reopened", f"Reopened by {user.name}", user)
        db.commit()
        db.refresh(q)
    return _detail(db, user, q)
