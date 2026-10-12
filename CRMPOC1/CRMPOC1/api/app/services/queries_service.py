"""The rules of Queries as a group conversation.

* A conversation has people in it (the one who raised it, people added as members or as CC). Each person is in for a
  stretch of time. Someone can be taken out and added back later.
* A message sent while somebody is out is private: only the people who were in at that moment can read it. Staff (Admin,
  Sub Admin) read everything and see who it was kept from.
* A query has a holder, the person who has to answer it (empty = the Admin team), and waits since a time. After 24 hours
  without an answer the holder gets an alarm.
* Every step is written in the history.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_query import UserQuery, UserQueryEvent, UserQueryMember, UserQueryMessage
from app.services import pending_action_service as pas
from app.services.role_access import role_key

STAFF_ROLES = frozenset({"admin", "incool", "sub_admin"})
OVERDUE_AFTER = timedelta(hours=24)
PRIORITIES = ("normal", "high", "urgent")
MODULE = "queries"


def is_staff(user: User) -> bool:
    return role_key(user.role) in STAFF_ROLES


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------- who is in ----------------
def stretches(db: Session, query_ids: list[int], user_id: int | None = None) -> dict[int, list[UserQueryMember]]:
    if not query_ids:
        return {}
    stmt = select(UserQueryMember).where(UserQueryMember.query_id.in_(query_ids)).order_by(UserQueryMember.id)
    if user_id is not None:
        stmt = stmt.where(UserQueryMember.user_id == user_id)
    out: dict[int, list[UserQueryMember]] = {}
    for m in db.scalars(stmt):
        out.setdefault(m.query_id, []).append(m)
    return out


def active_stretch(rows: list[UserQueryMember]) -> UserQueryMember | None:
    for m in rows:
        if m.left_at is None:
            return m
    return None


def is_member_now(db: Session, q: UserQuery, user: User) -> bool:
    return active_stretch(stretches(db, [q.id], user.id).get(q.id, [])) is not None


def can_view(db: Session, user: User, q: UserQuery) -> bool:
    return is_staff(user) or is_member_now(db, q, user)


def message_visible(msg: UserQueryMessage, mine: list[UserQueryMember]) -> bool:
    """Can a person (with these stretches in the conversation) read this message?"""
    at = aware(msg.created_at)
    for m in mine:
        if aware(m.joined_at) <= at and (m.left_at is None or at < aware(m.left_at)):
            return True
    if not msg.is_private and mine:
        first = min(mine, key=lambda m: aware(m.joined_at))
        if first.share_history and at < aware(first.joined_at):
            return True  # added with the earlier shared messages
    return False


def people_out(db: Session, q: UserQuery) -> list[int]:
    """People who were in this conversation and are out now."""
    by_user: dict[int, list[UserQueryMember]] = {}
    for m in stretches(db, [q.id]).get(q.id, []):
        by_user.setdefault(m.user_id, []).append(m)
    return [uid for uid, rows in by_user.items() if active_stretch(rows) is None]


def join(db: Session, q: UserQuery, user: User, *, kind: str, added_by: User | None, share_history: bool = True) -> UserQueryMember:
    """Put a person in the conversation (again). A person already in stays as they are."""
    rows = stretches(db, [q.id], user.id).get(q.id, [])
    cur = active_stretch(rows)
    if cur is not None:
        return cur
    # someone coming back keeps the right to the shared past they had; a new person gets it if asked for
    share = share_history or any(m.share_history for m in rows)
    m = UserQueryMember(query_id=q.id, user_id=user.id, kind=kind, share_history=share, added_by=added_by.id if added_by else None, joined_at=now())
    db.add(m)
    db.flush()
    return m


def leave(db: Session, q: UserQuery, user: User, *, by: User) -> bool:
    cur = active_stretch(stretches(db, [q.id], user.id).get(q.id, []))
    if cur is None:
        return False
    cur.left_at = now()
    cur.left_by = by.id
    db.flush()
    return True


def member_ids_now(db: Session, q: UserQuery) -> list[int]:
    return [m.user_id for m in stretches(db, [q.id]).get(q.id, []) if m.left_at is None]


# ---------------- history ----------------
def log_event(db: Session, q: UserQuery, kind: str, text: str, by: User | None) -> None:
    db.add(UserQueryEvent(query_id=q.id, kind=kind, text=text, by_user_id=by.id if by else None, at=now()))


# ---------------- who is asked to answer, and the alarm ----------------
def answerers(db: Session, q: UserQuery) -> list[User]:
    """Whoever has to answer: the holder, or the Admin team when nobody was named."""
    if q.holder_id:
        holder = db.get(User, q.holder_id)
        return [holder] if holder is not None and holder.is_active and holder.deleted_at is None else []
    return pas.get_users_by_roles(db, set(STAFF_ROLES))


def is_overdue(q: UserQuery, at: datetime | None = None) -> bool:
    return q.status == "Open" and q.awaiting_since is not None and (at or now()) - aware(q.awaiting_since) >= OVERDUE_AFTER


def hours_left(q: UserQuery, at: datetime | None = None) -> float | None:
    if q.status != "Open" or q.awaiting_since is None:
        return None
    return max(0.0, (OVERDUE_AFTER - ((at or now()) - aware(q.awaiting_since))).total_seconds() / 3600)


def _card(db: Session, q: UserQuery, user: User, *, action_type: str, title: str, message: str, label: str, urgent: bool, due: bool = False) -> None:
    pas.upsert_pending_action(
        db, recipient_user_id=user.id, module=MODULE, entity_id=q.id, entity_ref=f"QRY-{q.id}", action_type=action_type,
        title=title, message=("HIGH PRIORITY - " if urgent else "") + message, action_label=label, href=f"/queries/{q.id}",
        entity_status=q.status, due_at=(aware(q.awaiting_since) + OVERDUE_AFTER) if due and q.awaiting_since else None,
    )


def tell_about(db: Session, q: UserQuery, user: User, *, kind: str, text: str) -> None:
    """A card on the person's dashboard: forwarded to you, you were added, you were put in CC."""
    urgent = q.priority in ("high", "urgent")
    _card(db, q, user, action_type=f"query_{kind}", title={"forward": "A query was forwarded to you", "member": "You were added to a conversation", "cc": "You were put in CC on a query"}.get(kind, "Query"),
          message=f"{q.subject}: {text}", label="Open the query", urgent=urgent)


