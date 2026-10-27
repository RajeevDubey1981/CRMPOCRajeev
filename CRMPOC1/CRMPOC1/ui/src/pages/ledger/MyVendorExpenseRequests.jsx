import { useEffect, useState } from "react";

import { accountLedgerApi } from "../../api/accountLedger.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }); } catch { return d; }
}

const STATUS_PILL = {
  Pending: "bg-amber-100 text-amber-800 border border-amber-300",
  Approved: "bg-emerald-100 text-emerald-700 border border-emerald-300",
  Rejected: "bg-rose-100 text-rose-700 border border-rose-300",
};

/** Sales/Service's own view of what they raised for vendor approval -- only what they personally sent,
 * not the whole team's, with the vendor's note shown whenever something was rejected. */
export default function MyVendorExpenseRequests() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    accountLedgerApi.listVendorExpenses({ mine: true })
      .then(setRows)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load your requests"))
      .finally(() => setLoading(false));
  }, []);

  const pendingCount = rows.filter((r) => r.status === "Pending").length;
  const approvedRows = rows.filter((r) => r.status === "Approved");
  const approvedSum = approvedRows.reduce((sum, r) => sum + r.amount, 0);
  const rejectedCount = rows.filter((r) => r.status === "Rejected").length;
  const filtered = statusFilter ? rows.filter((r) => r.status === statusFilter) : rows;

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Expenses you've raised for vendor approval</p>
      <p className="mt-0.5 text-xs text-slate-500">Only what you personally sent — not the whole team's.</p>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-amber-700">Pending</div>
          <div className="text-xl font-bold text-amber-700">{pendingCount}</div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-emerald-700">Approved</div>
          <div className="text-xl font-bold text-emerald-700">{approvedRows.length}</div>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-rose-700">Rejected</div>
          <div className="text-xl font-bold text-rose-700">{rejectedCount}</div>
        </div>
        <div className="rounded-lg border border-slate-200 p-3">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">Approved total</div>
          <div className="text-xl font-bold">{fmtMoney(approvedSum)}</div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-xs">
          <option value="">All statuses</option>
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
        </select>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Order</th>
              <th className="px-3 py-2">Vendor</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Sent on</th>
              <th className="px-3 py-2">Vendor's note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">You haven't raised anything yet.</td></tr>
            ) : filtered.map((r) => (
              <tr key={r.id}>
                <td className="px-3 py-2 font-mono text-xs">{r.order_no || `#${r.order_id}`}</td>
                <td className="px-3 py-2">{r.vendor_name || "—"}</td>
                <td className="px-3 py-2">{r.reason}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.amount)}</td>
                <td className="px-3 py-2"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_PILL[r.status]}`}>{r.status}</span></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(r.created_at)}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{r.status === "Rejected" ? (r.decision_note || "—") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
