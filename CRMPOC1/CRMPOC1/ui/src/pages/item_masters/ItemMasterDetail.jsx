import { hasPermission } from "../../utils/permissions.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import { itemsApi } from "../../api/items.js";
import ItemCategorySelect from "../../components/items/ItemCategorySelect.jsx";

const UNITS = ["Pcs", "Set", "Nos", "Kit", "Kg", "Ltr"];

function fmt(s) { return s ? new Date(s).toLocaleString() : "—"; }

function fmtMrp(v) {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function Field({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>
        {value ?? <span className="text-slate-400">—</span>}
      </div>
    </div>
  );
}

export default function ItemMasterDetail() {
  const { user: permUser } = useAuth();
  const canDeletePerm = hasPermission(permUser, "items", "can_delete");
  const navigate = useNavigate();
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function load() {
    try {
      const data = await itemsApi.get(id);
      setItem(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load item");
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  function openEdit() {
    setEditForm({
      item_code: item.item_code,
      item_name: item.item_name,
      category: item.category || "",
      description: item.description || "",
      brand: item.brand || "",
      unit: item.unit || "",
      hsn_code: item.hsn_code || "",
      mrp: item.mrp !== null && item.mrp !== undefined ? String(item.mrp) : "",
      serial_count: String(item.serial_count ?? 1),
      is_active: item.is_active,
    });
    setSaveErr("");
    setEditing(true);
  }

  function setField(field, value) { setEditForm((f) => ({ ...f, [field]: value })); }

  async function saveEdit(e) {
    e.preventDefault();
    setSaveErr("");
    setSaving(true);
    try {
      const body = {
        item_code: editForm.item_code,
        item_name: editForm.item_name,
        category: editForm.category || null,
        description: editForm.description || null,
        brand: editForm.brand || null,
        unit: editForm.unit || null,
        hsn_code: editForm.hsn_code || null,
        mrp: editForm.mrp !== "" ? parseFloat(editForm.mrp) : null,
        serial_count: editForm.serial_count !== "" ? parseInt(editForm.serial_count, 10) : 1,
        is_active: editForm.is_active,
      };
      const updated = await itemsApi.update(id, body);
      setItem(updated);
      setEditing(false);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setSaveErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function doDelete() {
    try {
      await itemsApi.remove(id);
      navigate("/items");
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  if (err) return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  if (!item) return <div className="text-center text-slate-500 py-10">Loading…</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/items" className="text-sm text-brand-600 hover:underline">← Back to Item Masters</Link>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-bold text-slate-900">
            <span className="font-mono text-slate-500">{item.item_code}</span>
            <span>{item.item_name}</span>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              item.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
            }`}>
              {item.is_active ? "Active" : "Inactive"}
            </span>
          </h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={openEdit}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            ✏️ Edit
          </button>
{canDeletePerm && (
          <button
            onClick={() => setConfirmDelete(true)}
            className="rounded-md border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50"
          >
            🗑 Delete
          </button>
)}
        </div>
      </div>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Item details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Item Code" value={item.item_code} mono />
          <Field label="Item Name" value={item.item_name} />
          <Field label="Category" value={item.category} />
          <Field label="Brand" value={item.brand} />
          <Field label="Unit" value={item.unit} />
          <Field label="HSN Code" value={item.hsn_code} mono />
          <Field label="MRP" value={fmtMrp(item.mrp)} />
          <Field
            label="Serial numbers per unit"
            value={
              item.serial_count === 0
                ? "0 — no serial tracking"
                : item.serial_count === 2
                  ? "2 — Serial Number 1 and 2"
                  : "1 — Serial Number 1 only"
            }
          />
          <Field label="Status" value={item.is_active ? "Active" : "Inactive"} />
          <Field label="Description" value={item.description} full />
          <Field label="Created At" value={fmt(item.created_at)} />
          <Field label="Last Updated" value={fmt(item.updated_at)} />
        </div>
      </section>

      {/* Edit Modal */}
      <Modal open={editing} onClose={() => setEditing(false)} title="Edit Item">
        <form onSubmit={saveEdit} className="space-y-4">
          {saveErr && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{saveErr}</div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Item Code *</label>
              <input
                required
                value={editForm?.item_code || ""}
                onChange={(e) => setField("item_code", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Item Name *</label>
              <input
                required
                value={editForm?.item_name || ""}
                onChange={(e) => setField("item_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Category</label>
              <ItemCategorySelect
                value={editForm?.category || ""}
                onChange={(v) => setField("category", v)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Brand</label>
              <input
                value={editForm?.brand || ""}
                onChange={(e) => setField("brand", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Unit</label>
              <select
                value={editForm?.unit || ""}
                onChange={(e) => setField("unit", e.target.value)}
                className={fieldClass}
              >
                <option value="">— Select unit —</option>
                {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>HSN Code</label>
              <input
                value={editForm?.hsn_code || ""}
                onChange={(e) => setField("hsn_code", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>MRP (₹)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={editForm?.mrp ?? ""}
                onChange={(e) => setField("mrp", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Serial numbers per unit</label>
              <select
                value={editForm?.serial_count ?? "1"}
                onChange={(e) => setField("serial_count", e.target.value)}
                className={fieldClass}
              >
                <option value="0">0 — no serial tracking</option>
                <option value="1">1 — Serial Number 1 only</option>
                <option value="2">2 — Serial Number 1 and 2</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="edit_is_active"
                checked={editForm?.is_active ?? true}
                onChange={(e) => setField("is_active", e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="edit_is_active" className="text-sm font-medium text-slate-700">Active</label>
            </div>
          </div>
          <div>
            <label className={labelClass}>Description</label>
            <textarea
              rows={3}
              value={editForm?.description || ""}
              onChange={(e) => setField("description", e.target.value)}
              className={fieldClass}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete item?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete item <span className="font-mono">{item.item_code}</span>{" "}
            — <strong>{item.item_name}</strong>. This action can be reversed by an admin.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >Delete</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
