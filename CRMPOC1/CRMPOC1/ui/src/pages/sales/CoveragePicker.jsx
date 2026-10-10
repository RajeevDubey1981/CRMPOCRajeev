import { useMemo, useState } from "react";

import { INDIAN_STATES_UTS } from "../../data/indianStates.js";
import { districtsOf, sameDistrict } from "../../constants/indianDistricts.js";
import { fieldClass } from "./salesUi.jsx";

const plain = (t) => String(t || "").toLowerCase().replace(/[^a-z0-9]/g, "");

// What the profile starts with: the saved coverage, or the older list of areas turned into whole states.
export function startCoverage(person) {
  if (person.coverage) return { mode: person.coverage.mode, states: { ...(person.coverage.states || {}) } };
  const states = {};
  const countries = [];
  (person.areas || []).forEach((a) => {
    const hit = INDIAN_STATES_UTS.find((s) => plain(s) === plain(a));
    if (hit) states[hit] = { all: true, districts: [], pins: [] }; else countries.push(a);
  });
  const pins = person.extra_pincodes || [];
  if (pins.length && person.state) {
    const home = INDIAN_STATES_UTS.find((s) => plain(s) === plain(person.state)) || person.state;
    states[home] = states[home] ? { ...states[home], pins } : { all: false, districts: [], pins };
  }
  return { mode: "states", states, countries };
}

// A readable line for the table.
export function coverageText(person) {
  const c = person.coverage;
  if (!c) return null;
  if (c.mode === "all") return "All India";
  const parts = Object.entries(c.states || {}).map(([s, r]) => (r.all ? `${s} (whole)` : `${s}: ${[...(r.districts || [])].join(", ") || "pin codes only"}${(r.pins || []).length ? ` + ${r.pins.length} pin${r.pins.length > 1 ? "s" : ""}` : ""}`));
  return parts.join(" · ") || "Nothing selected";
}

export function coverageProblem(cov) {
  if (cov.mode !== "states") return "";
  for (const [name, r] of Object.entries(cov.states)) {
    if (!r.all && !(r.districts || []).length && !(r.pins || []).length) return `${name}: choose the whole state, some districts, or add pin codes`;
  }
  return "";
}

function Chip({ children, onRemove, tone = "blue" }) {
  return (
    <span className={`s-pop inline-flex items-center gap-1 rounded-full py-0.5 pl-2.5 pr-1 text-xs font-semibold ${tone === "pin" ? "border border-slate-200 bg-slate-50 tabular-nums text-slate-700" : "bg-sky-100 text-indcool-navy"}`}>
      {children}
      <button type="button" onClick={onRemove} aria-label="Remove" className="grid h-4 w-4 place-items-center rounded-full bg-black/10 text-[10px] leading-none hover:bg-rose-500 hover:text-white">×</button>
    </span>
  );
}

function Search({ placeholder, options, onPick, note }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const list = useMemo(() => options.filter((o) => plain(o).includes(plain(q))).slice(0, 60), [options, q]);
  return (
    <div className="relative">
      <input className={fieldClass} value={q} placeholder={placeholder} onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); if (list[0]) { onPick(list[0]); setQ(""); } else if (q.trim() && note) { onPick(q.trim()); setQ(""); } } }} />
      {open && (
        <div className="s-fade absolute left-0 right-0 z-20 mt-1 max-h-56 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
          {list.map((o) => <button key={o} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => { onPick(o); setQ(""); }} className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50">{o}</button>)}
          {list.length === 0 && <div className="px-3 py-2 text-xs text-slate-500">{note || "Nothing more matches."}</div>}
        </div>
      )}
    </div>
  );
}

function PinBox({ pins, onChange }) {
  const [text, setText] = useState("");
  const [bad, setBad] = useState("");
  function take(raw) {
    const parts = raw.split(/[\s,;]+/).filter(Boolean);
    const good = parts.filter((p) => /^\d{6}$/.test(p));
    const wrong = parts.filter((p) => !/^\d{6}$/.test(p));
    if (good.length) onChange([...new Set([...pins, ...good])]);
    setBad(wrong.length ? `Not a 6 digit pin code: ${wrong.join(", ")}` : "");
    setText(wrong.join(" "));
  }
  return (
    <div>
      <input className={fieldClass} value={text} inputMode="numeric" placeholder="Type or paste pin codes, press Enter or comma" onChange={(e) => setText(e.target.value)} onBlur={() => text.trim() && take(text)}
        onPaste={(e) => { e.preventDefault(); take(e.clipboardData.getData("text")); }}
        onKeyDown={(e) => { if (["Enter", ",", " "].includes(e.key)) { e.preventDefault(); take(text); } }} />
      {bad && <div className="mt-1 text-xs text-rose-600">{bad}</div>}
      <div className="mt-1.5 flex flex-wrap gap-1.5">{pins.map((p) => <Chip key={p} tone="pin" onRemove={() => onChange(pins.filter((x) => x !== p))}>{p}</Chip>)}</div>
    </div>
  );
}

