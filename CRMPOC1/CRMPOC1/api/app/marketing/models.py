"""Tables of the Marketing database. Columns named crm_* hold a number that points into the CRM database; there is
no foreign key to it. This first release holds who may use Marketing (ticks, with their history), the people, and the
settings. Contacts, consent, audiences and campaigns are added in the next releases."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.marketing.db import MarketingBase


class Stamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class MkProfile(MarketingBase, Stamped):
    """A person who uses Marketing. crm_user_id points at users.id."""

    __tablename__ = "mk_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    crm_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name_cache: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role_cache: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MkRoleTick(MarketingBase):
    """Admin's choice for a whole kind of person (team, mgr, oth, mkt): one row per tick that differs from the default."""

    __tablename__ = "mk_role_tick"
    __table_args__ = (UniqueConstraint("role_key", "tick_key", name="uq_mk_role_tick"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str] = mapped_column(String(20), nullable=False)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MkUserTick(MarketingBase):
    """Admin's choice for one person, when it differs from their kind."""

    __tablename__ = "mk_user_tick"
    __table_args__ = (UniqueConstraint("crm_user_id", "tick_key", name="uq_mk_user_tick"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crm_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MkTickHistory(MarketingBase):
    __tablename__ = "mk_tick_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    crm_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tick_key: Mapped[str] = mapped_column(String(60), nullable=False)
    allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # null = back to the default
    by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    by_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MkSetting(MarketingBase):
    __tablename__ = "mk_setting"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
