import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../api/sales.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { CountUp, Icon, greeting } from "../pages/sales/salesUi.jsx";

// The Sales block on the main dashboard. The numbers are asked from the Sales database each time the dashboard
// opens and kept for 60 seconds; the CRM stores none of them. If Sales is offline or slow the block shows a calm
// message and the rest of the dashboard works as usual.
let cache = { at: 0, userId: null, data: null };

// Each tile gets its own icon and colour so the row reads at a glance.
function look(key) {
  if (/overdue|late/.test(key)) return { icon: "alert", color: "#e11d48", soft: "#ffe4e6" };
  if (/hot|urgent/.test(key)) return { icon: "flame", color: "#ea580c", soft: "#ffedd5" };
  if (/won/.test(key)) return { icon: "trophy", color: "#059669", soft: "#d1fae5" };
  if (/quot|quote/.test(key)) return { icon: "file", color: "#0891b2", soft: "#cffafe" };
  if (/due|today|follow/.test(key)) return { icon: "bell", color: "#d97706", soft: "#fef3c7" };
  if (/unassigned|new/.test(key)) return { icon: "users", color: "#7c3aed", soft: "#ede9fe" };
  return { icon: "calendar", color: "#2f5bb5", soft: "#dbeafe" };
}

function Needs({ items }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (items.length < 2) return undefined;
    const t = setInterval(() => setI((n) => (n + 1) % items.length), 3500);
    return () => clearInterval(t);
  }, [items.length]);
  if (!items.length) return null;
  return (
    <div className="mt-3 flex items-center gap-3 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
      <span className="s-now grid h-7 w-7 shrink-0 place-items-center rounded-full bg-white text-indcool-blue"><Icon name="bell" size={15} /></span>
      <div className="min-w-0 flex-1"><div className="text-[11px] font-bold uppercase tracking-wide text-sky-700">Needs you · {i + 1} of {items.length}</div><div key={i} className="s-slide truncate font-medium">{items[i]}</div></div>
    </div>
  );
}

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
  if (state.status === "loading") return <div className="rounded-xl bg-white p-4 text-sm text-slate-400 shadow-sm">Sales...</div>;
  if (state.status === "down") {
    return (
      <div className="rounded-xl border border-amber-300 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-600">Sales</h3>
        <p className="mt-1 text-sm text-amber-700"><b>Sales is being updated.</b> The Sales numbers will be back in a few minutes. Everything else on this dashboard is working.</p>
      </div>
    );
  }
  const s = state.data;
  const first = String(user?.name || "").split(" ")[0];
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
  return (
    <div className="s-fade overflow-hidden rounded-xl bg-white shadow-sm">
      <div className="s-hero flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-white/70">{s.title}</div>
          <div className="mt-0.5 text-xl font-semibold">{greeting()}{first ? `, ${first}` : ""}</div>
          <div className="text-sm text-white/80">{today}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/sales/calendar" className="s-press inline-flex items-center rounded-md border border-white/40 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10"><Icon name="calendar" size={15} className="mr-1.5" />Calendar</Link>
          <Link to="/sales" className="s-press s-shine inline-flex items-center rounded-md bg-white px-3.5 py-1.5 text-sm font-semibold text-indcool-navy hover:bg-slate-100">Open Sales<Icon name="right" size={15} className="ml-1" /></Link>
        </div>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          {s.tiles.map((t, i) => {
            const l = look(t.key);
            const alarm = ["hot", "urgent", "overdue", "first_overdue", "unassigned"].includes(t.key) && t.value > 0;
            return (
              <div key={t.key} style={{ "--i": i }} className="s-rise s-lift relative overflow-hidden rounded-lg border border-slate-200 bg-white p-3">
                <span style={{ "--i": i, background: l.color }} className="s-grow absolute inset-x-0 top-0 h-1" />
                <div className="flex items-start justify-between gap-2">
                  <div className={`text-3xl font-semibold tabular-nums ${alarm ? "text-rose-600" : "text-slate-800"}`}><CountUp value={t.value} /></div>
                  <span style={{ background: l.soft, color: l.color }} className="grid h-8 w-8 shrink-0 place-items-center rounded-full"><Icon name={l.icon} size={16} /></span>
                </div>
                <div className="mt-1 text-xs font-medium text-slate-600">{t.label}</div>
                {t.sub && <div className="text-[11px] text-slate-400">{t.sub}</div>}
              </div>
            );
          })}
        </div>
        <Needs items={s.need} />
      </div>
    </div>
  );
}