function StateCard({ name, row, onChange, onRemove }) {
  const list = districtsOf(name);
  const pick = (all) => onChange({ ...row, all, districts: all ? [] : row.districts });
  return (
    <div className="s-rise mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <b className="text-sm text-slate-800">{name}</b>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md border border-slate-200 bg-white p-0.5 text-xs font-semibold">
            <button type="button" onClick={() => pick(true)} className={`rounded px-2.5 py-1 ${row.all ? "bg-indcool-blue text-white" : "text-slate-600"}`}>Whole state</button>
            <button type="button" onClick={() => pick(false)} className={`rounded px-2.5 py-1 ${!row.all ? "bg-indcool-blue text-white" : "text-slate-600"}`}>Some districts</button>
          </div>
          <button type="button" onClick={onRemove} className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100">Remove</button>
        </div>
      </div>
      {!row.all && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-bold text-slate-500">Districts</div>
          <Search placeholder="Search and add a district..." options={list.filter((d) => !row.districts.some((x) => sameDistrict(x, d)))} note={list.length ? "No more districts match." : "No list for this state. Type the name and press Enter."} onPick={(d) => onChange({ ...row, districts: [...row.districts, d] })} />
          <div className="mt-1.5 flex flex-wrap gap-1.5">{row.districts.map((d) => <Chip key={d} onRemove={() => onChange({ ...row, districts: row.districts.filter((x) => x !== d) })}>{d}</Chip>)}</div>
        </div>
      )}
      <div className="mt-3">
        <div className="mb-1 text-xs font-bold text-slate-500">Extra pin codes in {name} (optional)</div>
        <PinBox pins={row.pins || []} onChange={(pins) => onChange({ ...row, pins })} />
        <div className="mt-1 text-xs text-slate-500">{row.all ? "The whole state is covered, so extra pin codes are not needed." : "A lead from one of these pin codes comes to this person even outside the chosen districts."}</div>
      </div>
    </div>
  );
}

// All India, or selected states; each state is the whole state or some districts, with extra pin codes.
export default function CoveragePicker({ value, onChange, disabled = false, noun = "lead" }) {
  const { mode, states } = value;
  const names = Object.keys(states);
  const set = (patch) => onChange({ ...value, ...patch });
  const wholeCount = names.filter((n) => states[n].all).length;
  const districts = names.reduce((n, k) => n + (states[k].all ? 0 : states[k].districts.length), 0);
  const pins = names.reduce((n, k) => n + (states[k].pins || []).length, 0);
  const [tState, setTState] = useState("");
  const [tDist, setTDist] = useState("");
  const [tPin, setTPin] = useState("");
  const tested = (() => {
    if (!tState && !tPin) return null;
    if (mode === "all") return true;
    if (tPin && names.some((n) => (states[n].pins || []).includes(tPin.trim()))) return true;
    const hit = names.find((n) => plain(n) === plain(tState));
    if (!hit) return false;
    return states[hit].all || (!!tDist && states[hit].districts.some((d) => sameDistrict(d, tDist)));
  })();

  return (
    <fieldset disabled={disabled} className={disabled ? "opacity-60" : ""}>
      <div className="grid gap-2 sm:grid-cols-2">
        {[["all", "All India", "Any state, any district, any pin code"], ["states", "Selected states", "Pick states, then districts or pin codes"]].map(([k, t, d]) => (
          <button key={k} type="button" onClick={() => set({ mode: k })} className={`s-press s-lift relative rounded-lg border-2 px-3 py-2.5 text-left ${mode === k ? "border-indcool-blue bg-sky-50" : "border-slate-200 bg-white"}`}>
            <div className="text-sm font-bold text-slate-800">{t}</div><div className="text-xs text-slate-500">{d}</div>
            {mode === k && <span className="s-pop absolute right-3 top-2 text-indcool-blue">✓</span>}
          </button>
        ))}
      </div>
      {mode === "states" && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-bold text-slate-500">States covered</div>
          <Search placeholder="Search and add a state..." options={INDIAN_STATES_UTS.filter((s) => !states[s])} onPick={(s) => set({ states: { ...states, [s]: { all: true, districts: [], pins: [] } } })} />
          {names.length === 0 && <p className="mt-2 text-xs text-slate-500">No state selected yet. Choose at least one state, or All India.</p>}
          {names.map((n) => <StateCard key={n} name={n} row={states[n]} onChange={(row) => set({ states: { ...states, [n]: row } })} onRemove={() => { const next = { ...states }; delete next[n]; set({ states: next }); }} />)}
        </div>
      )}
      <div className="s-fade mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
        {mode === "all" ? `Covers all of India. Every new ${noun} can come to this person.` : names.length ? `Covers ${names.length} state${names.length > 1 ? "s" : ""}: ${wholeCount} whole, ${districts} district${districts === 1 ? "" : "s"} in the others, ${pins} extra pin code${pins === 1 ? "" : "s"}` : "Nothing selected yet"}
      </div>
      <details className="mt-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold text-slate-600">Try a lead</summary>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          <select className={fieldClass} value={tState} onChange={(e) => { setTState(e.target.value); setTDist(""); }}><option value="">State</option>{INDIAN_STATES_UTS.map((s) => <option key={s}>{s}</option>)}</select>
          <select className={fieldClass} value={tDist} onChange={(e) => setTDist(e.target.value)}><option value="">District (optional)</option>{districtsOf(tState).map((d) => <option key={d}>{d}</option>)}</select>
          <input className={fieldClass} value={tPin} maxLength={6} inputMode="numeric" placeholder="Pin code (optional)" onChange={(e) => setTPin(e.target.value.replace(/\D/g, ""))} />
        </div>
        {tested !== null && <div className={`s-pop mt-2 inline-block rounded-md px-3 py-1 text-sm font-semibold ${tested ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-700"}`}>{tested ? "Yes, this lead would come to this person" : "No, this lead is outside the coverage"}</div>}
      </details>
    </fieldset>
  );
}
