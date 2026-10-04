import { isSystemAdminRole } from "./roles.js";

// Does this user's role table give `action` (can_view / can_create / can_edit / can_delete / can_export)
// on `module`? For modules that are split by type (complaints) pass the type as `subModule`.
// This mirrors the server (services/permissions.py): a row without sub-module = every record, a row with a
// sub-module = only that type. A system admin is only let through when no rows exist for the module at all.
export function hasPermission(user, module, action, subModule = null) {
  const rows = Array.isArray(user?.permissions) ? user.permissions.filter((p) => p.module === module) : [];
  if (rows.length === 0) return isSystemAdminRole(user?.role);
  const allowed = rows.filter((p) => p[action]);
  if (allowed.some((p) => (p.sub_module ?? null) === null)) return true;
  if (subModule == null) return false;
  return allowed.some((p) => p.sub_module === subModule);
}
