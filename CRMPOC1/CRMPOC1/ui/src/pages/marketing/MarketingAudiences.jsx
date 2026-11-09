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

const EMPTY = { name: "", source: "prospects", market: "", stage: "", state: "", stale_days: "", heat: "", priority: "", csd_tier: "" };
const CSD_TIER_OPTIONS = {
  csd: [["", "Any tier"], ["retailer", "Retailer"], ["end", "End customer"], ["unset", "Unset — needs a look"]],
  gem: [["", "Any tier"], ["govt", "Govt buyer"], ["unset", "Unset — needs a look"]],
};

function toParams(f) {
  const p = {};
  for (const k of ["source", "market", "stage", "state", "stale_days", "heat", "priority", "csd_tier"]) {
    if (f[k]) p[k] = f[k];
  }
  return p;
}

function MembersModal({ title, params, onClose }) {
  const [state, setState] = useState({ loading: true, error: "", data: null });
  useEffect(() => {
    let alive = true;
    marketingApi.audienceMembers(params)
      .then((r) => { if (alive) setState({ loading: false, error: "", data: r }); })
      .catch((e) => { if (alive) setState({ loading: false, error: errText(e), data: null }); });
    return () => { alive = false; };
  }, [JSON.stringify(params)]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <div className="s-pop max-h-[80vh] w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
        <div className="max-h-[65vh] overflow-y-auto">
          {state.loading && <p className="px-4 py-6 text-center text-sm text-slate-500">Loading...</p>}
          {state.error && <div className="px-4 py-3"><Notice tone="bad">{state.error}</Notice></div>}
          {state.data && (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr><th className="px-4 py-2">Name</th><th className="px-4 py-2">Phone</th><th className="px-4 py-2">Email</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {state.data.members.map((m, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2">{m.name || "—"}{m.stopped && <span className="ml-1.5 rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">STOP</span>}</td>
                    <td className="px-4 py-2 text-slate-600">{m.phone || "—"}</td>
                    <td className="px-4 py-2 text-slate-600">{m.email || "—"}</td>
                  </tr>
                ))}
                {state.data.members.length === 0 && <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-400">Nobody matches yet.</td></tr>}
              </tbody>
            </table>
          )}
        </div>
        {state.data?.truncated && <div className="border-t border-slate-200 px-4 py-2 text-xs text-slate-400">Showing the first {state.data.members.length} of {state.data.total}.</div>}
      </div>
    </div>
  );
}

function Form({ initial, canAll, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [count, setCount] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [showMembers, setShowMembers] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    let alive = true;
    marketingApi.audienceCount(toParams(form)).then((r) => { if (alive) setCount(r.count); }).catch(() => { if (alive) setCount(null); });
    return () => { alive = false; };
  }, [form.source, form.market, form.stage, form.state, form.stale_days, form.heat, form.priority, form.csd_tier]);

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
          <select className={fieldClass} value={form.market} onChange={(e) => setForm((f) => ({ ...f, market: e.target.value, csd_tier: "" }))}>
            <option value="">Any market</option>
            {MARKETS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        {(form.market === "csd" || form.market === "gem") && (
          <label className="text-sm text-slate-600">Buyer tier
            <select className={fieldClass} value={form.csd_tier} onChange={set("csd_tier")}>
              {CSD_TIER_OPTIONS[form.market].map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
        )}
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
        <button type="button" onClick={() => count > 0 && setShowMembers(true)}
          className={`rounded-full bg-violet-100 px-3 py-1 text-sm font-semibold text-violet-700 ${count > 0 ? "hover:bg-violet-200" : "cursor-default"}`}>
          {count === null ? "..." : count} people match{count > 0 ? " · view list" : ""}
        </button>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-800">{suggestedTone(form.market)}</span>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>{form.id ? "Save changes" : "Save audience"}</button>
        <button type="button" className={btn.plain} onClick={onCancel}>Cancel</button>
      </div>
      {showMembers && <MembersModal title={`${form.name || "This audience"} — matching people`} params={toParams(form)} onClose={() => setShowMembers(false)} />}
    </div>
  );
}

export default function MarketingAudiences() {
  const { has } = useMarketing();
  const canAll = has("aud_all");
  const list = useAsync(() => marketingApi.audiences(), []);
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");
  const [viewing, setViewing] = useState(null);

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
              <button type="button" disabled={!a.count} onClick={() => setViewing(a)}
                className={`rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700 ${a.count ? "hover:bg-violet-200" : "cursor-default"}`}>
                {a.count}
              </button>
            </div>
            <div className="mt-1 text-xs text-slate-500">{a.source === "customers" ? "Customers" : "Prospects"} · {MARKETS.find((m) => m[0] === a.market)?.[1] || "Any market"}{a.csd_tier ? ` · ${(CSD_TIER_OPTIONS[a.market] || []).find((t) => t[0] === a.csd_tier)?.[1] || a.csd_tier}` : ""}{a.stage ? ` · ${STAGES.find((s) => s[0] === a.stage)?.[1] || a.stage}` : ""}</div>
            <div className="mt-2 flex gap-2">
              <button type="button" className={btn.plain} onClick={() => setEditing({ ...EMPTY, ...a, stale_days: a.stale_days ?? "" })}>Edit</button>
              <button type="button" className={btn.plain} onClick={() => remove(a)}>Delete</button>
            </div>
          </div>
        ))}
        {!list.loading && (list.data || []).length === 0 && <p className="text-sm text-slate-500">No saved audiences yet.</p>}
      </div>
      {viewing && <MembersModal title={`${viewing.name} — matching people`} params={toParams(viewing)} onClose={() => setViewing(null)} />}
    </div>
  );
}
