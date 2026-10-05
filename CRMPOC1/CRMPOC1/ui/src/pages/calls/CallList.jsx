import { hasPermission } from "../../utils/permissions.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { callsApi } from "../../api/calls.js";
import { usersApi } from "../../api/complaints.js";
import CallStatusEdit from "./CallStatusEdit.jsx";

const CALL_TYPES = ["Inbound", "Outbound", "Callback"];
const STATUSES = ["Completed", "Busy", "No Answer", "Call Back", "Not Interested"];

function fmtDateTime(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

function fmtDuration(secs) {
  if (!secs) return "—";
  const mins = Math.floor(secs / 60);
  const secsRem = secs % 60;
  return `${mins}m ${secsRem}s`;
}

export default function CallList() {
  const { user: permUser } = useAuth();
  const canDeletePerm = hasPermission(permUser, "calls", "can_delete");
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, stats: {} });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    call_type: "",
    search: "",
    date_from: "",
    date_to: "",
  });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [editTarget, setEditTarget] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [transferTarget, setTransferTarget] = useState(null);
  const [transferData, setTransferData] = useState({ transferred_to: "", transfer_notes: "" });
  const [staff, setStaff] = useState([]);
  const [transferLoading, setTransferLoading] = useState(false);

  const params = useMemo(() => ({
    page, per_page: perPage,
    status: filters.status || undefined,
    call_type: filters.call_type || undefined,
    search: filters.search || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await callsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load calls");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  useEffect(() => {
    usersApi.list()
      .then(setStaff)
      .catch(() => setStaff([]));
  }, []);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await callsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  async function doTransfer() {
    if (!transferTarget || !transferData.transferred_to) return;
    setTransferLoading(true);
    try {
      await callsApi.transfer(transferTarget.id, {
        transferred_to: parseInt(transferData.transferred_to, 10),
        transfer_notes: transferData.transfer_notes || undefined,
      });
      setTransferTarget(null);
      setTransferData({ transferred_to: "", transfer_notes: "" });
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to transfer call");
    } finally {
      setTransferLoading(false);
    }
  }

  function fmtFollowupDate(s) {
    if (!s) return "—";
    try { return new Date(s).toLocaleDateString(); } catch { return s; }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Call Log</h1>
        <div className="flex gap-2">
          <button
            onClick={() => navigate("/calls/calendar")}
            className="inline-flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            📅 Calendar
          </button>
          <button
            onClick={() => navigate("/calls/pending-follow-ups")}
            className="inline-flex items-center gap-2 rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
          >
            📋 Follow-ups
          </button>
          <button
            onClick={() => navigate("/calls/new")}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            ➕ Log New Call
          </button>
        </div>
      </div>

      {data.stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <div className="rounded-lg bg-blue-500 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.total || 0}</div>
            <div className="text-sm opacity-90">Total Calls</div>
          </div>
          <div className="rounded-lg bg-green-500 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.completed || 0}</div>
            <div className="text-sm opacity-90">Completed</div>
          </div>
          <div className="rounded-lg bg-yellow-500 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.call_backs || 0}</div>
            <div className="text-sm opacity-90">Call Backs</div>
          </div>
          <div className="rounded-lg bg-red-500 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.busy || 0}</div>
            <div className="text-sm opacity-90">Busy</div>
          </div>
          <div className="rounded-lg bg-gray-500 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.no_answer || 0}</div>
            <div className="text-sm opacity-90">No Answer</div>
          </div>
          <div className="rounded-lg bg-blue-600 p-4 text-white shadow">
            <div className="text-3xl font-bold">{data.stats.transferred || 0}</div>
            <div className="text-sm opacity-90">Transferred</div>
          </div>
        </div>
      )}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <input
            type="text"
            placeholder="Search customer, phone, ref no…"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={filters.status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Status</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={filters.call_type}
            onChange={(e) => applyFilter({ call_type: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            {CALL_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => applyFilter({ date_from: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => applyFilter({ date_to: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <button
              onClick={() => load()}
              className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              🔍 Filter
            </button>
            <button
              onClick={() => { setFilters({ status: "", call_type: "", search: "", date_from: "", date_to: "" }); setPage(1); }}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50"
            >
              ↺ Reset
            </button>
          </div>
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Ref No</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Date & Time</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Customer</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Phone</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Type</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Assigned To</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Duration</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Follow-up</th>
              <th className="px-4 py-3 text-right font-semibold text-slate-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {loading && (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-500">No calls found.</td></tr>
            )}
            {!loading && data.items.map((call) => (
              <tr key={call.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3 font-mono text-xs font-medium text-slate-900">{call.ref_no}</td>
                <td className="px-4 py-3 text-xs text-slate-700">{fmtDateTime(call.call_datetime)}</td>
                <td className="px-4 py-3 text-sm text-slate-900">{call.customer_name || "—"}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{call.phone || "—"}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-800">
                    {call.call_type || "—"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                    call.status === "Completed" ? "bg-green-100 text-green-800" :
                    call.status === "Busy" ? "bg-red-100 text-red-800" :
                    call.status === "No Answer" ? "bg-gray-100 text-gray-800" :
                    call.status === "Call Back" ? "bg-yellow-100 text-yellow-800" :
                    "bg-purple-100 text-purple-800"
                  }`}>
                    {call.status || "—"}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">{call.assigned_to_name || "—"}</td>
                <td className="px-4 py-3 text-xs text-slate-700">{fmtDuration(call.duration_secs)}</td>
                <td className="px-4 py-3 text-xs">
                  {call.followup_date ? (
                    <div className="inline-flex flex-col gap-1">
                      <span className="font-medium text-slate-900">{fmtFollowupDate(call.followup_date)}</span>
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        call.follow_up_status === "Completed" ? "bg-green-100 text-green-800" :
                        call.follow_up_status === "Pending" ? "bg-yellow-100 text-yellow-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {call.follow_up_status || "—"}
                      </span>
                    </div>
                  ) : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View"
                      onClick={() => navigate(`/calls/${call.id}`)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    >👁</button>
                    <button
                      title="Transfer"
                      onClick={() => { setTransferTarget(call); setTransferData({ transferred_to: "", transfer_notes: "" }); }}
                      className="rounded px-2 py-1 text-blue-600 hover:bg-blue-100 hover:text-blue-900"
                    >↗️</button>
                    <button
                      title="Edit"
                      onClick={() => setEditTarget(call)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    >✏️</button>
{canDeletePerm && (
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(call)}
                      className="rounded px-2 py-1 text-rose-600 hover:bg-rose-100 hover:text-rose-900"
                    >🗑</button>
)}
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

      {editTarget && (
        <CallStatusEdit
          call={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => { setEditTarget(null); load(); }}
        />
      )}

      <Modal
        open={!!transferTarget}
        onClose={() => setTransferTarget(null)}
        title={`Transfer call — ${transferTarget?.ref_no}`}
        maxWidth="max-w-md"
      >
        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">Transfer To *</label>
            <select
              value={transferData.transferred_to}
              onChange={(e) => setTransferData((d) => ({ ...d, transferred_to: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">— Select staff member —</option>
              {staff.map((u) => (
                <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">Transfer Notes</label>
            <textarea
              rows={3}
              value={transferData.transfer_notes}
              onChange={(e) => setTransferData((d) => ({ ...d, transfer_notes: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Why is this call being transferred?"
            />
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button
              onClick={() => setTransferTarget(null)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={doTransfer}
              disabled={transferLoading || !transferData.transferred_to}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {transferLoading ? "Transferring…" : "Transfer Call"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete call?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will delete the call record <span className="font-mono">{confirmDelete?.ref_no}</span>.
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
