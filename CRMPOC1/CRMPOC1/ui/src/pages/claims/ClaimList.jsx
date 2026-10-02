import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import { claimsApi } from "../../api/claims.js";

const STATUSES = ["Processing", "Completed", "Rejected"];

const STATUS_COLORS = {
  Processing: "bg-blue-100 text-blue-800",
  Completed: "bg-green-100 text-green-800",
  Rejected: "bg-red-100 text-red-800",
};

function StatusBadge({ value }) {
  const cls = STATUS_COLORS[value] || "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {value}
    </span>
  );
}

function fmtDateTime(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

export default function ClaimList() {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({ status: "", search: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  // Status update modal
  const [statusTarget, setStatusTarget] = useState(null);
  const [statusForm, setStatusForm] = useState({ status: "Processing", admin_remark: "" });
  const [statusSaving, setStatusSaving] = useState(false);

  // Delete confirm modal
  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: filters.status || undefined,
    search: filters.search || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await claimsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  function openStatusModal(claim) {
    setStatusTarget(claim);
    setStatusForm({ status: claim.status, admin_remark: "" });
  }

  async function submitStatus() {
    if (!statusTarget) return;
    setStatusSaving(true);
    try {
      await claimsApi.updateStatus(statusTarget.id, {
        status: statusForm.status,
        admin_remark: statusForm.admin_remark || null,
      });
      setStatusTarget(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to update status");
    } finally {
      setStatusSaving(false);
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await claimsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  function exportCsv() {
    const url = claimsApi.exportUrl({
      status: filters.status || undefined,
      search: filters.search || undefined,
    });
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `claims_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(obj);
      });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Claims</h1>
        <div className="flex gap-2">
          <button
            onClick={exportCsv}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Export CSV
          </button>
          <Link
            to="/claims/new"
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + New Claim
          </Link>
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            type="text"
            placeholder="Search customer name / mobile / claim ID / order / serial"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={filters.status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {err && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Claim ID</th>
              <th className="px-3 py-2">Order No</th>
              <th className="px-3 py-2">Serial No</th>
              <th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">Contact</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Submitted At</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading…</td>
              </tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-slate-500">No claims found.</td>
              </tr>
            )}
            {!loading && data.items.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs text-slate-800">{c.claim_id}</td>
                <td className="px-3 py-2">{c.order_no || <span className="text-slate-400">—</span>}</td>
                <td className="px-3 py-2">{c.serial_number || <span className="text-slate-400">—</span>}</td>
                <td className="px-3 py-2">{c.customer_name || <span className="text-slate-400">—</span>}</td>
                <td className="px-3 py-2">{c.customer_contact || <span className="text-slate-400">—</span>}</td>
                <td className="px-3 py-2"><StatusBadge value={c.status} /></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDateTime(c.submitted_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View"
                      onClick={() => navigate(`/claims/${c.id}`)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >
                      👁
                    </button>
                    <button
                      title="Update Status"
                      onClick={() => openStatusModal(c)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >
                      ✏️
                    </button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(c)}
                      className="rounded p-1 text-rose-600 hover:bg-rose-50"
                    >
                      🗑
                    </button>
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

      {/* Status update modal */}
      <Modal
        open={!!statusTarget}
        onClose={() => setStatusTarget(null)}
        title="Update Claim Status"
      >
        <div className="space-y-4">
          <div className="text-sm text-slate-600">
            Claim <span className="font-mono">{statusTarget?.claim_id}</span>
            {statusTarget?.customer_name && (
              <> — {statusTarget.customer_name}</>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
            <select
              value={statusForm.status}
              onChange={(e) => setStatusForm((f) => ({ ...f, status: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Admin Remark</label>
            <textarea
              value={statusForm.admin_remark}
              onChange={(e) => setStatusForm((f) => ({ ...f, admin_remark: e.target.value }))}
              rows={3}
              placeholder="Optional remark"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setStatusTarget(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={submitStatus}
              disabled={statusSaving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {statusSaving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete confirm modal */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete claim?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will permanently delete claim{" "}
            <span className="font-mono">{confirmDelete?.claim_id}</span>. This action cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm font-medium text-white hover:bg-rose-700"
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
