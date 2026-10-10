import { useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import { AddLeadModal, CallModal } from "./LeadModals.jsx";
import {
  FirstCallChip, HeatChip, Notice, PageTitle, PriorityChip, SalesTabs, StatusChip, TypeChip, btn, fmtDate, useAsync, useSales, valueText,
} from "./salesUi.jsx";

export function waLink(phone) {
  const digits = String(phone || "").replace(/\D/g, "");
  return `https://wa.me/${digits.length === 10 ? `91${digits}` : digits}`;
}

function LeadCard({ lead, onCall }) {
  const late = lead.follow_up_late || (lead.first_call_minutes !== null && lead.first_call_minutes < 0);
  return (
    <div className={`rounded-lg border bg-white p-3 shadow-sm ${late || lead.priority === "urgent" ? "border-l-4 border-l-rose-500" : "border-slate-200"}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        <Link to={`/sales/leads/${lead.id}`} className="text-sm font-semibold text-indcool-navy hover:underline">{lead.name}</Link>
        <PriorityChip lead={lead} />
        <TypeChip lead={lead} />
        <HeatChip lead={lead} />
        <FirstCallChip lead={lead} />
        <StatusChip status={lead.status} />
        {lead.crm_kind && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">Auto · {lead.source}</span>}
      </div>
      <div className="mt-1 text-sm text-slate-700">{lead.item}</div>
      {lead.details && <div className="text-xs text-slate-500">{lead.details}</div>}
      <div className="text-xs text-slate-500">{[lead.place, lead.phone, lead.source].filter(Boolean).join(" · ")}{lead.follow_up_on ? ` · follow-up ${fmtDate(lead.follow_up_on)}` : ""} · {valueText(lead)}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        <a className={btn.go} href={`tel:${lead.phone}`}>Call</a>
        <a className={btn.plain} href={waLink(lead.phone)} target="_blank" rel="noreferrer">WhatsApp</a>
        <button type="button" className={btn.primary} onClick={() => onCall(lead)}>Log call</button>
        <Link className={btn.plain} to={`/sales/leads/${lead.id}`}>Open</Link>
      </div>
    </div>
  );
}

function Group({ title, tone, list, onCall }) {
  if (!list.length) return null;
  const cls = tone === "red" ? "bg-rose-50 text-rose-700" : tone === "amber" ? "bg-amber-50 text-amber-800" : "bg-slate-100 text-slate-600";
  return (
    <section className="mb-4">
      <h2 className={`mb-2 rounded px-3 py-1.5 text-xs font-bold uppercase tracking-wide ${cls}`}>{title} ({list.length})</h2>
      <div className="grid gap-2 lg:grid-cols-2">{list.map((l) => <LeadCard key={l.id} lead={l} onCall={onCall} />)}</div>
    </section>
  );
}

export default function MyDay() {
  const { has } = useSales();
  const { data, loading, error, reload } = useAsync(() => salesApi.leads({ owner: "me", status: "open", limit: 500 }), []);
  const [call, setCall] = useState(null);
  const [adding, setAdding] = useState(false);
  const items = data?.items || [];
  const used = new Set();
  const take = (pred) => items.filter((l) => !used.has(l.id) && pred(l) && (used.add(l.id) || true));
  const first = take((l) => ["urgent", "high"].includes(l.priority));
  const hot = take((l) => l.heat === "hot");
  const fresh = take((l) => l.status === "new");
  const over = take((l) => l.follow_up_late);
  const today = take((l) => l.follow_up_on === new Date().toISOString().slice(0, 10));
  const later = take(() => true);

  return (
    <div>
      <PageTitle title="My day" sub="Your leads, in the order to work them" right={has("add_lead") && <button type="button" className={btn.go} onClick={() => setAdding(true)}>+ Add lead</button>} />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      {loading && !data && <p className="text-sm text-slate-500">Loading...</p>}
      {data && (
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {[["Open leads", data.counts.open, ""], ["Urgent or high", data.counts.urgent, "text-rose-600"], ["Hot", data.counts.hot, "text-rose-600"], ["Due today", data.counts.due_today, ""], ["Overdue", data.counts.overdue, "text-rose-600"], ["First calls late", data.counts.first_overdue, "text-rose-600"]].map(([l, v, c]) => (
            <div key={l} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"><div className={`text-2xl font-semibold tabular-nums ${c}`}>{v}</div><div className="text-xs text-slate-500">{l}</div></div>
          ))}
        </div>
      )}
      <Group title="Urgent and high priority: do these first" tone="red" list={first} onCall={setCall} />
      <Group title="Hot: ready to buy, close these first" tone="red" list={hot} onCall={setCall} />
      <Group title="New: make the first call" tone="amber" list={fresh} onCall={setCall} />
      <Group title="Overdue: call these first" tone="red" list={over} onCall={setCall} />
      <Group title="Due today" tone="amber" list={today} onCall={setCall} />
      <Group title="Later" list={later} onCall={setCall} />
      {data && items.length === 0 && <p className="text-sm text-slate-500">Nothing open. Well done.</p>}
      {call && <CallModal open lead={call} onClose={() => setCall(null)} onDone={() => { setCall(null); reload(); }} />}
      <AddLeadModal open={adding} onClose={() => setAdding(false)} onDone={() => { setAdding(false); reload(); }} />
    </div>
  );
}
