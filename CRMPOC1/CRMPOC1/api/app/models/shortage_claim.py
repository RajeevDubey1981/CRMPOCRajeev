"""A claim for an item missing from a new delivery (copper pipe, remote, gas charge ...), discovered by the
technical team during a service or installation visit. Pinned on the manufacturer, the transporter or an
insurance policy once reviewed; approved the same two-stage way as everything else (Service Manager, then
Admin/Sub Admin). Lives alongside the customer warranty claims in Claim (models/claim.py), as a second tab
on the same Claims page."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.models._mixins import TimestampMixin

FLOWS = ("service", "installation", "parts")
STAGES = ("svm", "sub", "done", "rejected")
RESPONSIBLE_TYPES = ("mfg", "trans", "ins", "company")
REQUIRED_PHOTOS = 4


class ShortageClaim(Base, TimestampMixin):
    __tablename__ = "shortage_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    flow: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # service | installation

    service_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("service_requests.id"), nullable=True, index=True)
    installation_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("installation_requests.id"), nullable=True, index=True)
    # Parts requests live in the separate indcool_parts database, so this is a plain id, not a real FK.
    item_request_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    serial_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Claimed value, if known at raise time. Above APPROVAL_CAP_AMOUNT (2500) — or if left blank — a Service
    # Manager approval still needs Admin/Sub Admin after it; at or under it, Service Manager can close it outright.
    amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    stage: Mapped[str] = mapped_column(String(10), nullable=False, default="svm", index=True)
    # Null = use REQUIRED_PHOTOS (4). Set to 0 when the engineer's serial-verification photos were already
    # paired onto this claim at raise time — nothing further to prove, the machine's already on record.
    required_photos_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    responsible_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # mfg | trans | ins | company
    vendor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    courier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    insurer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    raised_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)


class ShortageClaimItem(Base):
    """One missing item on a claim (a claim can list more than one: copper pipe AND gas, say)."""

    __tablename__ = "shortage_claim_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("shortage_claims.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)


class ShortageClaimPhoto(Base):
    __tablename__ = "shortage_claim_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("shortage_claims.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uploaded_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ShortageClaimEvent(Base):
    __tablename__ = "shortage_claim_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("shortage_claims.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
