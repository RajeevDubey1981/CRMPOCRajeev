import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../api/sales.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { CountUp } from "../pages/sales/salesUi.jsx";

// The Sales block on the main dashboard. The numbers are asked from the Sales database each time the dashboard
// opens and kept for 60 seconds; the CRM stores none of them. If Sales is offline or slow the block shows a calm
// message and the rest of the dashboard works as usual.
let cache = { at: 0, userId: null, data: null };

export default function SalesDashboardBlock() {
  const { user } = useAuth();
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const allowed = permissions.some((p) => p.module === "sales" && p.can_view);
  const [state, setState] = useState(() => (cache.data && cache.userId === user?.id && Date.now() - cache.at < 60000 ? { status: "ok", data: cache.data } : { status: "loading" }));

  useEffect(() => {
    if (!allowed) return undefined;
    if (cache.data && cache.userId === user?.id && Date.now() - cache.at < 60000) return undefined;
    let live = true;
    salesApi.summaryQuick()
      .then((data) => { cache = { at: Date.now(), userId: user?.id, data }; if (live) setState({ status: "ok", data }); })
      .catch((e) => { if (live) setState({ status: e?.response?.status === 403 ? "hidden" : "down" }); });
    return () => { live = false; };
  }, [allowed, user?.id]);

  if (!allowed || state.status === "hidden") return null;
  if (state.status === "loading") return <div className="rounded bg-white p-4 text-sm text-slate-400 shadow-sm">Sales...</div>;
  if (state.status === "down") {
    return (
      <div className="rounded border border-amber-300 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-600">Sales</h3>
        <p className="mt-1 text-sm text-amber-700"><b>Sales is being updated.</b> The Sales numbers will be back in a few minutes. Everything else on this dashboard is working.</p>
      </div>
    );
  }
  const s = state.data;
  return (
    <div className="s-fade rounded bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-600">{s.title}</h3>
        <Link to="/sales" className="s-press rounded bg-indcool-blue px-3 py-1.5 text-sm font-medium text-white hover:bg-indcool-navy">Open Sales</Link>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {s.tiles.map((t, i) => (
          <div key={t.key} style={{ "--i": i }} className="s-rise s-lift rounded border border-slate-200 p-2">
            <div className={`text-2xl font-semibold tabular-nums ${["hot", "urgent", "overdue", "first_overdue", "unassigned"].includes(t.key) && t.value ? "text-rose-600" : t.key === "won" ? "text-emerald-700" : "text-slate-800"}`}><CountUp value={t.value} /></div>
            <div className="text-xs text-slate-600">{t.label}</div>
            {t.sub && <div className="text-[11px] text-slate-400">{t.sub}</div>}
          </div>
        ))}
      </div>
      {s.need.length > 0 && <div className="mt-3 rounded border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900"><b>Needs you</b>{s.need.map((n) => <div key={n}>• {n}</div>)}</div>}
    </div>
  );
}
