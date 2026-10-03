"""Service request visibility and assignment rules."""

from __future__ import annotations

from app.models.service import ServiceRequest
from app.models.user import User
from app.services.role_access import is_system_admin, role_key

SERVICE_DESK_ROLES = frozenset({"service", "indcool_service"})
SERVICE_MANAGER_ROLES = frozenset({"service_manager"})
SERVICE_VIEW_ALL_ROLES = frozenset({
    "admin",
    "incool",
    "indcool",
    "indcool service",
    "service_manager",
    "sub_admin",
})
LEGACY_SERVICE_OPS_ROLES = frozenset({
    "admin",
    "incool",
    "indcool",
    "indcool service",
    "indcool_service",
    "service",
    "service_manager",
    "sub_admin",
})


def is_service_desk_user(user: User) -> bool:
    return role_key(user.role) in SERVICE_DESK_ROLES


def is_service_manager(user: User) -> bool:
    key = role_key(user.role)
    return key in SERVICE_MANAGER_ROLES or key == "sub_admin" or is_system_admin(user)


def can_view_all_service_requests(user: User) -> bool:
    return role_key(user.role) in SERVICE_VIEW_ALL_ROLES or is_system_admin(user)


def is_service_operations_member(user: User) -> bool:
    """User belongs to internal service operations (desk, manager, or legacy ops roles)."""
    return role_key(user.role) in LEGACY_SERVICE_OPS_ROLES


def can_assign_service_desk_user(user: User) -> bool:
    return is_service_manager(user) or role_key(user.role) == "admin"


def can_manage_field_assignments(user: User) -> bool:
    """Assign engineers/vendors — full-access service ops roles only (not desk)."""
    return can_view_all_service_requests(user)


def service_request_visible_to_user(service: ServiceRequest, user: User) -> bool:
    if can_view_all_service_requests(user):
        return True
    if is_service_desk_user(user):
        return service.assigned_service_user_id == user.id
    return False


def service_desk_user_can_work(service: ServiceRequest, user: User) -> bool:
    if not is_service_desk_user(user):
        return False
    return service.assigned_service_user_id == user.id


def service_operations_can_work(service: ServiceRequest, user: User) -> bool:
    if can_view_all_service_requests(user):
        return True
    return service_desk_user_can_work(service, user)
