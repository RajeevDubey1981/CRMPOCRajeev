export const REQUIRED_PERMISSION_MODULES = ["partner_registrations", "payments", "email_logs"];

// These modules only have a "View" right (nothing to create, edit or delete).
export const VIEW_ONLY_MODULES = ["payments", "email_logs"];

export const MODULE_LABELS = {
  partner_registrations: "Partner Registrations",
  payments: "Payment History (view only)",
  email_logs: "Email logs & bounces (view only)",
  users: "Users (a Sub Admin: normal users only)",
};

export function normalizePermissionModules(modules = []) {
  return [...new Set([...(modules || []), ...REQUIRED_PERMISSION_MODULES])];
}

export function moduleLabel(module) {
  return MODULE_LABELS[module] || module;
}
