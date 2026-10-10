import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../api/sales.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { CountUp } from "../pages/sales/salesUi.jsx";

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

// A small line of the last seven days, drawn in when the tile shows.
function Spark({ values, color }) {
  if (!values || values.length < 2) return null;
  const w = 64, h = 26;
  const mx = Math.max(...values), mn = Math.min(...values);
  const flat = mx === mn;
  const pts = values.map((v, i) => `${((i * w) / (values.length - 1)).toFixed(1)},${(flat ? h / 2 : h - 4 - ((v - mn) / (mx - mn)) * (h - 8)).toFixed(1)}`).join(" ");
  return (
    <svg className="absolute bottom-2 right-2" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline className="s-spark" points={pts} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" opacity={flat ? 0.45 : 1} />
    </svg>
  );
}

// The month target: a ring that fills to the share won so far.
function Target({ t }) {
  const set = t.target_lakh > 0;
  const share = set ? Math.min(1, t.won_lakh / t.target_lakh) : 0;
  const [v, setV] = useState(0);
  useEffect(() => { const id = setTimeout(() => setV(share), 200); return () => clearTimeout(id); }, [share]);
  const size = 84, r = (size - 10) / 2, c = 2 * Math.PI * r;
  const left = Math.max(0, t.target_lakh - t.won_lakh);
  return (
    <div className="s-rise mt-4 flex flex-wrap items-center gap-4 rounded-2xl bg-lime-50 p-4">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="9" />
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#65a30d" strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v)} className="s-ring" />
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center leading-tight"><div><div className="s-disp text-lg font-extrabold text-slate-800"><CountUp value={Math.round(share * 100)} />%</div><div className="text-[9px] text-slate-500">of target</div></div></div>
      </div>
      <div>
        {set ? (
          <>
            <div className="s-disp text-base font-extrabold text-slate-800">₹{t.won_lakh} lakh won of ₹{t.target_lakh} lakh</div>
            <div className="text-sm text-slate-500">{left > 0 ? `₹${left.toFixed(1)} lakh to go this month` : "Target reached this month"} · {t.days_left} day{t.days_left === 1 ? "" : "s"} left</div>
          </>
        ) : (
          <>
            <div className="s-disp text-base font-extrabold text-slate-800">₹{t.won_lakh} lakh won this month</div>
            <div className="text-sm text-slate-500">No month target set yet. A manager sets it in Sales, Team and profiles. {t.days_left} day{t.days_left === 1 ? "" : "s"} left in the month.</div>
          </>
        )}
      </div>
    </div>
  );
}

// What needs the person: one line at a time, sliding in.
function Needs({ items }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (items.length < 2) return undefined;
    const t = setInterval(() => setI((n) => (n + 1) % items.length), 3200);
    return () => clearInterval(t);
  }, [items.length]);
  if (!items.length) return null;
  return (
    <div className="mt-3 overflow-hidden rounded-xl bg-sky-100 px-4 py-2.5 text-sm font-semibold text-indcool-navy">
      <div key={i} className="s-slide truncate">{items[i]}</div>
    </div>
  );
}

function daysLeft() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate() - d.getDate() + 1;
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
  const wonTile = s.tiles.find((t) => t.key === "won");
  const wonFromTiles = Number(String(wonTile?.sub || "").replace(/[^0-9.]/g, "")) || 0;
  return (
    <div className="s-fade rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="s-disp text-base font-extrabold text-slate-800">{s.title}</h3>
        <Link to="/sales" className="s-press s-shine inline-flex items-center rounded-xl bg-indcool-navy px-4 py-2 text-sm font-semibold text-white shadow-lg hover:bg-indcool-blue">Open Sales</Link>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {s.tiles.map((t, i) => {
          const l = look(t.key);
          const alarm = ["hot", "urgent", "overdue", "first_overdue", "unassigned"].includes(t.key) && t.value > 0;
          return (
            <div key={t.key} style={{ "--i": i }} className="s-rise s-lift relative min-h-[110px] overflow-hidden rounded-2xl border border-slate-200 bg-white p-3.5">
              <span style={{ "--i": i, background: l.color }} className="s-grow absolute inset-x-0 top-0 h-1.5" />
              <div className={`s-disp mt-1 text-[32px] font-extrabold leading-tight tabular-nums ${alarm ? "text-rose-600" : t.key === "won" ? "text-emerald-600" : "text-slate-800"}`}><CountUp value={t.value} /></div>
              <div className="pr-14 text-sm text-slate-600">{t.label}</div>
              {t.sub && <div className="pr-14 text-[11px] text-slate-400">{t.sub}</div>}
              <Spark values={t.trend} color={l.color} />
            </div>
          );
        })}
      </div>
      <Target t={s.target || { won_lakh: wonFromTiles, target_lakh: 0, days_left: daysLeft() }} />
      <Needs items={s.need} />
    </div>
  );
}
