"""Who may do what in Bid Management.

manage   admin, incool, sub_admin, or any non-vendor user ticked "Can manage bids" by an admin / sub admin
override only admin, incool and sub_admin: take a locked bid back or give it to someone else
vendor   role vendor with the bids module switched on in the role card; sees and asks for own bids only
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vendor import Vendor
from app.services.permissions import can_act_on
from app.services.role_access import role_key
from app.services.vendor_accounts import vendor_master_for_user

OVERRIDE_ROLES = frozenset({"admin", "incool", "sub_admin"})


@dataclass
class BidAccess:
    mode: str  # "manage" | "vendor"
    can_override: bool
    vendor: Vendor | None = None

    @property
    def is_manager(self) -> bool:
        return self.mode == "manage"


def can_override_bids(user: User) -> bool:
    return role_key(user.role) in OVERRIDE_ROLES


def is_bid_manager(user: User) -> bool:
    key = role_key(user.role)
    if key in OVERRIDE_ROLES:
        return True
    return bool(getattr(user, "can_manage_bids", False)) and key != "vendor"


def bid_access(db: Session, user: User) -> BidAccess | None:
    if is_bid_manager(user):
        return BidAccess(mode="manage", can_override=can_override_bids(user))
    if role_key(user.role) == "vendor" and can_act_on(db, user, "bids", "can_view", None):
        vendor = vendor_master_for_user(db, user)
        if vendor is not None:
            return BidAccess(mode="vendor", can_override=False, vendor=vendor)
    return None


def synthetic_bid_permission(db: Session, user: User) -> dict | None:
    """The `bids` row of /api/auth/me. Managers come from the tick, vendors from their role card."""
    if is_bid_manager(user):
        return {
            "can_view": True, "can_create": True, "can_edit": True,
            "can_delete": can_override_bids(user), "can_export": True,
        }
    if bid_access(db, user) is not None:
        return {"can_view": True, "can_create": True, "can_edit": False, "can_delete": False, "can_export": False}
    return None
