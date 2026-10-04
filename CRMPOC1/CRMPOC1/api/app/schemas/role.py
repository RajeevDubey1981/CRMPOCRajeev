from datetime import datetime

from pydantic import BaseModel, Field

# Top-level modules
MODULES = (
    "complaints",
    "installations",
    "orders",
    "vendors",
    "items",
    "couriers",
    "calls",
    "claims",
    "users",
    "roles",
    "dashboard",
    "services",
    "partner_registrations",
    "payments",     # Payment History page (view only)
    "email_logs",   # email send logs and bounced addresses (view only)
    "bids",         # Bid management; vendors only, the bid team comes from the user tick
)

# Modules with sub-module scoping. A sub_module=None permission row means
# "all", a sub_module="<value>" row scopes the permission to just that value.
SUB_MODULES: dict[str, tuple[str, ...]] = {
    "complaints": ("Service", "Installation", "Sales", "Others"),
}


class PermissionItem(BaseModel):
    module: str
    sub_module: str | None = None
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_export: bool = False


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RoleDetail(RoleOut):
    permissions: list[PermissionItem]
    user_count: int = 0


class PermissionsBulkUpdate(BaseModel):
    permissions: list[PermissionItem]


class PermissionsMatrixRow(BaseModel):
    role: str
    role_id: int
    permissions: list[PermissionItem]


class ModulesResponse(BaseModel):
    modules: list[str]
    sub_modules: dict[str, list[str]]
