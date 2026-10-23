import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { servicesApi } from "../../api/services.js";

const STATUS_PILL = {
  "Pending Service Team Review": "bg-teal-100 text-teal-800",
  "Pending Service Approval": "bg-amber-100 text-amber-800",
  "Approved for Service": "bg-emerald-100 text-emerald-700",
  "Rejected": "bg-rose-100 text-rose-700",
};

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch { return s; }
}

const FILTERS = ["All", "Pending Service Team Review", "Pending Service Approval", "Approved for Service", "Rejected"];

const CARD_STYLE = {
  "Pending Service Team Review": { bar: "border-t-teal-500", chip: "bg-teal-50 text-teal-700" },
  "Pending Service Approval": { bar: "border-t-amber-500", chip: "bg-amber-50 text-amber-700" },
  "Approved for Service": { bar: "border-t-emerald-500", chip: "bg-emerald-50 text-emerald-700" },
  "Rejected": { bar: "border-t-rose-500", chip: "bg-rose-50 text-rose-700" },
};

export default function ServiceReviewsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setRows(await servicesApi.reviewUnits());
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => (
    statusFilter === "All" ? rows : rows.filter((r) => r.unit_status === statusFilter)
  ), [rows, statusFilter]);

  const counts = useMemo(() => {
    const c = {};
    for (const r of rows) c[r.unit_status] = (c[r.unit_status] || 0) + 1;
    return c;
  }, [rows]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Service Reviews</h1>
        <p className="text-sm text-slate-500">Every unit you've forwarded, approved, or rejected across all service requests — where it is now, in one place.</p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {FILTERS.filter((f) => f !== "All").map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setStatusFilter(statusFilter === f ? "All" : f)}
            className={`rounded-lg border-t-[3px] bg-white p-2.5 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${CARD_STYLE[f].bar} ${statusFilter === f ? "ring-2 ring-offset-1 ring-indcool-navy/30" : ""}`}
          >
            <div className="text-xl font-extrabold tabular-nums text-slate-800">{counts[f] || 0}</div>
            <div className={`mt-0.5 inline-block rounded-full px-1.5 py-0.5 text-[11px] font-semibold ${CARD_STYLE[f].chip}`}>{f}</div>
          </button>
        ))}
      </div>

      {statusFilter !== "All" && (
        <button type="button" onClick={() => setStatusFilter("All")} className="text-xs font-medium text-brand-700 hover:underline">
          ← Show all statuses
        </button>
      )}

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Request</th>
              <th className="px-3 py-2">Serial</th>
              <th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">Recommended action</th>
              <th className="px-3 py-2">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Nothing here.</td></tr>
            ) : filtered.map((r) => (
              <tr key={r.unit_id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/services/${r.service_id}`} className="font-medium text-brand-700 hover:underline">{r.request_no}</Link>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{r.serial_no || "—"}</td>
                <td className="px-3 py-2">{r.customer_name || "—"}</td>
                <td className="px-3 py-2">
                  <div className="max-w-xs truncate">{r.recommended_action || r.problem_found || "—"}</div>
                  {r.unit_status === "Rejected" && r.decision_remarks && (
                    <div className="mt-0.5 text-xs text-rose-600">Rejected: {r.decision_remarks}</div>
                  )}
                </td>
                <td className="px-3 py-2">
                  {r.requested_total ? `₹${Number(r.requested_total).toLocaleString("en-IN")}` : "—"}
                  {r.requires_admin_approval && <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800">Admin</span>}
                </td>
                <td className="px-3 py-2">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_PILL[r.unit_status] || "bg-slate-100 text-slate-600"}`}>
                    {r.unit_status}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(r.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
