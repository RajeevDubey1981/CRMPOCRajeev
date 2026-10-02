import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import { itemsApi } from "../../api/items.js";
import AddItemCategoryModal from "../../components/items/AddItemCategoryModal.jsx";
import ItemCategorySelect from "../../components/items/ItemCategorySelect.jsx";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(); } catch { return s; }
}

function fmtMrp(v) {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

export default function ItemMasterList() {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({ search: "", category: "", is_active: "" });
  const [addCategoryOpen, setAddCategoryOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    search: filters.search || undefined,
    category: filters.category || undefined,
    is_active: filters.is_active === "" ? undefined : filters.is_active === "true",
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await itemsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load items");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await itemsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  function exportCsv() {
    const url = itemsApi.exportUrl({
      search: filters.search || undefined,
      category: filters.category || undefined,
      is_active: filters.is_active === "" ? undefined : filters.is_active === "true",
    });
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) return r.json().then((body) => { throw new Error(body.detail || `Server error ${r.status}`); });
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `item_masters_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(obj);
      })
      .catch((e) => alert(e.message || "Export failed"));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Item Masters</h1>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setAddCategoryOpen(true)}
            className="rounded-md border border-brand-300 bg-brand-50 px-3 py-2 text-sm font-medium text-brand-800 hover:bg-brand-100"
          >
            Add category
          </button>
          <button
            type="button"
            onClick={exportCsv}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Export CSV
          </button>
          <Link
            to="/items/new"
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + New Item
          </Link>
        </div>
      </div>

      <AddItemCategoryModal
        open={addCategoryOpen}
        onClose={() => setAddCategoryOpen(false)}
      />

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            type="text"
            placeholder="Search code / name / brand"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <ItemCategorySelect
            value={filters.category}
            onChange={(v) => applyFilter({ category: v })}
            placeholder="All categories"
          />
          <select
            value={filters.is_active}
            onChange={(e) => applyFilter({ is_active: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Item Code</th>
              <th className="px-3 py-2">Item Name</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Brand</th>
              <th className="px-3 py-2">Unit</th>
              <th className="px-3 py-2">HSN Code</th>
              <th className="px-3 py-2">MRP</th>
              <th className="px-3 py-2">Serials / unit</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={12} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={12} className="px-3 py-6 text-center text-slate-500">No items found.</td></tr>
            )}
            {!loading && data.items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{item.id}</td>
                <td className="px-3 py-2 font-mono text-xs">{item.item_code}</td>
                <td className="px-3 py-2 font-medium text-slate-800">{item.item_name}</td>
                <td className="px-3 py-2">{item.category || "—"}</td>
                <td className="px-3 py-2">{item.brand || "—"}</td>
                <td className="px-3 py-2">{item.unit || "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">{item.hsn_code || "—"}</td>
                <td className="px-3 py-2">{fmtMrp(item.mrp)}</td>
                <td className="px-3 py-2 text-center">{item.serial_count ?? 1}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                    item.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-100 text-slate-500"
                  }`}>
                    {item.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(item.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View"
                      onClick={() => navigate(`/items/${item.id}`)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >👁</button>
                    <button
                      title="Edit"
                      onClick={() => navigate(`/items/${item.id}`)}
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

      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete item?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete item <span className="font-mono">{confirmDelete?.item_code}</span>{" "}
            — <strong>{confirmDelete?.item_name}</strong>?
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
