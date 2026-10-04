export const REQUIRED_PERMISSION_MODULES = ["partner_registrations", "payments", "email_logs"];

// These modules only have a "View" right (nothing to create, edit or delete).
export const VIEW_ONLY_MODULES = ["payments", "email_logs"];

export const MODULE_LABELS = {
  partner_registrations: "Partner Registrations",
  payments: "Payment History (view only)",
  email_logs: "Email logs & bounces (view only)",
  users: "Users (a Sub Admin: normal users only)",
  store_receiving: "Store: Receive goods (GRN). Create = scan and submit",
  store_approval: "Store: Approve GRN. Edit = approve and post",
  store_stock: "Store: Stock and ledger",
  acc_items: "Accounts: Items and BOM. Create = draft a BOM, Edit = activate it",
  acc_purchase: "Accounts: Suppliers and purchase orders. Create = raise a PO",
  acc_po_approval: "Accounts: Approve purchase orders. Edit = approve",
  acc_assembly: "Accounts: Assembly orders. Create = plan, Edit = complete with serials",
  store_dispatch: "Store: Reserve and dispatch orders. Create = reserve and dispatch, Edit = release reserved stock",
};

export function normalizePermissionModules(modules = []) {
  return [...new Set([...(modules || []), ...REQUIRED_PERMISSION_MODULES])];
}

export function moduleLabel(module) {
  return MODULE_LABELS[module] || module;
}
