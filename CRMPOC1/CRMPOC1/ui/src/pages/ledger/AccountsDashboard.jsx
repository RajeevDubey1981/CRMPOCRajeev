import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { accountLedgerApi } from "../../api/accountLedger.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

function monthLabel(ym) {
  try {
    const [y, m] = ym.split("-");
    return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-IN", { month: "short" });
  } catch { return ym; }
}

export default function AccountsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    accountLedgerApi.dashboard()
      .then(setData)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4 text-sm text-slate-500">Loading…</div>;
  if (err) return <div className="p-4 text-sm text-rose-700">{err}</div>;
  if (!data) return null;

  const maxBar = Math.max(1, ...data.month_wise.flatMap((m) => [m.due, m.paid]));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Accounts Dashboard</h1>
        <p className="text-sm text-slate-500">What's owed, what's been paid, and who's overdue — across every vendor and engineer.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Total due (all parties)</div>
          <div className="mt-1 text-xl font-bold text-rose-700">{fmtMoney(data.total_due)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Paid this month</div>
          <div className="mt-1 text-xl font-bold text-emerald-700">{fmtMoney(data.paid_this_month)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Overdue amount</div>
          <div className="mt-1 text-xl font-bold text-rose-700">{fmtMoney(data.overdue_amount)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Overdue parties</div>
          <div className="mt-1 text-xl font-bold">{data.overdue_count}</div>
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Due vs Paid — month wise</p>
        <div className="mt-3 flex items-end gap-4" style={{ height: 140 }}>
          {data.month_wise.map((m) => (
            <div key={m.month} className="flex flex-1 flex-col items-center justify-end gap-1" style={{ height: "100%" }}>
              <div className="flex items-end gap-1" style={{ height: 100 }}>
                <div className="w-3 rounded-t bg-rose-500/80" style={{ height: `${Math.max(2, (m.due / maxBar) * 100)}px` }} title={`Due: ${fmtMoney(m.due)}`} />
                <div className="w-3 rounded-t bg-emerald-600/80" style={{ height: `${Math.max(2, (m.paid / maxBar) * 100)}px` }} title={`Paid: ${fmtMoney(m.paid)}`} />
              </div>
              <div className="text-[10px] text-slate-500">{monthLabel(m.month)}</div>
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-4 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-rose-500" /> Due</span>
          <span className="inline-flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-emerald-600" /> Paid</span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <div className="px-4 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Overdue — sorted worst first</p>
        </div>
        <table className="mt-2 min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Party</th>
              <th className="px-3 py-2">Cycle</th>
              <th className="px-3 py-2">Oldest unpaid since</th>
              <th className="px-3 py-2">Overdue by</th>
              <th className="px-3 py-2 text-right">Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.overdue.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">Nothing overdue.</td></tr>
            ) : data.overdue.map((r) => (
              <tr key={`${r.party_type}-${r.party_id}`} className="cursor-pointer hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/ledger/${r.party_type}/${r.party_id}`} className="font-medium text-brand-700 hover:underline">{r.name}</Link>
                  <span className="ml-1 text-xs text-slate-500">({r.party_type})</span>
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{r.cycle_days} days</td>
                <td className="px-3 py-2 text-xs">{fmtDate(r.oldest_unpaid_since)}</td>
                <td className="px-3 py-2">
                  <span className="inline-flex rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-700">{r.overdue_days}d</span>
                </td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
