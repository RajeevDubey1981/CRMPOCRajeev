import { useEffect, useMemo, useState } from "react";
import { marketApi } from "../../api/market.js";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN"); } catch { return s; }
}

function fmtRupee(v) {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function StatusBadge({ value }) {
  const cls =
    value === "Active"
      ? "bg-green-100 text-green-700"
      : "bg-slate-100 text-slate-500";
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {value}
    </span>
  );
}

const EMPTY_FORM = {
  sku: "",
  name: "",
  company: "",
  category_id: "",
  base_price: "",
  mrp: "",
  status: "Active",
  stock_count: "0",
  description: "",
};

function ItemForm({ form, setForm, categories, onSubmit, onCancel, submitLabel, skuReadOnly = false }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className={labelClass}>SKU *</label>
          <input
            type="text"
            value={form.sku}
            onChange={(e) => setForm((f) => ({ ...f, sku: e.target.value }))}
            className={fieldClass}
            readOnly={skuReadOnly}
          />
        </div>
        <div>
          <label className={labelClass}>Name *</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className={fieldClass}
          />
        </div>
        <div>
          <label className={labelClass}>Company</label>
          <input
            type="text"
            value={form.company}
            onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
            className={fieldClass}
          />
        </div>
        <div>
          <label className={labelClass}>Category</label>
          <select
            value={form.category_id}
            onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
            className={fieldClass}
          >
            <option value="">No category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>Base Price (₹)</label>
          <input
            type="number"
            step="0.01"
            value={form.base_price}
            onChange={(e) => setForm((f) => ({ ...f, base_price: e.target.value }))}
            className={fieldClass}
          />
        </div>
        <div>
          <label className={labelClass}>MRP (₹)</label>
          <input
            type="number"
            step="0.01"
            value={form.mrp}
            onChange={(e) => setForm((f) => ({ ...f, mrp: e.target.value }))}
            className={fieldClass}
          />
        </div>
        <div>
          <label className={labelClass}>Status</label>
          <select
            value={form.status}
            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
            className={fieldClass}
          >
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>
        <div>
          <label className={labelClass}>Stock Count</label>
          <input
            type="number"
            value={form.stock_count}
            onChange={(e) => setForm((f) => ({ ...f, stock_count: e.target.value }))}
            className={fieldClass}
          />
        </div>
      </div>
      <div>
        <label className={labelClass}>Description</label>
        <textarea
          rows={3}
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          className={fieldClass}
        />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onSubmit}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          {submitLabel}
        </button>
      </div>
    </div>
  );
}

export default function MarketItems() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({ search: "", status: "", category_id: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createErr, setCreateErr] = useState("");

  const [editItem, setEditItem] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editErr, setEditErr] = useState("");

  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: filters.status || undefined,
    category_id: filters.category_id || undefined,
    search: filters.search || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await marketApi.listItems(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load items");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    marketApi.listCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  function parseItemBody(form) {
    const body = { ...form };
    if (!body.base_price) delete body.base_price;
    else body.base_price = parseFloat(body.base_price);
    if (!body.mrp) delete body.mrp;
    else body.mrp = parseFloat(body.mrp);
    if (!body.category_id) delete body.category_id;
    else body.category_id = parseInt(body.category_id);
    body.stock_count = parseInt(body.stock_count) || 0;
    if (!body.company) delete body.company;
    if (!body.description) delete body.description;
    return body;
  }

  async function doCreate() {
    setCreateErr("");
    try {
      await marketApi.createItem(parseItemBody(createForm));
      setCreateOpen(false);
      setCreateForm(EMPTY_FORM);
      load();
    } catch (e) {
      setCreateErr(e.response?.data?.detail || "Failed to create item");
    }
  }

  function openEdit(item) {
    setEditItem(item);
    setEditForm({
      sku: item.sku || "",
      name: item.name || "",
      company: item.company || "",
      category_id: item.category_id != null ? String(item.category_id) : "",
      base_price: item.base_price != null ? String(item.base_price) : "",
      mrp: item.mrp != null ? String(item.mrp) : "",
      status: item.status || "Active",
      stock_count: String(item.stock_count ?? 0),
      description: item.description || "",
    });
    setEditErr("");
  }

  async function doEdit() {
    setEditErr("");
    try {
      const body = parseItemBody(editForm);
      delete body.sku;
      await marketApi.updateItem(editItem.id, body);
      setEditItem(null);
      load();
    } catch (e) {
      setEditErr(e.response?.data?.detail || "Failed to update item");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await marketApi.deleteItem(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete item");
    }
  }

  const totalItems = data.total;
  const activeItems = data.items.filter((i) => i.status === "Active").length;
  const lowStock = data.items.filter((i) => i.stock_count <= 5).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Market Items</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Total: {totalItems} | Active (page): {activeItems} | Low Stock (page): {lowStock}
          </p>
        </div>
        <button
          onClick={() => { setCreateForm(EMPTY_FORM); setCreateErr(""); setCreateOpen(true); }}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + Add New Item
        </button>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <input
            type="text"
            placeholder="Search SKU or name…"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={filters.status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
          <select
            value={filters.category_id}
            onChange={(e) => applyFilter({ category_id: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">SKU</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Base Price</th>
              <th className="px-3 py-2">MRP</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={11} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={11} className="px-3 py-6 text-center text-slate-500">No items found.</td></tr>
            )}
            {!loading && data.items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-500">{item.id}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-700">{item.sku}</td>
                <td className="px-3 py-2 font-medium text-slate-800">{item.name}</td>
                <td className="px-3 py-2 text-slate-600">{item.company || "—"}</td>
                <td className="px-3 py-2 text-slate-600">{item.category_name || "—"}</td>
                <td className="px-3 py-2">{fmtRupee(item.base_price)}</td>
                <td className="px-3 py-2">{fmtRupee(item.mrp)}</td>
                <td className="px-3 py-2">
                  <span className={item.stock_count <= 5 ? "font-semibold text-rose-600" : ""}>
                    {item.stock_count}
                  </span>
                </td>
                <td className="px-3 py-2"><StatusBadge value={item.status} /></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(item.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="Edit"
                      onClick={() => openEdit(item)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >✏️</button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(item)}
                      className="rounded p-1 text-rose-600 hover:bg-rose-50"
                    >🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(n) => { setPerPage(n); setPage(1); }}
      />

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add New Item" maxWidth="max-w-2xl">
        {createErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{createErr}</div>}
        <ItemForm
          form={createForm}
          setForm={setCreateForm}
          categories={categories}
          onSubmit={doCreate}
          onCancel={() => setCreateOpen(false)}
          submitLabel="Add Item"
          skuReadOnly={false}
        />
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editItem} onClose={() => setEditItem(null)} title="Edit Item" maxWidth="max-w-2xl">
        {editErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{editErr}</div>}
        <ItemForm
          form={editForm}
          setForm={setEditForm}
          categories={categories}
          onSubmit={doEdit}
          onCancel={() => setEditItem(null)}
          submitLabel="Save Changes"
          skuReadOnly={true}
        />
      </Modal>

      {/* Delete Confirm */}
      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete Item?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete item <span className="font-mono">{confirmDelete?.sku}</span> —{" "}
            <strong>{confirmDelete?.name}</strong>? This cannot be undone.
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
