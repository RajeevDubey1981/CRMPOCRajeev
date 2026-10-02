import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import { couriersApi } from "../../api/couriers.js";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(); } catch { return s; }
}

export default function CourierList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [successMsg, setSuccessMsg] = useState(location.state?.success || "");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    search: search || undefined,
  }), [page, perPage, search]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await couriersApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load couriers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function applySearch(value) {
    setSearch(value);
    setPage(1);
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await couriersApi.remove(confirmDelete.id);
      setSuccessMsg(`Courier "${confirmDelete.courier_name}" deleted successfully.`);
      setConfirmDelete(null);
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to delete courier");
    }
  }

  function exportCsv() {
    const url = couriersApi.exportUrl({ search: search || undefined });
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => { throw new Error(b.detail || `Error ${r.status}`); });
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `couriers_${new Date().toISOString().slice(0, 10)}.csv`;
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
        <h1 className="text-2xl font-semibold text-slate-800">Courier Masters</h1>
        <div className="flex gap-2">
          <button
            onClick={exportCsv}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Export CSV
          </button>
          <Link
            to="/couriers/new"
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + New Courier
          </Link>
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            type="text"
            placeholder="Search courier name / contact / mobile"
            value={search}
            onChange={(e) => applySearch(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {successMsg && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{successMsg}</div>}
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Courier Name</th>
              <th className="px-3 py-2">Contact Name</th>
              <th className="px-3 py-2">Mobile</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Address</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">No couriers found.</td></tr>
            )}
            {!loading && data.items.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{c.id}</td>
                <td className="px-3 py-2 font-medium text-slate-800">{c.courier_name}</td>
                <td className="px-3 py-2">{c.contact_name || "—"}</td>
                <td className="px-3 py-2">{c.contact_mobile || "—"}</td>
                <td className="px-3 py-2">{c.email || "—"}</td>
                <td className="px-3 py-2 max-w-xs truncate">{c.address || "—"}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(c.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View"
                      onClick={() => navigate(`/couriers/${c.id}`)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >👁</button>
                    <button
                      title="Edit"
                      onClick={() => navigate(`/couriers/${c.id}?edit=1`)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >✏️</button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(c)}
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
        title="Delete courier?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete courier <strong>{confirmDelete?.courier_name}</strong>.
            This action can be reversed by an admin.
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
