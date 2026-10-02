export const REQUIRED_PERMISSION_MODULES = ["partner_registrations"];

export const MODULE_LABELS = {
  partner_registrations: "Partner Registrations",
};

export function normalizePermissionModules(modules = []) {
  return [...new Set([...(modules || []), ...REQUIRED_PERMISSION_MODULES])];
}

export function moduleLabel(module) {
  return MODULE_LABELS[module] || module;
}
