from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings


@dataclass(frozen=True)
class PaymentApprovalStage:
    key: str
    label: str
    roles: frozenset[str]


SERVICE_DESK_ROLES = frozenset({"service", "indcool_service"})
SERVICE_MANAGER_ROLES = frozenset({"service_manager"})
ADMIN_ROLES = frozenset({"admin", "incool"})


def role_key(role: str | None) -> str:
    return (role or "").strip().lower()


def is_system_admin(user: Any) -> bool:
    return role_key(getattr(user, "role", None)) in ADMIN_ROLES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def configured_payment_approval_steps() -> int:
    steps = int(getattr(settings, "payment_approval_steps", 3) or 3)
    return 2 if steps == 2 else 3


def payment_approval_stages() -> list[PaymentApprovalStage]:
    stages = [
        PaymentApprovalStage("service_role", "Service Role", SERVICE_DESK_ROLES),
    ]
    if configured_payment_approval_steps() == 3:
        stages.append(PaymentApprovalStage("service_manager", "Service Manager", SERVICE_MANAGER_ROLES))
    stages.append(PaymentApprovalStage("admin", "Admin", ADMIN_ROLES))
    return stages


def first_payment_stage() -> PaymentApprovalStage:
    return payment_approval_stages()[0]


def stage_by_key(stage_key: str | None) -> PaymentApprovalStage:
    stages = payment_approval_stages()
    for stage in stages:
        if stage.key == stage_key:
            return stage
    return stages[0]


def stage_index(stage_key: str | None) -> int:
    stages = payment_approval_stages()
    for idx, stage in enumerate(stages):
        if stage.key == stage_key:
            return idx
    return 0


def is_final_stage(stage_key: str | None) -> bool:
    return stage_index(stage_key) == len(payment_approval_stages()) - 1


def next_stage(stage_key: str | None) -> PaymentApprovalStage | None:
    stages = payment_approval_stages()
    idx = stage_index(stage_key)
    return stages[idx + 1] if idx + 1 < len(stages) else None


def user_can_approve_stage(user: Any, stage_key: str | None) -> bool:
    if is_system_admin(user):
        return True
    stage = stage_by_key(stage_key)
    key = role_key(user.role)
    if stage.key == "admin":
        return is_system_admin(user)
    return key in stage.roles


def approval_stage_payload(stage_key: str | None) -> dict:
    stages = payment_approval_stages()
    idx = stage_index(stage_key)
    stage = stages[idx]
    return {
        "payment_approval_stage": stage.key,
        "payment_approval_stage_label": stage.label,
        "payment_approval_step": idx + 1,
        "payment_approval_total_steps": len(stages),
        "payment_next_approver_role": stage.label,
    }


def get_users_for_stage(db: Session, stage_key: str | None) -> list[Any]:
    from app.models.user import User

    stage = stage_by_key(stage_key)
    role_keys = {role_key(role) for role in stage.roles}
    return list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                func.lower(func.trim(User.role)).in_(role_keys),
            )
        )
    )


def record_payment_approval(
    db: Session,
    *,
    module: str,
    entity_id: int,
    stage_key: str | None,
    decision: str,
    user: Any,
    remarks: str | None,
    service_payment_request_id: int | None = None,
) -> Any:
    from app.models.payment_approval import PaymentApprovalLog

    stages = payment_approval_stages()
    idx = stage_index(stage_key)
    stage = stages[idx]
    row = PaymentApprovalLog(
        module=module,
        entity_id=entity_id,
        service_payment_request_id=service_payment_request_id,
        stage_key=stage.key,
        stage_label=stage.label,
        stage_level=idx + 1,
        total_stages=len(stages),
        decision=decision,
        approved_by_user_id=user.id,
        approver_role=user.role,
        remarks=remarks,
        created_at=_now(),
    )
    db.add(row)
    return row


def ensure_current_stage_approver(user: Any, stage_key: str | None) -> None:
    if not user_can_approve_stage(user, stage_key):
        stage = stage_by_key(stage_key)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Only {stage.label} can approve or reject this payment stage",
        )


def notify_payment_stage(
    db: Session,
    *,
    module: str,
    entity_id: int,
    title: str,
    href: str,
    entity_status: str,
    stage_key: str | None,
    entity_ref: str = "",
    occurred_at: datetime | None = None,
) -> None:
    from app.services.pending_action_service import notify_users

    users = get_users_for_stage(db, stage_key)
    stage = stage_by_key(stage_key)
    notify_users(
        db,
        users,
        module=module,
        entity_id=entity_id,
        entity_ref=entity_ref,
        action_type="approve_payment",
        title=title,
        message=f"Payment request is waiting for {stage.label} approval.",
        action_label="Approve payment",
        href=href,
        entity_status=entity_status,
        occurred_at=occurred_at,
    )


def resolve_payment_stage_actions(
    db: Session,
    *,
    module: str,
    entity_id: int,
    entity_ref: str = "",
) -> None:
    from app.services.pending_action_service import resolve_pending_actions

    resolve_pending_actions(
        db,
        module=module,
        entity_id=entity_id,
        action_types=["approve_payment"],
        entity_ref=entity_ref,
    )