def resolve_cards(db: Session, q: UserQuery, user_ids: list[int] | None = None, action_types: list[str] | None = None) -> None:
    if user_ids is None:
        pas.resolve_pending_actions(db, module=MODULE, entity_id=q.id, action_types=action_types)
        return
    from app.models.pending_action import UserPendingAction

    stamp = now()
    for row in db.scalars(select(UserPendingAction).where(
        UserPendingAction.module == MODULE, UserPendingAction.entity_id == q.id, UserPendingAction.is_active.is_(True),
        UserPendingAction.recipient_user_id.in_(user_ids),
    )):
        if action_types is None or row.action_type in action_types:
            row.is_active = False
            row.resolved_at = stamp


def ring(db: Session, q: UserQuery, *, by: User | None = None, again: bool = False) -> int:
    """The alarm: a card that stays on the dashboard until the query is answered. Returns how many people were rung."""
    people = answerers(db, q)
    waited = int((now() - aware(q.awaiting_since)).total_seconds() // 3600) if q.awaiting_since else 24
    for person in people:
        _card(db, q, person, action_type="query_overdue", title="A query has waited for your answer",
              message=f"{q.subject}: no reply for {waited} hours. Answer it or forward it.", label="Answer now", urgent=True, due=True)
    q.alarm_count = (q.alarm_count or 0) + 1
    q.last_alarm_at = now()
    names = ", ".join(p.name for p in people) or "nobody"
    if by is None:
        log_event(db, q, "alarm", f"No reply for 24 hours: alarm rung for {names}", None)
    else:
        log_event(db, q, "alarm", f"Alarm rung again for {names} by {by.name}", by)
    return len(people)


def sweep_overdue(db: Session) -> int:
    """Ring the alarm for every open query that waited 24 hours with no answer and was not rung for yet in this wait."""
    rung = 0
    cutoff = now() - OVERDUE_AFTER
    for q in db.scalars(select(UserQuery).where(UserQuery.status == "Open", UserQuery.awaiting_since.isnot(None))):
        if aware(q.awaiting_since) > cutoff:
            continue
        if q.last_alarm_at is not None and aware(q.last_alarm_at) >= aware(q.awaiting_since):
            continue  # already rung for this wait
        ring(db, q)
        rung += 1
    if rung:
        db.commit()
    return rung


def start_waiting(q: UserQuery) -> None:
    q.status = "Open"
    q.awaiting_since = q.awaiting_since or now()


def answered(q: UserQuery) -> None:
    q.status = "Answered"
    q.awaiting_since = None


# ---------------- the runner: rings the alarm of queries that waited 24 hours ----------------
_started = False


def _loop() -> None:
    import logging
    import time

    from app.database import SessionLocal

    log = logging.getLogger("queries")
    time.sleep(45)
    while True:
        try:
            with SessionLocal() as db:
                sweep_overdue(db)
        except Exception:
            log.exception("Query alarm sweep failed")
        time.sleep(600)


def start_query_runner() -> None:
    global _started
    if _started:
        return
    _started = True
    import threading

    threading.Thread(target=_loop, name="query-alarm", daemon=True).start()
