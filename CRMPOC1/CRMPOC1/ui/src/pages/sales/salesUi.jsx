import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";

import { salesApi } from "../../api/sales.js";

export { errText, fmtDate, fmtDateTime } from "../bids/bidUi.jsx";

export const HEAT = {
  hot: { label: "Hot", cls: "bg-rose-100 text-rose-700 border-rose-200", hint: "Ready to buy now" },
  warm: { label: "Warm", cls: "bg-amber-100 text-amber-800 border-amber-200", hint: "Interested, needs follow-up" },
  cold: { label: "Cold", cls: "bg-sky-100 text-sky-700 border-sky-200", hint: "Only enquiring" },
};
export const PRIORITY = {
  urgent: { label: "Urgent", cls: "bg-rose-600 text-white border-rose-700" },
  high: { label: "High", cls: "bg-orange-100 text-orange-700 border-orange-200" },
  normal: { label: "Normal", cls: "bg-slate-100 text-slate-600 border-slate-200" },
  low: { label: "Low", cls: "bg-slate-50 text-slate-400 border-slate-200" },
};
export const STATUS = {
  new: { label: "New", cls: "bg-sky-100 text-sky-800" },
  con: { label: "Contacted", cls: "bg-amber-100 text-amber-800" },
  int: { label: "Interested", cls: "bg-indigo-100 text-indigo-800" },
  quo: { label: "Quote sent", cls: "bg-cyan-100 text-cyan-800" },
  neg: { label: "Negotiation", cls: "bg-violet-100 text-violet-800" },
  won: { label: "Won", cls: "bg-emerald-600 text-white" },
  dis: { label: "Disposed", cls: "bg-slate-200 text-slate-700" },
  rev: { label: "Waiting for manager", cls: "bg-orange-100 text-orange-800" },
};
export const TYPE_COLOR = {
  gem: "#1d4ed8", csd: "#0e7490", retail: "#047857", spare: "#b45309", dealer: "#7c3aed", tender: "#be185d", corp: "#475569", export: "#0369a1",
};
export const QUOTE_TONE = {
  draft: "bg-slate-100 text-slate-700", wait: "bg-amber-100 text-amber-800", wadm: "bg-orange-100 text-orange-800", ret: "bg-violet-100 text-violet-800",
  appr: "bg-emerald-100 text-emerald-800", rej: "bg-rose-100 text-rose-800", sent: "bg-cyan-100 text-cyan-800", acc: "bg-emerald-600 text-white",
  cust_rej: "bg-slate-200 text-slate-700", cancel: "bg-rose-200 text-rose-900",
};

export const fieldClass = "w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:bg-slate-100";
export const btn = {
  primary: "rounded bg-indcool-blue px-3 py-2 text-sm font-semibold text-white hover:bg-indcool-navy disabled:opacity-50",
  go: "rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50",
  danger: "rounded bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-50",
  plain: "rounded border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50",
};

export function HeatChip({ lead }) {
  if (!lead || lead.closed) return null;
  const h = HEAT[lead.heat] || HEAT.cold;
  return <span title={h.hint} className={`inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${h.cls}`}>{h.label}{lead.heat === "hot" ? " · ready now" : ""}</span>;
}

export function PriorityChip({ lead, always = false }) {
  if (!lead || lead.closed) return null;
  if (!always && (lead.priority === "normal" || lead.priority === "low")) return null;
  const p = PRIORITY[lead.priority] || PRIORITY.normal;
  return <span className={`inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${p.cls}`}>{p.label}</span>;
}

export function TypeChip({ lead }) {
  const color = lead.lead_type_color || TYPE_COLOR[lead.lead_type] || "#64748b";
  return <span className="inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: `${color}1f`, color }}>{lead.lead_type_label}</span>;
}

export function StatusChip({ status }) {
  const s = STATUS[status] || { label: status, cls: "bg-slate-100 text-slate-700" };
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${s.cls}`}>{s.label}</span>;
}

export function timeAgo(iso) {
  if (!iso) return "";
  const text = String(iso);
  const t = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`).getTime();
  if (Number.isNaN(t)) return "";
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  if (m < 1440) return `${Math.floor(m / 60)} h ago`;
  return `${Math.floor(m / 1440)} day${Math.floor(m / 1440) > 1 ? "s" : ""} ago`;
}

// The workflow a lead goes through. Won and Disposed are the two ways it ends.
export const STAGES = [["new", "New"], ["con", "Contacted"], ["int", "Interested"], ["quo", "Quote sent"], ["neg", "Negotiation"]];

