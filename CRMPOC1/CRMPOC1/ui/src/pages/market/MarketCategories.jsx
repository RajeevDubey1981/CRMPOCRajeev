import { useEffect, useState } from "react";
import { marketApi } from "../../api/market.js";
import Modal from "../../components/Modal.jsx";

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN"); } catch { return s; }
}

const EMPTY_FORM = { name: "", parent_id: "" };

export default function MarketCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createErr, setCreateErr] = useState("");

  const [editCat, setEditCat] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editErr, setEditErr] = useState("");

  const [confirmDelete, setConfirmDelete] = useState(null);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setCategories(await marketApi.listCategories());
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load categories");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function doCreate() {
    setCreateErr("");
    try {
      const body = {
        name: createForm.name.trim(),
        parent_id: createForm.parent_id ? parseInt(createForm.parent_id) : null,
      };
      if (!body.name) { setCreateErr("Name is required"); return; }
      await marketApi.createCategory(body);
      setCreateOpen(false);
      setCreateForm(EMPTY_FORM);
      load();
    } catch (e) {
      setCreateErr(e.response?.data?.detail || "Failed to create category");
    }
  }

  function openEdit(cat) {
    setEditCat(cat);
    setEditForm({
      name: cat.name,
      parent_id: cat.parent_id != null ? String(cat.parent_id) : "",
    });
    setEditErr("");
  }

  async function doEdit() {
    setEditErr("");
    try {
      const body = {
        name: editForm.name.trim(),
        parent_id: editForm.parent_id ? parseInt(editForm.parent_id) : null,
      };
      if (!body.name) { setEditErr("Name is required"); return; }
      await marketApi.updateCategory(editCat.id, body);
      setEditCat(null);
      load();
    } catch (e) {
      setEditErr(e.response?.data?.detail || "Failed to update category");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await marketApi.deleteCategory(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete category");
    }
  }

  // Compute summary stats
  const total = categories.length;
  const rootCats = categories.filter((c) => !c.parent_id).length;
  const subCats = categories.filter((c) => !!c.parent_id).length;
  const withItems = categories.filter((c) => c.item_count > 0).length;

  // Sort: roots first, then children grouped under parents
  const sorted = [];
  const roots = categories.filter((c) => !c.parent_id);
  const childMap = {};
  for (const c of categories) {
    if (c.parent_id) {
      if (!childMap[c.parent_id]) childMap[c.parent_id] = [];
      childMap[c.parent_id].push(c);
    }
  }
  for (const r of roots) {
    sorted.push({ ...r, _depth: 0 });
    if (childMap[r.id]) {
      for (const child of childMap[r.id]) {
        sorted.push({ ...child, _depth: 1 });
      }
    }
  }

  function CategoryForm({ form, setForm, submitLabel, onSubmit, onCancel, selfId = null }) {
    // Exclude self and self's children from parent dropdown
    const eligible = categories.filter(
      (c) => c.id !== selfId && c.parent_id !== selfId
    );
    return (
      <div className="space-y-3">
        <div>
          <label className={labelClass}>Category Name *</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className={fieldClass}
            placeholder="e.g. Air Conditioners"
          />
        </div>
        <div>
          <label className={labelClass}>Parent Category (optional)</label>
          <select
            value={form.parent_id}
            onChange={(e) => setForm((f) => ({ ...f, parent_id: e.target.value }))}
            className={fieldClass}
          >
            <option value="">Root Category (no parent)</option>
            {eligible.filter((c) => !c.parent_id).map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >Cancel</button>
          <button
            type="button"
            onClick={onSubmit}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >{submitLabel}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Market Categories</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Total: {total} | Root: {rootCats} | Sub: {subCats} | With Items: {withItems}
          </p>
        </div>
        <button
          onClick={() => { setCreateForm(EMPTY_FORM); setCreateErr(""); setCreateOpen(true); }}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + Add Category
        </button>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Parent</th>
              <th className="px-3 py-2">Items</th>
              <th className="px-3 py-2">Sub-categories</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">No categories yet.</td></tr>
            )}
            {!loading && sorted.map((cat) => (
              <tr key={cat.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  {cat._depth > 0 && (
                    <span className="mr-1 font-mono text-slate-400 select-none">└──</span>
                  )}
                  <span className={cat._depth > 0 ? "text-slate-600" : "font-medium text-slate-800"}>
                    {cat.name}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-500">{cat.parent_name || "Root"}</td>
                <td className="px-3 py-2">
                  {cat.item_count > 0
                    ? <span className="font-medium text-slate-700">{cat.item_count}</span>
                    : <span className="text-slate-400">0</span>
                  }
                </td>
                <td className="px-3 py-2">
                  {cat.child_count > 0
                    ? <span className="font-medium text-slate-700">{cat.child_count}</span>
                    : <span className="text-slate-400">0</span>
                  }
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(cat.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="Edit"
                      onClick={() => openEdit(cat)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >✏️</button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(cat)}
                      className="rounded p-1 text-rose-600 hover:bg-rose-50"
                    >🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add Category">
        {createErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{createErr}</div>}
        <CategoryForm
          form={createForm}
          setForm={setCreateForm}
          submitLabel="Add Category"
          onSubmit={doCreate}
          onCancel={() => setCreateOpen(false)}
        />
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editCat} onClose={() => setEditCat(null)} title="Edit Category">
        {editErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{editErr}</div>}
        <CategoryForm
          form={editForm}
          setForm={setEditForm}
          submitLabel="Save Changes"
          onSubmit={doEdit}
          onCancel={() => setEditCat(null)}
          selfId={editCat?.id}
        />
      </Modal>

      {/* Delete Confirm */}
      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete Category?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete category <strong>{confirmDelete?.name}</strong>?
            {confirmDelete?.child_count > 0 && (
              <span className="block mt-1 text-amber-700">
                Warning: this category has {confirmDelete.child_count} sub-categor{confirmDelete.child_count === 1 ? "y" : "ies"}.
                Deleting it may affect those sub-categories.
              </span>
            )}
            {confirmDelete?.item_count > 0 && (
              <span className="block mt-1 text-amber-700">
                Warning: {confirmDelete.item_count} item{confirmDelete.item_count === 1 ? " is" : "s are"} assigned to this category.
              </span>
            )}
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
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
