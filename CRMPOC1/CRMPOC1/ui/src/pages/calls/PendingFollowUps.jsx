import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { callsApi } from "../../api/calls.js";

function fmtDateTime(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

function fmtFollowupDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(); } catch { return s; }
}

function isOverdue(s) {
  if (!s) return false;
  try { return new Date(s) < new Date(); } catch { return false; }
}

export default function PendingFollowUps() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const complaintId = searchParams.get("complaint_id");
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const params = useMemo(() => ({
    page, per_page: perPage,
    ...(complaintId ? { complaint_id: parseInt(complaintId, 10) } : {}),
  }), [page, perPage, complaintId]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await callsApi.pendingFollowups(params));
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(typeof detail === "string" ? detail : "Failed to load follow-ups");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  async function markComplete(callId) {
    try {
      await callsApi.completeFollowup(callId);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to mark complete");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Pending Follow-ups</h1>
        <button
          onClick={() => complaintId ? navigate(`/complaints/${complaintId}`) : navigate("/complaints")}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          ← Back
        </button>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Ref No</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Customer</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Phone</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Assigned To</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Follow-up Date</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Created</th>
              <th className="px-4 py-3 text-right font-semibold text-slate-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {loading && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">No pending follow-ups.</td></tr>
            )}
            {!loading && data.items.map((call) => {
              const isOd = isOverdue(call.followup_date);
              return (
                <tr key={call.id} className={`border-b border-slate-100 hover:bg-slate-50 ${isOd ? "bg-red-50" : ""}`}>
                  <td className="px-4 py-3 font-mono text-xs font-medium text-slate-900">{call.ref_no}</td>
                  <td className="px-4 py-3 text-sm text-slate-900">{call.customer_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{call.phone || "—"}</td>
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
                  <td className="px-4 py-3 text-xs">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-slate-900">{fmtFollowupDate(call.followup_date)}</span>
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        isOd ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {isOd ? "Overdue" : "Pending"}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-700">{fmtDateTime(call.call_datetime)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        title="View"
                        onClick={() => navigate(`/calls/${call.id}`)}
                        className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                      >
                        👁
                      </button>
                      <button
                        title="Mark Complete"
                        onClick={() => markComplete(call.id)}
                        className="rounded px-2 py-1 text-green-600 hover:bg-green-100 hover:text-green-900"
                      >
                        ✓
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
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
    </div>
  );
}
