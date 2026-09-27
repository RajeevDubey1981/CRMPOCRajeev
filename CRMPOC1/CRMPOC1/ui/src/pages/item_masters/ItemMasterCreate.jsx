import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { itemsApi } from "../../api/items.js";
import ItemCategorySelect from "../../components/items/ItemCategorySelect.jsx";

const UNITS = ["Pcs", "Set", "Nos", "Kit", "Kg", "Ltr"];

export default function ItemMasterCreate() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    item_code: "",
    item_name: "",
    category: "",
    description: "",
    brand: "",
    unit: "",
    hsn_code: "",
    mrp: "",
    serial_count: "1",
    is_active: true,
  });

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSubmitting(true);
    try {
      const body = {
        item_code: form.item_code,
        item_name: form.item_name,
        category: form.category || null,
        description: form.description || null,
        brand: form.brand || null,
        unit: form.unit || null,
        hsn_code: form.hsn_code || null,
        mrp: form.mrp !== "" ? parseFloat(form.mrp) : null,
        serial_count: form.serial_count !== "" ? parseInt(form.serial_count, 10) : 1,
        is_active: form.is_active,
      };
      const created = await itemsApi.create(body);
      navigate(`/items/${created.id}`);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to create");
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800">New Item</h1>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <form onSubmit={submit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Item Code *</label>
            <input
              required
              value={form.item_code}
              onChange={(e) => set("item_code", e.target.value)}
              className={fieldClass}
              placeholder="e.g. 8908012210436"
            />
          </div>
          <div>
            <label className={labelClass}>Item Name *</label>
            <input
              required
              value={form.item_name}
              onChange={(e) => set("item_name", e.target.value)}
              className={fieldClass}
              placeholder="e.g. SPLIT AC IDCACS18K5"
            />
          </div>
          <div>
            <label className={labelClass}>Category</label>
            <ItemCategorySelect
              value={form.category}
              onChange={(v) => set("category", v)}
              className={fieldClass}
            />
            <p className="mt-1 text-xs text-slate-500">
              Need a new category? Use <strong>Add category</strong> on the Item Masters list page.
            </p>
          </div>
          <div>
            <label className={labelClass}>Brand</label>
            <input
              value={form.brand}
              onChange={(e) => set("brand", e.target.value)}
              className={fieldClass}
              placeholder="e.g. Indcool"
            />
          </div>
          <div>
            <label className={labelClass}>Unit</label>
            <select value={form.unit} onChange={(e) => set("unit", e.target.value)} className={fieldClass}>
              <option value="">— Select unit —</option>
              {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>HSN Code</label>
            <input
              value={form.hsn_code}
              onChange={(e) => set("hsn_code", e.target.value)}
              className={fieldClass}
              placeholder="e.g. 84151010"
            />
          </div>
          <div>
            <label className={labelClass}>MRP (₹)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.mrp}
              onChange={(e) => set("mrp", e.target.value)}
              className={fieldClass}
              placeholder="0.00"
            />
          </div>
          <div>
            <label className={labelClass}>Serial numbers per unit</label>
            <select
              value={form.serial_count}
              onChange={(e) => set("serial_count", e.target.value)}
              className={fieldClass}
            >
              <option value="0">0 — no serial tracking</option>
              <option value="1">1 — Serial Number 1 only</option>
              <option value="2">2 — Serial Number 1 and 2</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              How many serial numbers are captured per unit for this item code on orders.
            </p>
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => set("is_active", e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="is_active" className="text-sm font-medium text-slate-700">Active</label>
          </div>
        </div>

        <div>
          <label className={labelClass}>Description</label>
          <textarea
            rows={3}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            className={fieldClass}
            placeholder="Optional product description"
          />
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate("/items")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >Cancel</button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Create Item"}
          </button>
        </div>
      </form>
    </div>
  );
}
