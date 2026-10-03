"""Shared role checks for operational vs system administration."""

from __future__ import annotations

from app.models.user import User

OPERATIONS_ADMIN_ROLES = frozenset({
    "admin",
    "incool",
    "indcool",
    "indcool service",
    "indcool_service",
    "service",
    "service_manager",
    "sub_admin",
})
SYSTEM_ADMIN_ROLES = frozenset({"admin", "incool"})
# Sub Admin: does the daily admin work (operations) but is NOT a system admin: it cannot change roles or
# permissions, approve payments, or create / edit Admin and Sub Admin accounts.
SUB_ADMIN_ROLE = "sub_admin"
PROTECTED_USER_ROLES = frozenset({"admin", "incool", "sub_admin"})
SERVICE_TEAM_ROLES = OPERATIONS_ADMIN_ROLES


def role_key(role: str | None) -> str:
    return (role or "").strip().lower()


def permission_role_name(role: str | None) -> str:
    """Map legacy user.role values to canonical Role.name for permission lookup."""
    key = role_key(role)
    if key in {"indcool", "indcool service", "service", "service_manager"}:
        return "indcool_service"
    return key


def is_service_team(user: User) -> bool:
    return role_key(user.role) in SERVICE_TEAM_ROLES


def is_operations_admin(user: User) -> bool:
    return role_key(user.role) in OPERATIONS_ADMIN_ROLES


def is_system_admin(user: User) -> bool:
    return role_key(user.role) in SYSTEM_ADMIN_ROLES


def is_sub_admin(user: User) -> bool:
    return role_key(user.role) == SUB_ADMIN_ROLE
