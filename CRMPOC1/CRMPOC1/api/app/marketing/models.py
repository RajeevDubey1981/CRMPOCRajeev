"""Tables of the Marketing database. Columns named crm_* hold a number that points into the CRM database; there is
no foreign key to it. This first release holds who may use Marketing (ticks, with their history), the people, and the
settings. Contacts, consent, audiences and campaigns are added in the next releases."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
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


class MkChannel(MarketingBase, Stamped):
    """A connected platform account holder (for example the Meta login of the person who connected). The token is kept
    encrypted. crm_user_id points at users.id."""

    __tablename__ = "mk_channel"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # meta ...
    ext_user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ext_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")  # connected | expired | removed
    connected_by: Mapped[int] = mapped_column(Integer, nullable=False)  # crm user id


class MkChannelAsset(MarketingBase, Stamped):
    """Something the connected login can use: an ad account now; a Page or an Instagram account later."""

    __tablename__ = "mk_channel_asset"
    __table_args__ = (UniqueConstraint("channel_id", "kind", "ext_id", name="uq_mk_channel_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # ad_account | page | instagram
    ext_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    in_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # the ones the CRM works with


class MkBanner(MarketingBase, Stamped):
    """A festive/offer banner shown at the top of outgoing CRM emails while it is active."""

    __tablename__ = "mk_banner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="green")  # green | violet | navy
    greeting: Mapped[str] = mapped_column(String(60), nullable=False, default="")  # e.g. "Happy Diwali!"
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    pill1: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    pill2: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    cta_text: Mapped[str] = mapped_column(String(40), nullable=False, default="Shop Now")
    cta_link: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    start_date: Mapped[date_] = mapped_column(Date, nullable=False)
    end_date: Mapped[date_] = mapped_column(Date, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all")  # all (more targets come with Audiences)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # crm user id


class MkAudience(MarketingBase, Stamped):
    """A saved filter over the CRM's own Sales leads (prospects) or Orders (existing customers).
    Nothing is copied here -- the count and matches are computed live from the CRM database each time."""

    __tablename__ = "mk_audience"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="prospects")  # prospects | customers
    market: Mapped[str | None] = mapped_column(String(20), nullable=True)  # lead_type / Order.market key, or null = any
    stage: Mapped[str | None] = mapped_column(String(20), nullable=True)  # SalesLead.status key, or "interested_open"
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)  # place filter
    stale_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # no action in at least this many days
    heat: Mapped[str | None] = mapped_column(String(10), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # crm user id
