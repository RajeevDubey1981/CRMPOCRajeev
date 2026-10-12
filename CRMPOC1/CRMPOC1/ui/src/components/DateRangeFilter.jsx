import { useEffect, useRef, useState } from "react";

// One date filter for every list and dashboard: a button that opens quick choices and From and To boxes.
// The choice is remembered in this browser, so the same dates stay when you move between screens.
const KEY = "crm_registered_range";

const pad = (n) => String(n).padStart(2, "0");
export const isoDay = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const daysBack = (n) => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - n); return d; };

export const PRESETS = [
  ["Today", () => [daysBack(0), daysBack(0)]],
  ["Yesterday", () => [daysBack(1), daysBack(1)]],
  ["Last 7 days", () => [daysBack(6), daysBack(0)]],
  ["Last 30 days", () => [daysBack(29), daysBack(0)]],
  ["This month", () => { const d = new Date(); return [new Date(d.getFullYear(), d.getMonth(), 1), daysBack(0)]; }],
];

function readSaved() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!s) return null;
    const p = PRESETS.find(([n]) => n === s.name);
    if (p) { const [a, b] = p[1](); return { name: s.name, from: isoDay(a), to: isoDay(b) }; }
    return s.from || s.to ? { name: "", from: s.from || "", to: s.to || "" } : null;
  } catch { return null; }
}
function save(v) { try { if (v) localStorage.setItem(KEY, JSON.stringify(v)); else localStorage.removeItem(KEY); } catch { /* the choice is simply not remembered */ } }

const show = (iso) => (iso ? new Date(`${iso}T00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "");

// from and to are "YYYY-MM-DD" or "". onChange(from, to) is called with the new range.
export default function DateRangeFilter({ from = "", to = "", onChange, label = "Registered", remember = true, className = "" }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const box = useRef(null);

  // pick up the remembered dates once, when the screen opens with no dates of its own
  useEffect(() => {
    if (!remember || from || to) return;
    const s = readSaved();
    if (s) { setName(s.name); onChange(s.from, s.to); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const set = !!(from || to);
  function apply(a, b, n = "") {
    setName(n);
    if (remember) save(a || b ? { name: n, from: a, to: b } : null);
    onChange(a, b);
  }
  const text = !set ? `${label}: any date` : name ? `${label}: ${name}` : `${label}: ${from ? show(from) : "start"} to ${to ? show(to) : "today"}`;

  return (
    <div ref={box} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`s-press inline-flex items-center gap-2 rounded border px-3 py-2 text-sm transition-colors ${set ? "border-indcool-blue bg-sky-50 font-semibold text-indcool-navy" : "border-slate-300 bg-white text-slate-700 hover:border-indcool-blue"}`}
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></svg>
        <span>{text}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="s-pop absolute left-0 top-full z-30 mt-2 w-[21rem] max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xl">
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map(([n, fn]) => (
              <button
                key={n}
                type="button"
                onClick={() => { const [a, b] = fn(); apply(isoDay(a), isoDay(b), n); setOpen(false); }}
                className={`s-press rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${name === n ? "border-indcool-blue bg-indcool-blue text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"}`}
              >{n}</button>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <label className="flex flex-col gap-1 text-[11px] font-semibold text-slate-500">From
              <input type="date" value={from} max={to || undefined} onChange={(e) => apply(e.target.value, to, "")} className="rounded border border-slate-300 px-2 py-1.5 text-sm font-normal text-slate-800" />
            </label>
            <label className="flex flex-col gap-1 text-[11px] font-semibold text-slate-500">To
              <input type="date" value={to} min={from || undefined} onChange={(e) => apply(from, e.target.value, "")} className="rounded border border-slate-300 px-2 py-1.5 text-sm font-normal text-slate-800" />
            </label>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
            <span>Your dates stay when you change screens</span>
            <button type="button" className="font-semibold text-indcool-blue hover:underline" onClick={() => { apply("", ""); setOpen(false); }}>Clear dates</button>
          </div>
        </div>
      )}
    </div>
  );
}

// The line shown under the filters while dates are set.
export function DateRangeTag({ from, to, onClear, count }) {
  if (!from && !to) return null;
  return (
    <div className="s-pop mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 py-1 pl-3 pr-1.5 font-semibold text-indcool-navy">
        Registered: {from ? show(from) : "start"} to {to ? show(to) : "today"}
        <button type="button" onClick={onClear} aria-label="Remove date filter" className="grid h-4 w-4 place-items-center rounded-full bg-sky-200 text-[10px] leading-none text-indcool-navy">✕</button>
      </span>
      {typeof count === "number" && <span>{count} shown</span>}
    </div>
  );
}
