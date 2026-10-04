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
    "store_receiving",  # Store: receive goods with a GRN (create = scan and submit)
    "store_approval",   # Store: approve and post a GRN (edit = approve)
    "store_stock",      # Store: stock on hand and the ledger
    "store_dispatch",   # Store: reserve stock for orders and dispatch with the bill (edit = release a reservation)
    "acc_items",        # Accounts: BOM and make-or-buy (create = draft a BOM, edit = activate it)
    "acc_purchase",     # Accounts: suppliers and purchase orders (create = raise a PO)
    "acc_po_approval",  # Accounts: approve a purchase order (edit = approve)
    "acc_assembly",     # Accounts: assembly orders (create = plan, edit = complete with serials)
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
