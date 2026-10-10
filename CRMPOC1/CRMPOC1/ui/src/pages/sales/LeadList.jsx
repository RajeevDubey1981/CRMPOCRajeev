import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import { AddLeadModal, GiveModal } from "./LeadModals.jsx";
import UploadModal from "./UploadModal.jsx";
import {
  FirstCallChip, HeatChip, Notice, PageTitle, PriorityChip, SalesTabs, StatusChip, TypeChip, btn, errText, fieldClass, fmtDate, useAsync, useSales, valueText,
} from "./salesUi.jsx";

const KPIS = [
  ["urgent", "Urgent and high priority", true], ["hot", "Hot: ready to buy", true], ["unassigned", "New, not given to anyone", true],
  ["due_today", "Follow-ups today"], ["overdue", "Overdue follow-ups", true], ["first_overdue", "First calls late", true], ["quo", "Quotes out"], ["rev", "Disposals to approve"],
];

export default function LeadList() {
  const { has, status } = useSales();
  const [params, setParams] = useSearchParams();
  const f = { q: params.get("q") || "", status: params.get("status") || "open", type: params.get("type") || "", heat: params.get("heat") || "", priority: params.get("priority") || "", owner: params.get("owner") || "", kpi: params.get("kpi") || "", sort: params.get("sort") || "pri" };
  const setF = (patch) => {
    const next = { ...f, ...patch };
    const p = {};
    Object.entries(next).forEach(([k, v]) => { if (v && !(k === "status" && v === "open") && !(k === "sort" && v === "pri")) p[k] = v; });
    setParams(p, { replace: true });
  };
  const [search, setSearch] = useState(f.q);
  useEffect(() => { const t = setTimeout(() => { if (search !== f.q) setF({ q: search }); }, 300); return () => clearTimeout(t); }, [search]); // eslint-disable-line react-hooks/exhaustive-deps
  const { data, loading, error, reload } = useAsync(() => salesApi.leads({ q: f.q, status: f.status === "all" ? "" : f.status, lead_type: f.type, heat: f.heat, priority: f.priority, owner: f.owner, kpi: f.kpi, sort: f.sort, limit: 300 }), [f.q, f.status, f.type, f.heat, f.priority, f.owner, f.kpi, f.sort]);
  const team = useAsync(() => (has("give") ? salesApi.team() : Promise.resolve([])), [has("give")]);
  const [adding, setAdding] = useState(false);
  const [giving, setGiving] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const people = (team.data || []).filter((p) => p.is_active && (p.role || "").trim().toLowerCase() === "sales");

  async function run(fn, done) {
    setBusy(true);
    setMsg("");
    try { const r = await fn(); setMsg(done(r)); reload(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  const counts = data?.counts || {};

  return (
    <div>
      <PageTitle title={has("see_all") ? "All leads" : "My leads"} sub="Every Sales and Partner enquiry in the CRM becomes a lead here" right={
        <div className="flex flex-wrap gap-2">
          {has("autogive") && <button type="button" className={btn.plain} disabled={busy} onClick={() => run(() => salesApi.autoGive(), (r) => (r.given ? `${r.given} new lead(s) given by type and place` : "No new lead is waiting"))}>Auto-give new leads</button>}
          {has("give") && <button type="button" className={btn.plain} disabled={busy} onClick={() => run(() => salesApi.sync({}), (r) => (r.started ? "Started. New enquiries from now on become leads." : `${r.complaints + r.partners} new lead(s) from the CRM`))}>Bring in enquiries now</button>}
          {has("upload") && <button type="button" className={btn.plain} disabled={busy} onClick={() => run(() => salesApi.sync({ backfill_days: 30 }), (r) => `${r.complaints + r.partners} lead(s) from the last 30 days`)}>Bring in the last 30 days</button>}
          {has("upload") && <button type="button" className={btn.plain} onClick={() => setUploading(true)}>Upload Excel or CSV</button>}
          {has("add_lead") && <button type="button" className={btn.go} onClick={() => setAdding(true)}>+ Add lead</button>}
        </div>
      } />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
        {KPIS.filter(([k]) => has("see_all") || !["unassigned", "rev"].includes(k)).map(([k, label, red]) => (
          <button key={k} type="button" onClick={() => setF({ kpi: f.kpi === k ? "" : k })} className={`rounded-lg border p-2 text-left shadow-sm ${f.kpi === k ? "border-indcool-blue bg-sky-50 ring-1 ring-indcool-blue" : "border-slate-200 bg-white"}`}>
            <div className={`text-2xl font-semibold tabular-nums ${red && counts[k] ? "text-rose-600" : "text-slate-800"}`}>{counts[k] ?? 0}</div>
            <div className="text-[11px] leading-tight text-slate-500">{label}</div>
          </button>
        ))}
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-2">
        <input className={`${fieldClass} !w-64`} type="search" placeholder="Search name, phone, item, place or number" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select className={`${fieldClass} !w-auto`} value={f.status} onChange={(e) => setF({ status: e.target.value })}><option value="open">Open</option><option value="closed">Closed</option><option value="all">All</option></select>
        <select className={`${fieldClass} !w-auto`} value={f.type} onChange={(e) => setF({ type: e.target.value })}><option value="">All types</option>{(status?.lead_types || []).map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
        <select className={`${fieldClass} !w-auto`} value={f.heat} onChange={(e) => setF({ heat: e.target.value })}><option value="">Hot, warm, cold</option><option value="hot">Hot only</option><option value="warm">Warm only</option><option value="cold">Cold only</option></select>
        <select className={`${fieldClass} !w-auto`} value={f.priority} onChange={(e) => setF({ priority: e.target.value })}><option value="">All priorities</option><option value="urgent">Urgent</option><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option></select>
        {has("see_all") && <select className={`${fieldClass} !w-auto`} value={f.owner} onChange={(e) => setF({ owner: e.target.value })}><option value="">All owners</option><option value="none">Not given yet</option>{people.map((p) => <option key={p.crm_user_id} value={p.crm_user_id}>{p.name}</option>)}</select>}
        <select className={`${fieldClass} !w-auto`} value={f.sort} onChange={(e) => setF({ sort: e.target.value })}><option value="pri">Priority first, then heat</option><option value="heat">Hottest first</option><option value="new">Newest first</option></select>
        {(f.kpi || f.q || f.type || f.heat || f.priority || f.owner || f.status !== "open") && <button type="button" className={btn.plain} onClick={() => { setSearch(""); setParams({}, { replace: true }); }}>Clear</button>}
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr><th className="px-3 py-2">Lead</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Priority</th><th className="px-3 py-2">Heat</th><th className="px-3 py-2">Wants</th><th className="px-3 py-2">Source</th><th className="px-3 py-2">Place</th><th className="px-3 py-2">Owner</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Follow-up</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(data?.items || []).map((l) => (
              <tr key={l.id} className="align-top hover:bg-sky-50/40">
                <td className="px-3 py-2"><Link to={`/sales/leads/${l.id}`} className="font-semibold text-indcool-navy hover:underline">{l.name}</Link><div className="text-xs text-slate-500">{l.phone}</div><div className="text-[11px] text-slate-400">{l.lead_no}</div></td>
                <td className="px-3 py-2"><TypeChip lead={l} /></td>
                <td className="px-3 py-2"><PriorityChip lead={l} always /></td>
                <td className="px-3 py-2"><HeatChip lead={l} /></td>
                <td className="px-3 py-2"><div>{l.item}</div><div className="text-xs text-slate-500">{valueText(l)}{l.closes_on ? ` · closes ${fmtDate(l.closes_on)}` : ""}</div>{l.details && <div className="text-xs text-slate-500">{l.details}</div>}</td>
                <td className="px-3 py-2">{l.source}{l.crm_ref && <div className="text-[11px] text-slate-400">{l.crm_ref}</div>}</td>
                <td className="px-3 py-2">{l.place || "—"}</td>
                <td className="px-3 py-2">{has("give") && !l.closed ? <button type="button" className="text-left text-indcool-blue hover:underline" onClick={() => setGiving(l)}>{l.owner_name || "Give it"}</button> : (l.owner_name || "—")}</td>
                <td className="px-3 py-2"><StatusChip status={l.status} /><div className="mt-1"><FirstCallChip lead={l} /></div></td>
                <td className="px-3 py-2">{l.follow_up_on ? <span className={l.follow_up_late ? "font-semibold text-rose-600" : ""}>{fmtDate(l.follow_up_on)}</span> : "—"}</td>
              </tr>
            ))}
            {!loading && (data?.items || []).length === 0 && <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-500">No lead matches.</td></tr>}
          </tbody>
        </table>
      </div>
      <AddLeadModal open={adding} onClose={() => setAdding(false)} onDone={() => { setAdding(false); reload(); }} />
      {uploading && <UploadModal mode="leads" onClose={() => setUploading(false)} onDone={(r) => { setUploading(false); if (r) { setMsg(`${r.created} lead(s) made from the file`); reload(); } }} />}
      {giving && <GiveModal open lead={giving} people={people} onClose={() => setGiving(null)} onDone={() => { setGiving(null); reload(); }} />}
    </div>
  );
}
