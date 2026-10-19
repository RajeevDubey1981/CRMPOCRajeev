"""Who may use Parts, and what each person may do inside it.

Roles, reusing the CRM's own role names (no new role is introduced):
- engineer: raises requests from the field, never sees amounts, never approves.
- service_manager: first approval on every request.
- admin / sub_admin (and the legacy incool/indcool/indcool_service/service accounts that already do service-desk
  work): second approval where one is needed, and can act at either stage.
- sales: read-only on the spare-parts catalogue (for quotations); no access to Approvals.
Everyone else (callcenter, vendor, ...) has no access to Parts.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.models.user import User
from app.parts.db import parts_enabled
from app.services.permissions import can_act_on
from app.services.role_access import role_key

SERVICE_MANAGER_ROLES = frozenset({"service_manager"})
SUB_STAGE_ROLES = frozenset({"admin", "incool", "sub_admin"})
SERVICE_DESK_ROLES = frozenset({"service", "indcool", "indcool service", "indcool_service"})
SALES_READ_ROLES = frozenset({"sales", "sales_manager"})


@dataclass
class Ctx:
    user: User
    role: str

    @property
    def is_engineer(self) -> bool:
        return self.role == "engineer"

    @property
    def is_service_manager(self) -> bool:
        return self.role in SERVICE_MANAGER_ROLES

    @property
    def is_second_stage(self) -> bool:
        return self.role in SUB_STAGE_ROLES

    @property
    def can_see_amounts(self) -> bool:
        return not self.is_engineer

    @property
    def can_see_approvals(self) -> bool:
        return self.role in (SERVICE_MANAGER_ROLES | SUB_STAGE_ROLES | SERVICE_DESK_ROLES)

    def can_act_on_stage(self, stage: str) -> bool:
        if stage == "svm":
            return self.is_service_manager or self.is_second_stage
        if stage == "sub":
            return self.is_second_stage
        return False


def get_ctx(user: User = Depends(get_current_user)) -> Ctx:
    if not parts_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The Parts module is not set up yet")
    return Ctx(user=user, role=role_key(user.role))


def require_catalogue_edit(ctx: Ctx, db: Session, *, flag: str = "can_edit") -> None:
    """The spare-parts catalogue lives under Item Master, so changing it needs the same Roles-screen
    permission as editing an item (module "items"), not a fixed list of roles."""
    if not can_act_on(db, ctx.user, "items", flag, None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot change the item/spare-parts catalogue")


def require_approvals_access(ctx: Ctx) -> None:
    if not ctx.can_see_approvals:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to Approvals")
