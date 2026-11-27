import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { webOrdersApi } from "../../api/webOrders.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { fmtIST } from "../../utils/time.js";

const REFRESH_MS = 20000;
const PAGE = 50;
const rupees = (n) => (n === null || n === undefined ? "-" : `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`);
const when = (v) => (v ? fmtIST(v, "String", "en-IN", { dateStyle: "medium", timeStyle: "short" }) : "-");

// Words are shown exactly as the website writes them; only the colour is chosen from the meaning.
export function tone(word) {
  const w = String(word || "").toLowerCase();
  if (/cancel|fail|refund|reject|return|declin|expire/.test(w)) return "bg-rose-100 text-rose-800";
  if (/deliver|receiv|complete|success|paid|captur/.test(w)) return "bg-emerald-100 text-emerald-800";
  if (/confirm|process|packed|ready/.test(w)) return "bg-sky-100 text-sky-800";
  if (/ship|dispatch|transit|out for/.test(w)) return "bg-indigo-100 text-indigo-800";
  if (/pre.?book/.test(w)) return "bg-violet-100 text-violet-800";
  if (/pend|creat|await|new/.test(w)) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export function Badge({ children }) {
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${tone(children)}`}>{children || "unknown"}</span>;
}

function LivePill({ summary, now }) {
  if (!summary) return null;
  if (!summary.sync_enabled) return <span className="rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700">Sync is switched off on the server</span>;
  const beat = summary.heartbeat_at ? new Date(summary.heartbeat_at).getTime() : 0;
  if (!beat) return <span className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-800">Waiting for the first sync from the website</span>;
  const mins = Math.max(0, Math.floor((now - beat) / 60000));
  const fresh = mins < 5;
  const last = summary.last_synced_at ? new Date(summary.last_synced_at).getTime() : 0;
  const lastMins = last ? Math.max(0, Math.floor((now - last) / 60000)) : null;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs ${fresh ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
      <span className={`h-2 w-2 rounded-full ${fresh ? "animate-pulse bg-emerald-500" : "bg-rose-500"}`} />
      {fresh ? "Live" : `Sync stopped ${mins} min ago`}
      {lastMins !== null ? ` · last order change ${lastMins < 1 ? "just now" : `${lastMins} min ago`}` : ""}
    </span>
  );
}

export default function WebOrders() {
  const { user } = useAuth();
  const canExport = (Array.isArray(user?.permissions) ? user.permissions : []).some((p) => p.module === "web_orders" && !p.sub_module && p.can_export) || (user?.role || "").toLowerCase() === "admin";
  const [summary, setSummary] = useState(null);
  const [data, setData] = useState({ total: 0, items: [] });
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [payment, setPayment] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [err, setErr] = useState("");
  const [now, setNow] = useState(Date.now());
  const timer = useRef(null);

  const params = useCallback(() => {
    const p = { limit: PAGE, offset };
    if (q.trim()) p.q = q.trim();
    if (status) p.status = status;
    if (payment) p.payment_status = payment;
    if (from) p.date_from = from;
    if (to) p.date_to = to;
    return p;
  }, [q, status, payment, from, to, offset]);

  const load = useCallback(async () => {
    try {
      const [s, d] = await Promise.all([webOrdersApi.summary(), webOrdersApi.list(params())]);
      setSummary(s);
      setData(d);
      setErr("");
      setNow(Date.now());
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not load the web orders");
    }
  }, [params]);

  useEffect(() => {
    load();
    clearInterval(timer.current);
    timer.current = setInterval(load, REFRESH_MS); // live: the list refreshes itself while the page is open
    return () => clearInterval(timer.current);
  }, [load]);

  async function download() {
    const blob = await webOrdersApi.exportCsv(params());
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "web-orders.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const chip = (label, active, onClick, count) => (
    <button key={label} type="button" onClick={onClick} className={`rounded-full px-3 py-1 text-xs capitalize ${active ? "bg-[#1e3a8a] text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>
      {label}{count !== undefined ? ` · ${count}` : ""}
    </button>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Web Orders</h1>
          <p className="text-sm text-slate-500">Orders placed on www.indcool.in, with every status change, kept in step with the website.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LivePill summary={summary} now={now} />
          {canExport && <button type="button" onClick={download} className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">Download CSV</button>}
        </div>
      </div>

      {err && <p className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</p>}

      {summary && (
        <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="w-24 text-xs uppercase tracking-wide text-slate-500">Order</span>
            {chip("All", status === "", () => { setStatus(""); setOffset(0); }, summary.total)}
            {Object.entries(summary.by_status).map(([k, n]) => chip(k, status === k, () => { setStatus(k); setOffset(0); }, n))}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="w-24 text-xs uppercase tracking-wide text-slate-500">Payment</span>
            {chip("All", payment === "", () => { setPayment(""); setOffset(0); })}
            {Object.entries(summary.by_payment_status).map(([k, n]) => chip(k, payment === k, () => { setPayment(k); setOffset(0); }, n))}
          </div>
          <p className="text-xs text-slate-500">{summary.today} {summary.today === 1 ? "order" : "orders"} placed today.</p>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <input value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} placeholder="Search order no., name, mobile, email or payment id" className="min-w-[260px] flex-1 rounded border border-slate-300 px-3 py-2 text-sm" />
        <label className="text-xs text-slate-500">From<input type="date" value={from} onChange={(e) => { setFrom(e.target.value); setOffset(0); }} className="ml-1 rounded border border-slate-300 px-2 py-1.5 text-sm" /></label>
        <label className="text-xs text-slate-500">To<input type="date" value={to} onChange={(e) => { setTo(e.target.value); setOffset(0); }} className="ml-1 rounded border border-slate-300 px-2 py-1.5 text-sm" /></label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">Order</th><th className="px-3 py-2">Placed</th><th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">Total</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Payment</th><th className="px-3 py-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-400">No orders match.</td></tr>}
            {data.items.map((o) => (
              <tr key={o.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2"><Link to={`/web-orders/${o.id}`} className="font-medium text-[#1e3a8a] hover:underline">{o.order_number || `#${o.site_order_id}`}</Link></td>
                <td className="whitespace-nowrap px-3 py-2 text-slate-600">{when(o.placed_at)}</td>
                <td className="px-3 py-2"><div className="text-slate-800">{o.customer_name || "-"}</div><div className="text-xs text-slate-500">{o.mobile}</div></td>
                <td className="whitespace-nowrap px-3 py-2">{rupees(o.total)}</td>
                <td className="px-3 py-2"><Badge>{o.status}</Badge></td>
                <td className="px-3 py-2"><Badge>{o.payment_status}</Badge> <span className="text-xs text-slate-500">{o.payment_method}</span></td>
                <td className="whitespace-nowrap px-3 py-2 text-xs text-slate-500">{when(o.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>{data.total === 0 ? "0 orders" : `${offset + 1} to ${Math.min(offset + PAGE, data.total)} of ${data.total}`}</span>
        <div className="flex gap-2">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40">Previous</button>
          <button type="button" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)} className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
}
