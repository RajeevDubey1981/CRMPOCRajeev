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
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # uploaded banner image, replaces the drawn design in email
    start_date: Mapped[date_] = mapped_column(Date, nullable=False)
    end_date: Mapped[date_] = mapped_column(Date, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all")  # all | audience
    target_audience_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # set when target_type == "audience"
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # crm user id


class MkConsent(MarketingBase, Stamped):
    """A phone number or email on the Marketing STOP list -- excluded from every audience count and, later, every send.
    contact_key is the phone's digits or the email lowercased/trimmed, so it matches however it was typed elsewhere."""

    __tablename__ = "mk_consent"
    __table_args__ = (UniqueConstraint("contact_key", "channel", name="uq_mk_consent_contact_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contact_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_display: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # as typed, for the list screen
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="all")  # all | email | whatsapp | sms
    reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # manual | reply_stop
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # crm user id


class MkCampaign(MarketingBase, Stamped):
    """A message sent once to a saved audience's contacts. The audience is re-counted live at send time, not copied."""

    __tablename__ = "mk_campaign"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    audience_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # null when send_to_all
    send_to_all: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # every CRM contact with an email, not one saved audience
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # an uploaded hero banner shown above the message
    # the one product this campaign is about -- shown as a card under the hero banner, above the message
    offer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    offer_price: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    offer_mrp: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    offer_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    offer_link: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # instead of linking straight to offer_link, each Prospects contact gets their own link to a short
    # form that writes their answer onto their existing Sales lead -- no public form, no new lead, no dupes.
    collect_interest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    subject: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")  # plain text/simple HTML; {{name}} substituted per contact
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft", index=True)
    # draft | wait (needs approval) | appr (approved, about to send) | sending (batching) | sent | rejected | cancelled
    reject_reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    next_batch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)  # when "sending", when the next batch of 25 goes out
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MkCampaignLog(MarketingBase):
    """One row per contact a campaign was aimed at -- sent, or the reason it was skipped."""

    __tablename__ = "mk_campaign_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    contact_key: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    contact_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # sent | stopped | cooldown | no_email | failed
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MkContactTouch(MarketingBase):
    """The last time a contact received ANY campaign -- the cooldown that stops back-to-back promotions."""

    __tablename__ = "mk_contact_touch"

    contact_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class MkLeadInterestToken(MarketingBase, Stamped):
    """One per recipient of a collect_interest campaign -- the opaque token in their personal link.
    Points at an existing Sales lead; a submission writes onto that lead, it never creates a new one."""

    __tablename__ = "mk_lead_interest_token"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lead_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # SalesLead.id, in the Sales database
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_interest: Mapped[str | None] = mapped_column(String(10), nullable=True)  # yes | maybe
