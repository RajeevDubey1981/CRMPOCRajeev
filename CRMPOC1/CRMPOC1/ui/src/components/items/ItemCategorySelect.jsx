import { useEffect, useMemo, useState } from "react";

import { itemsApi } from "../../api/items.js";
import { DEFAULT_ITEM_CATEGORIES } from "../../data/itemCategories.js";
import { readItemCategoryExtras } from "../../utils/itemCategoryExtras.js";

export default function ItemCategorySelect({
  value,
  onChange,
  className = "",
  disabled = false,
  placeholder = "— Select category —",
}) {
  const [dbCategories, setDbCategories] = useState([]);
  const [extras, setExtras] = useState(() => readItemCategoryExtras());

  function reloadCategories() {
    itemsApi.categories().then(setDbCategories).catch(() => setDbCategories([]));
    setExtras(readItemCategoryExtras());
  }

  useEffect(() => {
    reloadCategories();
    const onUpdate = () => reloadCategories();
    window.addEventListener("item-categories-updated", onUpdate);
    return () => window.removeEventListener("item-categories-updated", onUpdate);
  }, []);

  const options = useMemo(() => {
    const merged = new Set([...DEFAULT_ITEM_CATEGORIES, ...dbCategories, ...extras]);
    if (value) merged.add(value);
    return Array.from(merged).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  }, [dbCategories, extras, value]);

  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={`w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:bg-slate-100 ${className}`}
    >
      <option value="">{placeholder}</option>
      {options.map((c) => (
        <option key={c} value={c}>{c}</option>
      ))}
    </select>
  );
}
