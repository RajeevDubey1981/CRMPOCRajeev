import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, SalesTabs, TYPE_COLOR, useAsync } from "./salesUi.jsx";

export function SummaryTiles({ s }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
      {s.tiles.map((t) => (
        <div key={t.key} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          <div className={`text-2xl font-semibold tabular-nums ${["hot", "urgent", "overdue", "first_overdue", "unassigned"].includes(t.key) && t.value ? "text-rose-600" : t.key === "won" ? "text-emerald-700" : "text-slate-800"}`}>{t.value}</div>
          <div className="text-xs text-slate-600">{t.label}</div>
          {t.sub && <div className="text-[11px] text-slate-400">{t.sub}</div>}
        </div>
      ))}
    </div>
  );
}

function Bars({ rows, color }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="space-y-1.5">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-2 text-xs">
          <span className="w-32 shrink-0 truncate text-slate-700" title={r.label}>{r.label}</span>
          <span className="h-3.5 flex-1 rounded bg-slate-100"><span className="block h-full rounded" style={{ width: `${(r.value * 100) / max}%`, background: r.color || color }} /></span>
          <span className="w-24 shrink-0 text-right font-semibold tabular-nums">{r.text ?? r.value}</span>
        </div>
      ))}
    </div>
  );
}

function Card({ title, sub, children }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {sub && <p className="mb-2 text-xs text-slate-500">{sub}</p>}
      {children}
    </section>
  );
}

export default function SalesDashboard() {
  const { data: s, loading, error } = useAsync(() => salesApi.summary(), []);
  return (
    <div>
      <PageTitle title="Sales dashboard" sub={s ? s.title : ""} />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      {loading && !s && <p className="text-sm text-slate-500">Loading...</p>}
      {s && (
        <>
          <SummaryTiles s={s} />
          {s.need.length > 0 && <div className="mt-3"><Notice><b>Needs you</b>{s.need.map((n) => <div key={n}>• {n}</div>)}</Notice></div>}
          {s.by_type && (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <Card title="Leads by type" sub="Leads and how many were won">
                <Bars rows={s.by_type.map((r) => ({ label: r.label, value: r.leads, text: `${r.leads} · ${r.won} won`, color: TYPE_COLOR[r.type] }))} color="#3987e5" />
              </Card>
              <Card title="Where leads come from" sub="Leads and how many were won">
                <Bars rows={s.by_source.map((r) => ({ label: r.source, value: r.leads, text: `${r.leads} · ${r.won} won` }))} color="#1c5cab" />
              </Card>
              <Card title="Hot, warm and cold" sub="Open leads">
                <Bars rows={[["Hot", "hot", "#b91c1c"], ["Warm", "warm", "#b45309"], ["Cold", "cold", "#2563eb"]].map(([l, k, c]) => ({ label: l, value: s.by_heat[k], color: c }))} color="#64748b" />
              </Card>
              <Card title="Team leaderboard" sub="Won value, and what each person did">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="text-left text-slate-500"><tr><th>Member</th><th className="text-right">Given</th><th className="text-right">Called</th><th className="text-right">Won</th><th className="text-right">Won ₹ L</th><th className="text-right">Overdue</th></tr></thead>
                    <tbody>
                      {s.leaderboard.map((r) => (
                        <tr key={r.user_id} className="border-t border-slate-100"><td className="py-1">{r.name}</td><td className="text-right tabular-nums">{r.given}</td><td className="text-right tabular-nums">{r.contacted}</td><td className="text-right tabular-nums">{r.won}</td><td className="text-right font-semibold tabular-nums">{r.won_lakh.toFixed(1)}</td><td className={`text-right tabular-nums ${r.overdue >= 3 ? "font-bold text-rose-600" : ""}`}>{r.overdue}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
          <p className="mt-3 text-xs text-slate-500">You see only what your ticks allow. <Link className="text-indcool-blue hover:underline" to="/sales/leads">Open the leads</Link></p>
        </>
      )}
    </div>
  );
}
