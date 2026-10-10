"""Who may use Sales, and what each person may do inside it.

Two layers, as in the preview:
1. the CRM role card has one module "sales" (view): it only shows the Sales menu;
2. inside Sales, ticks kept in the Sales database: a built-in default per role (team or manager), a choice by Admin
   for the whole role, and a choice by Admin for one person. Admin and Sub Admin always have everything except what
   is not theirs to give (nothing is locked from them).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.role import Permission, Role
from app.models.user import User
from app.sales.db import get_sales_db, sales_enabled
from app.sales.models import SalesRoleTick, SalesUserTick
from app.sales.rules import ALL_TICKS, LOCKED_TICKS, TICK_DEFAULTS
from app.services.role_access import permission_role_name, role_key

ADMIN_ROLES = frozenset({"admin", "incool", "sub_admin"})
MANAGER_ROLES = frozenset({"sales_manager"})


def is_admin_user(user: User) -> bool:
    return role_key(user.role) in ADMIN_ROLES


def role_tick_key(role: str | None) -> str:
    return "mgr" if role_key(role) in MANAGER_ROLES else "team"


def has_sales_menu(main_db: Session, user: User) -> bool:
    """The role card: admins always, others when their role card has the Sales module ticked for view."""
    if not sales_enabled():
        return False
    if is_admin_user(user):
        return True
    name = permission_role_name(user.role)
    role = main_db.scalar(select(Role).where(func.lower(func.trim(Role.name)) == name))
    if role is None:
        return False
    row = main_db.scalar(
        select(Permission).where(Permission.role_id == role.id, Permission.module == "sales", Permission.sub_module.is_(None))
    )
    return bool(row and row.can_view)


def role_ticks(sdb: Session, role_key_: str) -> set[str]:
    ticks = set(TICK_DEFAULTS[role_key_])
    for row in sdb.scalars(select(SalesRoleTick).where(SalesRoleTick.role_key == role_key_)):
        (ticks.add if row.allowed else ticks.discard)(row.tick_key)
    return ticks - LOCKED_TICKS


def user_ticks(sdb: Session, user: User) -> set[str]:
    if is_admin_user(user):
        return set(ALL_TICKS)
    ticks = role_ticks(sdb, role_tick_key(user.role))
    for row in sdb.scalars(select(SalesUserTick).where(SalesUserTick.crm_user_id == user.id)):
        (ticks.add if row.allowed else ticks.discard)(row.tick_key)
    return ticks - LOCKED_TICKS


@dataclass
class Ctx:
    user: User
    ticks: set[str] = field(default_factory=set)
    is_admin: bool = False

    def has(self, key: str) -> bool:
        return key in self.ticks

    def any(self, *keys: str) -> bool:
        return any(k in self.ticks for k in keys)


def get_ctx(
    user: User = Depends(get_current_user),
    main_db: Session = Depends(get_db),
    sdb: Session = Depends(get_sales_db),
) -> Ctx:
    if not has_sales_menu(main_db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have the Sales menu")
    return Ctx(user=user, ticks=user_ticks(sdb, user), is_admin=is_admin_user(user))


def require(*keys: str):
    """A dependency that needs at least one of the ticks."""

    def checker(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if not ctx.any(*keys):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have this tick in Sales")
        return ctx

    return checker


def menu_flags(ctx: Ctx) -> dict:
    t = ctx.has
    return {
        "my_day": True,
        "leads_all": t("see_all"),
        "quotations": t("make_quote") or t("approve_quote"),
        "approvals": t("approve_quote") or t("approve_disp"),
        "export_desk": t("exp_desk"),
        "connect": t("connect"),
        "team": t("others_profile") or t("targets") or ctx.is_admin,
        "ticks": ctx.is_admin,
        "team_dashboard": t("team_dash"),
        "company_dashboard": t("co_dash"),
    }
