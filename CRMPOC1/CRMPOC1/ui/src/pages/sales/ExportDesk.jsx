import { useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import { localTime } from "./LeadDetail.jsx";
import { FirstCallChip, HeatChip, Notice, PageTitle, PriorityChip, SalesTabs, StatusChip, useAsync, valueText } from "./salesUi.jsx";

const COUNTRIES = [
  ["Nepal", "Asia/Kathmandu", "15 minutes ahead of India", "By road to Birgunj, or by sea to Kolkata"],
  ["Kenya", "Africa/Nairobi", "2 h 30 min behind India", "By sea to Mombasa"],
  ["Ghana", "Africa/Accra", "5 h 30 min behind India", "By sea to Tema"],
  ["Sri Lanka", "Asia/Colombo", "Same time as India", "By sea to Colombo"],
];

export default function ExportDesk() {
  const { data, error } = useAsync(() => salesApi.leads({ lead_type: "export", status: "", limit: 300 }), []);
  const [country, setCountry] = useState("");
  const cOf = (l) => l.country || (l.place || "").split(",").pop().trim();
  const items = (data?.items || []).filter((l) => !country || cOf(l) === country);
  return (
    <div>
      <PageTitle title="Export desk: Nepal, Kenya, Ghana and Sri Lanka" sub="Leads of the type Export. Prices are quoted in US dollars with no GST (exported under a LUT)." />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="mb-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {COUNTRIES.map(([c, tz, diff, route]) => {
          const t = localTime(tz);
          const open = (data?.items || []).filter((l) => !l.closed && cOf(l) === c);
          const ok = t.hour >= 9 && t.hour < 18;
          return (
            <button type="button" key={c} onClick={() => setCountry(country === c ? "" : c)} className={`rounded-lg border bg-white p-3 text-left shadow-sm ${country === c ? "border-indcool-blue ring-1 ring-indcool-blue" : "border-slate-200"}`}>
              <div className="font-semibold text-slate-800">{c}</div>
              <div className="text-2xl font-semibold tabular-nums">{open.length} <span className="text-xs font-normal text-slate-500">open leads</span></div>
              <div className="text-xs text-slate-500">US$ {open.reduce((a, l) => a + (l.value_usd || 0), 0).toLocaleString("en-US")} at stake</div>
              <div className="mt-1 text-xs text-slate-500">Time there: <b className="text-slate-800">{t.text}</b> · {diff}</div>
              <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{ok ? "Good time to call" : "Outside office hours"}</span>
              <div className="mt-1 text-[11px] text-slate-400">{route}</div>
            </button>
          );
        })}
      </div>
      <Notice>Marketplace and directory connections (Alibaba.com, TradeWheel, Kompass, import records) need your own accounts and keys, so they are not part of this first version. Export leads come in from the website, the call centre, a partner or by hand, and are typed Export from the words (Nepal, Kenya, Ghana, Sri Lanka, FOB, CIF) or by choosing the type.</Notice>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Buyer</th><th className="px-3 py-2">Country</th><th className="px-3 py-2">Wants</th><th className="px-3 py-2">Price basis</th><th className="px-3 py-2">Heat</th><th className="px-3 py-2">Priority</th><th className="px-3 py-2">Owner</th><th className="px-3 py-2">Status</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((l) => (
              <tr key={l.id}>
                <td className="px-3 py-2"><Link to={`/sales/leads/${l.id}`} className="font-semibold text-indcool-navy hover:underline">{l.name}</Link><div className="text-xs text-slate-500">{l.phone}</div></td>
                <td className="px-3 py-2">{cOf(l) || "—"}</td>
                <td className="px-3 py-2">{l.item}<div className="text-xs text-slate-500">{valueText(l)}</div></td>
                <td className="px-3 py-2">{l.price_basis || "—"}</td>
                <td className="px-3 py-2"><HeatChip lead={l} /></td>
                <td className="px-3 py-2"><PriorityChip lead={l} always /></td>
                <td className="px-3 py-2">{l.owner_name || "—"}</td>
                <td className="px-3 py-2"><StatusChip status={l.status} /><div><FirstCallChip lead={l} /></div></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">No export lead yet. Add a lead and choose the type Export.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
