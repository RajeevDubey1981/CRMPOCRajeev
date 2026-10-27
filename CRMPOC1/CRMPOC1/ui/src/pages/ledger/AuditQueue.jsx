import { useEffect, useState } from "react";

import { accountLedgerApi } from "../../api/accountLedger.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDateTime(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "numeric", minute: "2-digit" }); } catch { return d; }
}

const SOURCE_LABEL = {
  manual: "Manual entry", bank_statement: "Bank statement", return: "Return/cancellation",
};

/** Audit's inbox: every debit Accounts/Accounts Manager generated, waiting to post. Nothing here has
 * touched a balance yet -- Approve posts it for real, Reject leaves it unposted. A multi-select lets
 * Audit decide a whole batch (e.g. a day's bank statement run) in one action. */
export default function AuditQueue() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const [rejectNote, setRejectNote] = useState("");
  const [showRejectBox, setShowRejectBox] = useState(false);

  function load() {
    setLoading(true);
    accountLedgerApi.auditPending()
      .then((r) => { setRows(r); setSelected(new Set()); })
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load the audit queue"))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === rows.length ? new Set() : new Set(rows.map((r) => r.id))));
  }

  const selectedTotal = rows.filter((r) => selected.has(r.id)).reduce((sum, r) => sum + r.amount, 0);

  async function decide(decision) {
    if (selected.size === 0) return;
    if (decision === "Rejected" && !rejectNote.trim()) { setShowRejectBox(true); return; }
    setBusy(true);
    setErr("");
    try {
      await accountLedgerApi.auditDecide({ ids: [...selected], decision, note: rejectNote.trim() || null });
      setRejectNote("");
      setShowRejectBox(false);
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to record the decision");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Audit Queue</h1>
        <p className="text-sm text-slate-500">Every payment Accounts or Accounts Manager generated, waiting on your approval before it posts. An Admin bypass skips this queue entirely and is flagged on the ledger entry itself.</p>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-brand-300 bg-brand-50 p-3">
          <span className="text-sm font-semibold">{selected.size} selected — {fmtMoney(selectedTotal)}</span>
          <button type="button" disabled={busy} onClick={() => decide("Approved")} className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
            Approve selected
          </button>
          <button type="button" disabled={busy} onClick={() => setShowRejectBox(true)} className="rounded-md border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50">
            Reject selected
          </button>
          {showRejectBox && (
            <div className="flex items-center gap-2">
              <input
                value={rejectNote} onChange={(e) => setRejectNote(e.target.value)}
                placeholder="Reason for rejecting (required)"
                className="rounded-md border border-slate-300 px-2 py-1 text-xs"
              />
              <button type="button" disabled={busy || !rejectNote.trim()} onClick={() => decide("Rejected")} className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50">
                Confirm reject
              </button>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2"><input type="checkbox" checked={rows.length > 0 && selected.size === rows.length} onChange={toggleAll} className="h-4 w-4" /></th>
              <th className="px-3 py-2">Party</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Raised by</th>
              <th className="px-3 py-2">Raised on</th>
              <th className="px-3 py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Nothing waiting on you right now.</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} className={selected.has(r.id) ? "bg-brand-50/50" : undefined}>
                <td className="px-3 py-2"><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} className="h-4 w-4" /></td>
                <td className="px-3 py-2 font-medium">{r.party_name || "—"} <span className="text-xs text-slate-400">({r.party_type})</span></td>
                <td className="px-3 py-2">{r.description}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{SOURCE_LABEL[r.source_type] || r.source_type}</td>
                <td className="px-3 py-2 text-xs">{r.raised_by_name || "—"}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDateTime(r.created_at)}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
