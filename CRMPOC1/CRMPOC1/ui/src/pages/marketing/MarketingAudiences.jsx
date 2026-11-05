import { useEffect, useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useAsync, useMarketing } from "./marketingUi.jsx";

const MARKETS = [
  ["gem", "GeM"], ["csd", "CSD"], ["retail", "Retail"], ["spare", "Spare parts"], ["dealer", "Dealer"],
  ["tender", "State tender"], ["corp", "Corporate / project"], ["export", "Export"],
  ["service_engineer", "Service Engineer"], ["service_franchisee", "Service Franchisee"],
];
const STAGES = [
  ["", "Any stage"], ["new", "New"], ["con", "Contacted"], ["int", "Interested, not onboarded"],
  ["quo", "Quote sent"], ["neg", "Negotiation"], ["won", "Won"], ["dis", "Disposed"],
];
const TONE = {
  dealer: "B2B, pricing-led", csd: "B2B, pricing-led", gem: "B2B, tender-led", tender: "B2B, tender-led", corp: "B2B, project-led",
  retail: "Consumer, offer-led", export: "B2B, catalog-led", spare: "Operational, availability-led",
  service_engineer: "Operational, incentive-led", service_franchisee: "Operational, incentive-led",
};

function suggestedTone(market) {
  if (!market) return "Pick a market to see a suggested tone";
  return TONE[market] || "General outreach";
}

const EMPTY = { name: "", source: "prospects", market: "", stage: "", state: "", stale_days: "", heat: "", priority: "" };

function toParams(f) {
  const p = {};
  for (const k of ["source", "market", "stage", "state", "stale_days", "heat", "priority"]) {
    if (f[k]) p[k] = f[k];
  }
  return p;
}

function Form({ initial, canAll, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [count, setCount] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    let alive = true;
    marketingApi.audienceCount(toParams(form)).then((r) => { if (alive) setCount(r.count); }).catch(() => { if (alive) setCount(null); });
    return () => { alive = false; };
  }, [form.source, form.market, form.stage, form.state, form.stale_days, form.heat, form.priority]);

  async function save() {
    if (!form.name.trim()) { setMsg("Give this audience a name."); return; }
    setBusy(true); setMsg("");
    try {
      const body = { ...form, stale_days: form.stale_days ? Number(form.stale_days) : null };
      if (form.id) await marketingApi.updateAudience(form.id, body);
      else await marketingApi.createAudience(body);
      onSaved();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-800">{form.id ? "Edit audience" : "New audience"}</h3>
      {msg && <Notice tone="bad">{msg}</Notice>}
      <div className="mb-3 flex gap-2">
        {[["prospects", "Prospects (Sales leads)"], ["customers", "Customers (already bought)"]].map(([v, l]) => (
          <button key={v} type="button" disabled={v === "customers" && !canAll}
            className={`s-press rounded-md px-3 py-1.5 text-sm font-medium ${form.source === v ? "bg-violet-600 text-white" : "bg-slate-100 text-slate-600"} ${v === "customers" && !canAll ? "opacity-40" : ""}`}
            onClick={() => setForm((f) => ({ ...f, source: v }))}>{l}</button>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm text-slate-600">Audience name
          <input className={fieldClass} value={form.name} onChange={set("name")} placeholder="GeM dealers, interested" />
        </label>
        <label className="text-sm text-slate-600">Market
          <select className={fieldClass} value={form.market} onChange={set("market")}>
            <option value="">Any market</option>
            {MARKETS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        {form.source === "prospects" && (
          <label className="text-sm text-slate-600">Stage
            <select className={fieldClass} value={form.stage} onChange={set("stage")}>
              {STAGES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
        )}
        <label className="text-sm text-slate-600">Place (state)
          <input className={fieldClass} value={form.state} onChange={set("state")} placeholder="e.g. Delhi" />
        </label>
        <label className="text-sm text-slate-600">No action in at least (days)
          <input type="number" min="0" className={fieldClass} value={form.stale_days} onChange={set("stale_days")} placeholder="e.g. 15" />
        </label>
        {form.source === "prospects" && (
          <>
            <label className="text-sm text-slate-600">Heat
              <select className={fieldClass} value={form.heat} onChange={set("heat")}>
                <option value="">Any</option><option value="hot">Hot</option><option value="warm">Warm</option><option value="cold">Cold</option>
              </select>
            </label>
            <label className="text-sm text-slate-600">Priority
              <select className={fieldClass} value={form.priority} onChange={set("priority")}>
                <option value="">Any</option><option value="urgent">Urgent</option><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option>
              </select>
            </label>
          </>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-violet-100 px-3 py-1 text-sm font-semibold text-violet-700">{count === null ? "..." : count} people match</span>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-800">{suggestedTone(form.market)}</span>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>{form.id ? "Save changes" : "Save audience"}</button>
        <button type="button" className={btn.plain} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function MarketingAudiences() {
  const { has } = useMarketing();
  const canAll = has("aud_all");
  const list = useAsync(() => marketingApi.audiences(), []);
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");

  async function remove(a) {
    if (!window.confirm(`Delete audience "${a.name}"?`)) return;
    try { await marketingApi.deleteAudience(a.id); list.reload(); } catch (e) { setMsg(errText(e)); }
  }

  return (
    <div>
      <PageTitle title="Audiences" sub="Build a list from Sales leads (not yet onboarded) or existing customers (already bought), by market, stage and place." />
      <MarketingTabs />
      {msg && <Notice tone="bad">{msg}</Notice>}
      {list.error && <Notice tone="bad">{list.error}</Notice>}

      {editing ? (
        <Form initial={editing} canAll={canAll} onSaved={() => { setEditing(null); list.reload(); }} onCancel={() => setEditing(null)} />
      ) : (
        <div className="mb-4"><button type="button" className={btn.primary} onClick={() => setEditing({ ...EMPTY })}>+ New audience</button></div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {(list.data || []).map((a, i) => (
          <div key={a.id} style={{ "--i": i }} className="s-rise rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-slate-800">{a.name}</span>
              <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700">{a.count}</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">{a.source === "customers" ? "Customers" : "Prospects"} · {MARKETS.find((m) => m[0] === a.market)?.[1] || "Any market"}{a.stage ? ` · ${STAGES.find((s) => s[0] === a.stage)?.[1] || a.stage}` : ""}</div>
            <div className="mt-2 flex gap-2">
              <button type="button" className={btn.plain} onClick={() => setEditing({ ...EMPTY, ...a, stale_days: a.stale_days ?? "" })}>Edit</button>
              <button type="button" className={btn.plain} onClick={() => remove(a)}>Delete</button>
            </div>
          </div>
        ))}
        {!list.loading && (list.data || []).length === 0 && <p className="text-sm text-slate-500">No saved audiences yet.</p>}
      </div>
    </div>
  );
}
