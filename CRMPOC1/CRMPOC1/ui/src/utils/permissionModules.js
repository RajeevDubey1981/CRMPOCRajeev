export const REQUIRED_PERMISSION_MODULES = ["partner_registrations", "payments", "email_logs", "historical_installations"];

// These modules only have a "View" right (nothing to create, edit or delete).
export const VIEW_ONLY_MODULES = ["payments", "email_logs"];

export const MODULE_LABELS = {
  partner_registrations: "Partner Registrations",
  payments: "Payment History (view only)",
  email_logs: "Email logs & bounces (view only)",
  historical_installations: "Historical Installations",
  users: "Users (a Sub Admin: normal users only)",
  bids: "Bids (vendors only: the bid team is set by the tick on the user)",
  vendor_ledger: "Vendor Account (Dr/Cr ledger, bank statements)",
  engineer_ledger: "Engineer Account (Dr/Cr ledger)",
  ledger_audit: "Audit (approves every ledger payment before it posts)",
};

export function normalizePermissionModules(modules = []) {
  return [...new Set([...(modules || []), ...REQUIRED_PERMISSION_MODULES])];
}

export function moduleLabel(module) {
  return MODULE_LABELS[module] || module;
}
