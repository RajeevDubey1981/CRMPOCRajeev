"""Who may use Marketing, and what each person may do inside it.

Two layers, the same idea as Bid management and Sales:
1. the Marketing menu: Admin and Sub Admin always, the role "marketing", and anyone who has the tick "Can manage
   marketing" on their user (given only by Admin or Sub Admin). Nobody sees it while the Marketing database is not set up.
2. inside Marketing, ticks kept in the Marketing database: a built-in default for each kind of person, a choice by
   Admin for a whole kind, and a choice by Admin for one person.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.marketing.db import get_marketing_db, marketing_enabled
from app.marketing.models import MkRoleTick, MkUserTick
from app.marketing.rules import ALL_TICKS, LOCKED_TICKS, TICK_DEFAULTS
from app.models.user import User
from app.services.role_access import role_key

ADMIN_ROLES = frozenset({"admin", "incool", "sub_admin"})
MARKETING_ROLES = frozenset({"marketing", "marketing_manager"})
NEVER_ROLES = frozenset({"vendor", "engineer"})  # these cannot be given Marketing


def is_admin_user(user: User) -> bool:
    return role_key(user.role) in ADMIN_ROLES


def kind_of(user: User) -> str:
    r = role_key(user.role)
    return "mgr" if r == "sales_manager" else "team" if r == "sales" else "mkt" if r == "marketing" else "mktm" if r == "marketing_manager" else "oth"


def has_marketing_menu(user: User) -> bool:
    if not marketing_enabled() or not user.is_active or user.deleted_at is not None:
        return False
    r = role_key(user.role)
    if r in NEVER_ROLES:
        return False
    return r in ADMIN_ROLES or r in MARKETING_ROLES or bool(getattr(user, "can_manage_marketing", False))


def kind_ticks(mdb: Session, kind: str) -> set[str]:
    ticks = set(TICK_DEFAULTS[kind])
    for row in mdb.scalars(select(MkRoleTick).where(MkRoleTick.role_key == kind)):
        (ticks.add if row.allowed else ticks.discard)(row.tick_key)
    return ticks - LOCKED_TICKS


def user_ticks(mdb: Session, user: User) -> set[str]:
    if is_admin_user(user):
        return set(ALL_TICKS)
    ticks = kind_ticks(mdb, kind_of(user))
    for row in mdb.scalars(select(MkUserTick).where(MkUserTick.crm_user_id == user.id)):
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


def get_ctx(user: User = Depends(get_current_user), mdb: Session = Depends(get_marketing_db)) -> Ctx:
    if not has_marketing_menu(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have the Marketing menu")
    return Ctx(user=user, ticks=user_ticks(mdb, user), is_admin=is_admin_user(user))


def require(*keys: str):
    """A dependency that needs at least one of the ticks."""

    def checker(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if not ctx.any(*keys):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have this tick in Marketing")
        return ctx

    return checker


def menu_flags(ctx: Ctx) -> dict:
    t = ctx.has
    return {
        "overview": t("view"),
        "audiences": t("aud_own") or t("aud_all"),
        "campaigns": t("draft") or t("submit") or t("approve"),
        "consent": t("consent_edit") or ctx.is_admin,
        "ticks": ctx.is_admin,
        "settings": t("settings") or t("cost"),
        "channels": t("cost") or t("connect"),
    }
