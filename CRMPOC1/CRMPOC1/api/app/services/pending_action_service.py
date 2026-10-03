from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pending_action import UserPendingAction
from app.models.user import User
from app.services.role_access import OPERATIONS_ADMIN_ROLES, role_key


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _coalesce_dt(*values: datetime | None) -> datetime:
    for value in values:
        if value is not None:
            return value
    return _now()


def upsert_pending_action(
    db: Session,
    *,
    recipient_user_id: int,
    module: str,
    entity_id: int,
    action_type: str,
    title: str,
    message: str,
    action_label: str,
    href: str,
    entity_status: str,
    occurred_at: datetime | None = None,
    recipient_vendor_id: int | None = None,
    entity_ref: str = "",
) -> UserPendingAction:
    entity_ref = (entity_ref or "").strip()
    occurred = occurred_at or _now()
    row = db.scalar(
        select(UserPendingAction).where(
            UserPendingAction.recipient_user_id == recipient_user_id,
            UserPendingAction.module == module,
            UserPendingAction.entity_id == entity_id,
            UserPendingAction.entity_ref == entity_ref,
            UserPendingAction.action_type == action_type,
        )
    )
    if row is None:
        row = UserPendingAction(
            recipient_user_id=recipient_user_id,
            recipient_vendor_id=recipient_vendor_id,
            module=module,
            entity_id=entity_id,
            entity_ref=entity_ref,
            action_type=action_type,
            title=title,
            message=message,
            action_label=action_label,
            href=href,
            entity_status=entity_status,
            occurred_at=occurred,
            is_active=True,
            is_read=False,
            read_at=None,
            resolved_at=None,
        )
        db.add(row)
        return row

    row.recipient_vendor_id = recipient_vendor_id
    row.title = title
    row.message = message
    row.action_label = action_label
    row.href = href
    row.entity_status = entity_status
    row.occurred_at = occurred
    row.is_active = True
    row.resolved_at = None
    return row


def resolve_pending_actions(
    db: Session,
    *,
    module: str,
    entity_id: int,
    action_types: list[str] | None = None,
    entity_ref: str | None = None,
) -> None:
    stmt = select(UserPendingAction).where(
        UserPendingAction.module == module,
        UserPendingAction.entity_id == entity_id,
        UserPendingAction.is_active.is_(True),
    )
    if entity_ref is not None:
        stmt = stmt.where(UserPendingAction.entity_ref == entity_ref)
    if action_types:
        stmt = stmt.where(UserPendingAction.action_type.in_(action_types))
    now = _now()
    for row in db.scalars(stmt):
        row.is_active = False
        row.resolved_at = now


def resolve_all_for_entity(db: Session, *, module: str, entity_id: int) -> None:
    resolve_pending_actions(db, module=module, entity_id=entity_id)


def get_operations_admin_users(db: Session) -> list[User]:
    keys = {role_key(role) for role in OPERATIONS_ADMIN_ROLES}
    return list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                func.lower(func.trim(User.role)).in_(keys),
            )
        )
    )


def get_users_by_roles(db: Session, roles: set[str]) -> list[User]:
    keys = {role_key(role) for role in roles}
    return list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                func.lower(func.trim(User.role)).in_(keys),
            )
        )
    )


def notify_users(
    db: Session,
    users: list[User],
    *,
    module: str,
    entity_id: int,
    action_type: str,
    title: str,
    message: str,
    action_label: str,
    href: str,
    entity_status: str,
    occurred_at: datetime | None = None,
    recipient_vendor_id: int | None = None,
    entity_ref: str = "",
) -> None:
    seen: set[int] = set()
    for user in users:
        if user.id in seen:
            continue
        seen.add(user.id)
        upsert_pending_action(
            db,
            recipient_user_id=user.id,
            recipient_vendor_id=recipient_vendor_id,
            module=module,
            entity_id=entity_id,
            entity_ref=entity_ref,
            action_type=action_type,
            title=title,
            message=message,
            action_label=action_label,
            href=href,
            entity_status=entity_status,
            occurred_at=occurred_at,
        )


def list_pending_actions(db: Session, user: User, limit: int = 15) -> tuple[int, list[UserPendingAction]]:
    total = db.scalar(
        select(func.count()).select_from(UserPendingAction).where(
            UserPendingAction.recipient_user_id == user.id,
            UserPendingAction.is_active.is_(True),
            UserPendingAction.is_read.is_(False),
        )
    ) or 0
    items = list(
        db.scalars(
            select(UserPendingAction)
            .where(
                UserPendingAction.recipient_user_id == user.id,
                UserPendingAction.is_active.is_(True),
            )
            .order_by(UserPendingAction.is_read.asc(), UserPendingAction.occurred_at.desc())
            .limit(limit)
        )
    )
    return total, items


def mark_actions_read(db: Session, user: User, action_ids: list[int] | None = None) -> None:
    stmt = select(UserPendingAction).where(
        UserPendingAction.recipient_user_id == user.id,
        UserPendingAction.is_active.is_(True),
        UserPendingAction.is_read.is_(False),
    )
    if action_ids:
        stmt = stmt.where(UserPendingAction.id.in_(action_ids))
    now = _now()
    for row in db.scalars(stmt):
        row.is_read = True
        row.read_at = now
