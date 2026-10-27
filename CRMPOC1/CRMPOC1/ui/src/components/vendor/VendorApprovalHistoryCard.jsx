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

/** The vendor's own full history of extra-expense requests -- not just what's still pending (that's
 * the urgent banner above), but what they already approved or rejected too. */
export default function VendorApprovalHistoryCard() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    accountLedgerApi.listVendorExpenses({})
      .then(setRows)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load your approval history"))
      .finally(() => setLoading(false));
  }, []);

  if (!loading && rows.length === 0 && !err) return null;

  const pendingCount = rows.filter((r) => r.status === "Pending").length;
  const approvedSum = rows.filter((r) => r.status === "Approved").reduce((sum, r) => sum + r.amount, 0);
  const rejectedCount = rows.filter((r) => r.status === "Rejected").length;

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Your approval history</p>
      <p className="mt-0.5 text-xs text-slate-500">Every extra-expense request raised against your orders, including ones you already decided.</p>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}

      <div className="mt-3 grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-amber-700">Pending</div>
          <div className="text-lg font-bold text-amber-700">{pendingCount}</div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-emerald-700">Approved (lifetime)</div>
          <div className="text-lg font-bold text-emerald-700">{fmtMoney(approvedSum)}</div>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-rose-700">Rejected</div>
          <div className="text-lg font-bold text-rose-700">{rejectedCount}</div>
        </div>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Order</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} title={r.decision_note || ""}>
                <td className="px-3 py-2 font-mono text-xs">{r.order_no || `#${r.order_id}`}</td>
                <td className="px-3 py-2">{r.reason}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.amount)}</td>
                <td className="px-3 py-2"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_PILL[r.status]}`}>{r.status}</span></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
