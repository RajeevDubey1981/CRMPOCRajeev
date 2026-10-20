import { useEffect, useState } from "react";

import { partsApi, REQUEST_KINDS } from "../../api/parts.js";
import { RequestDetail } from "./PartsApprovals.jsx";

const KIND_LABEL = Object.fromEntries(REQUEST_KINDS.map((k) => [k.value, k.label]));

function stagePill(stage) {
  if (stage === "done") return <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Approved</span>;
  if (stage === "rejected") return <span className="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">Rejected</span>;
  if (stage === "sub") return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending Admin</span>;
  return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending Service Manager</span>;
}

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch { return s; }
}

// Every part/expense/unit request this engineer has raised — rejected ones were previously
// invisible to them entirely (only the admin-side Approvals tab showed the reason, and that
// tab is gated away from the engineer role). This gives them the same Resubmit path.
export default function MyPartRequests() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [detailId, setDetailId] = useState(null);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setRows(await partsApi.requests({}));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load your requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const rejectedCount = rows.filter((r) => r.stage === "rejected").length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">My Requests</h1>
        <p className="text-sm text-slate-500">Every spare part / expense / unit request you've raised, and where it stands.</p>
      </div>

      {rejectedCount > 0 && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {rejectedCount} request{rejectedCount > 1 ? "s" : ""} rejected — open one below to see why, and resubmit it.
        </div>
      )}

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Request</th>
              <th className="px-3 py-2">What</th>
              <th className="px-3 py-2">Raised</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">You haven't raised any requests yet.</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} onClick={() => setDetailId(r.id)} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2"><span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">{KIND_LABEL[r.kind] || r.kind}</span></td>
                <td className="px-3 py-2 font-medium text-brand-700">{r.request_no}</td>
                <td className="px-3 py-2 max-w-xs truncate">{r.part_name_cache || r.crm_item_name_cache || r.description}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(r.created_at)}</td>
                <td className="px-3 py-2">{stagePill(r.stage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailId && (
        <RequestDetail id={detailId} onClose={() => setDetailId(null)} onChanged={load} />
      )}
    </div>
  );
}
