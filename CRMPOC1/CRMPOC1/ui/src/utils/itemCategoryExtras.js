const STORAGE_KEY = "indcool_item_category_extras";

export function readItemCategoryExtras() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string" && v.trim()) : [];
  } catch {
    return [];
  }
}

export function addItemCategoryExtra(name) {
  const trimmed = (name || "").trim();
  if (!trimmed) return false;
  const merged = new Set([...readItemCategoryExtras(), trimmed]);
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...merged].sort()));
  window.dispatchEvent(new CustomEvent("item-categories-updated"));
  return true;
}