// The mark that someone has attended the lead: the person who has it did something about it.
export function AttendedChip({ lead }) {
  if (!lead || lead.closed) return null;
  if (lead.attended) {
    return <span title="The person who has this lead has acted on it" className="inline-block whitespace-nowrap rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">✓ Attended {timeAgo(lead.last_action_at)}{lead.attempts > 1 ? ` · ${lead.attempts} calls` : ""}</span>;
  }
  if (!lead.owner_user_id) return null;
  return <span title="Nobody has acted on this lead yet" className="inline-block whitespace-nowrap rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">Not attended yet</span>;
}

export function firstCall(lead) {
  if (lead.first_call_minutes === null || lead.first_call_minutes === undefined || lead.status !== "new") return null;
  const m = lead.first_call_minutes;
  const abs = Math.abs(m);
  const text = `${Math.floor(abs / 60) ? `${Math.floor(abs / 60)} h ` : ""}${abs % 60} min`;
  return m < 0 ? { late: true, text: `First call overdue by ${text}` } : { late: false, text: `First call due in ${text}` };
}

export function FirstCallChip({ lead }) {
  const fc = firstCall(lead);
  if (!fc) return null;
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${fc.late ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-800"}`}>{fc.text}</span>;
}

export function moneyIn(currency, value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (currency === "USD") return `US$ ${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function valueText(lead) {
  if (lead.is_prospect) return "Value not known yet";
  if (lead.crm_kind === "partner") return "Partner registration, no order value";
  if (lead.value_lakh === null || lead.value_lakh === undefined) return "Value not entered";
  return `Est. ₹${lead.value_lakh} lakh${lead.value_usd ? ` (US$ ${Number(lead.value_usd).toLocaleString("en-US")})` : ""}`;
}

// ---- who the person is in Sales: the ticks, read once and kept ----
const SalesContext = createContext({ ready: false, status: null, has: () => false, reload: () => {} });

export function SalesProvider({ children }) {
  const [state, setState] = useState({ ready: false, status: null, error: "" });
  const load = useCallback(() => {
    salesApi.status()
      .then((status) => setState({ ready: true, status, error: "" }))
      .catch((e) => setState({ ready: true, status: null, error: e?.response?.data?.detail || "Sales is not available" }));
  }, []);
  useEffect(() => { load(); }, [load]);
  const value = useMemo(() => ({
    ready: state.ready, status: state.status, error: state.error, reload: load,
    has: (tick) => !!state.status?.ticks?.includes(tick),
    any: (...ticks) => ticks.some((t) => state.status?.ticks?.includes(t)),
  }), [state, load]);
  return <SalesContext.Provider value={value}>{children}</SalesContext.Provider>;
}

export function useSales() {
  return useContext(SalesContext);
}

export function SalesTabs() {
  const { status } = useSales();
  const m = status?.menu || {};
  const dash = m.company_dashboard || m.team_dashboard || (status?.ticks || []).includes("my_dash");
  const tabs = [
    ["/sales", "My day", true],
    ["/sales/leads", m.leads_all ? "All leads" : "My leads"],
    ...(m.quotations ? [["/sales/quotations", "Quotations"]] : []),
    ...(m.export_desk ? [["/sales/export", "Export desk"]] : []),
    ...(m.team ? [["/sales/team", "Team and profiles"]] : []),
    ...(m.ticks ? [["/sales/ticks", "Access ticks"]] : []),
    ...(dash ? [["/sales/dashboard", "Dashboard"]] : []),
    ...((status?.ticks || []).includes("connect") ? [["/sales/sources", "Connections"]] : []),
    ...((status?.ticks || []).includes("reglog") ? [["/sales/log", "Registered-first log"]] : []),
    ...(m.ticks ? [["/sales/types", "Lead types"]] : []),
  ];
  return (
    <nav className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 pb-2">
      {tabs.map(([to, label, end]) => (
        <NavLink key={to} to={to} end={!!end} className={({ isActive }) => `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-indcool-blue text-white" : "text-slate-600 hover:bg-slate-100"}`}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function PageTitle({ title, sub, right }) {
  return (
    <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">{title}</h1>
        {sub && <p className="text-sm text-slate-500">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function Notice({ tone = "info", children }) {
  const cls = tone === "bad" ? "border-rose-200 bg-rose-50 text-rose-800" : tone === "warn" ? "border-amber-200 bg-amber-50 text-amber-900" : tone === "good" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-sky-200 bg-sky-50 text-sky-900";
  return <div className={`mb-3 rounded-md border px-3 py-2 text-sm ${cls}`}>{children}</div>;
}

export function Field({ label, children, hint }) {
  return (
    <label className="mb-3 block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function useAsync(fn, deps) {
  const [state, setState] = useState({ loading: true, data: null, error: "" });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: "" }));
    fn()
      .then((data) => live && setState({ loading: false, data, error: "" }))
      .catch((e) => live && setState({ loading: false, data: null, error: e?.response?.data?.detail || "Could not load" }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}
