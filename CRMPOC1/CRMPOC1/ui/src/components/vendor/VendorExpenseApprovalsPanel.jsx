import { useEffect, useState } from "react";

import { accountLedgerApi } from "../../api/accountLedger.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

/** The vendor's own "approve this expense" inbox: an urgent banner for anything Sales/Service raised
 * against one of their orders, with a one-click Approve/Reject right here. Nothing debits until the
 * vendor decides. */
export default function VendorExpenseApprovalsPanel() {
  const [rows, setRows] = useState([]);
  const [busyId, setBusyId] = useState(null);
  const [err, setErr] = useState("");

  function load() {
    accountLedgerApi.listVendorExpenses({ status: "Pending" }).then(setRows).catch(() => {});
  }
  useEffect(load, []);

  async function decide(id, decision) {
    setBusyId(id);
    setErr("");
    try {
      await accountLedgerApi.decideVendorExpense(id, { decision });
      setRows((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to record your decision");
    } finally {
      setBusyId(null);
    }
  }

  if (rows.length === 0) return null;

  return (
    <div className="rounded-lg border-2 border-rose-400 bg-rose-50 p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="text-lg">🚨</span>
        <h3 className="text-sm font-bold uppercase tracking-wide text-rose-700">
          Urgent — {rows.length} expense approval{rows.length > 1 ? "s" : ""} waiting on you
        </h3>
      </div>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}
      <ul className="mt-3 space-y-2">
        {rows.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-white p-3 shadow-sm">
            <div>
              <p className="text-sm font-semibold text-slate-800">Order {r.order_no || `#${r.order_id}`} — {fmtMoney(r.amount)}</p>
              <p className="text-xs text-slate-600">{r.reason}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" disabled={busyId === r.id} onClick={() => decide(r.id, "Approved")}
                className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
                Approve
              </button>
              <button type="button" disabled={busyId === r.id} onClick={() => decide(r.id, "Rejected")}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-50">
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
