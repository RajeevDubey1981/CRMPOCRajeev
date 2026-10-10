import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import {
  AttendedChip, HeatChip, Icon, Notice, PageTitle, PriorityChip, SalesTabs, TypeChip, btn, errText, fieldClass, useAsync, useSales, valueText,
} from "./salesUi.jsx";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HEAT_BAR = { hot: "border-l-rose-500 bg-rose-50 text-rose-800", warm: "border-l-amber-500 bg-amber-50 text-amber-900", cold: "border-l-sky-500 bg-sky-50 text-sky-800" };

// Dates are kept as local YYYY-MM-DD text so a day never slips by one because of the time zone.
const key = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const parse = (k) => { const [y, m, d] = k.split("-").map(Number); return new Date(y, m - 1, d); };
const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
const weekStart = (d) => addDays(d, -((d.getDay() + 6) % 7));
const longDay = (d) => `${DAYS[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;

function Chip({ lead, onDragStart, late }) {
  return (
    <Link
      to={`/sales/leads/${lead.id}`}
      draggable
      onDragStart={(e) => onDragStart(e, lead)}
      title={`${lead.name} · ${lead.item || ""}`}
      className={`s-lift mt-1 flex cursor-grab items-center gap-1 truncate rounded border-l-4 px-1.5 py-0.5 text-[11px] font-medium active:cursor-grabbing ${HEAT_BAR[lead.heat] || HEAT_BAR.cold} ${late ? "ring-1 ring-rose-300" : ""}`}
    >
      {lead.priority === "urgent" && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-rose-600" />}
      <span className="truncate">{lead.name}</span>
    </Link>
  );
}

function LeadRow({ lead, today, onMove, busy, index }) {
  const late = lead.follow_up_on && lead.follow_up_on < today;
  return (
    <div className="s-rise rounded-lg border border-slate-200 bg-white p-3" style={{ "--i": index }}>
      <div className="flex flex-wrap items-center gap-1.5">
        <Link to={`/sales/leads/${lead.id}`} className="text-sm font-semibold text-indcool-navy hover:underline">{lead.name}</Link>
        <PriorityChip lead={lead} />
        <TypeChip lead={lead} />
        <HeatChip lead={lead} />
        <AttendedChip lead={lead} />
        {late && <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">Late</span>}
      </div>
      <div className="mt-0.5 text-sm text-slate-700">{lead.item}</div>
      <div className="text-xs text-slate-500">{[lead.place, lead.phone].filter(Boolean).join(" · ")} · {valueText(lead)}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        <a className={btn.go} href={`tel:${lead.phone}`}><Icon name="phone" size={14} className="mr-1.5 -mt-0.5" />Call</a>
        <button type="button" className={btn.plain} disabled={busy} onClick={() => onMove(lead, key(addDays(new Date(), 1)))}>Tomorrow</button>
        <button type="button" className={btn.plain} disabled={busy} onClick={() => onMove(lead, key(addDays(new Date(), 7)))}>Next week</button>
        <Link className={btn.plain} to={`/sales/leads/${lead.id}`}>Open</Link>
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const { has } = useSales();
  const [mode, setMode] = useState("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const [picked, setPicked] = useState(() => key(new Date()));
  const [owner, setOwner] = useState(has("see_all") ? "" : "me");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState("");
  const { data, loading, error, reload } = useAsync(() => salesApi.leads({ status: "open", limit: 500, owner: owner || undefined }), [owner]);
  const today = key(new Date());

  const leads = useMemo(() => (data?.items || []).filter((l) => l.follow_up_on), [data]);
  const byDay = useMemo(() => {
    const m = {};
    leads.forEach((l) => { (m[l.follow_up_on] = m[l.follow_up_on] || []).push(l); });
    return m;
  }, [leads]);
  const late = leads.filter((l) => l.follow_up_on < today);
  const noDate = (data?.items || []).filter((l) => !l.follow_up_on);

  async function move(lead, day) {
    if (!day || day === lead.follow_up_on) return;
    setBusy(true);
    try {
      await salesApi.followUp(lead.id, day);
      setNote(`${lead.name}: follow-up moved to ${longDay(parse(day))}`);
      reload();
    } catch (e) { setNote(errText(e)); } finally { setBusy(false); }
  }
  const dragStart = (e, lead) => { e.dataTransfer.setData("text/plain", String(lead.id)); e.dataTransfer.effectAllowed = "move"; };
  const dropOn = (day) => (e) => {
    e.preventDefault();
    setOver("");
    const lead = (data?.items || []).find((l) => String(l.id) === e.dataTransfer.getData("text/plain"));
    if (lead) move(lead, day);
  };
  const dropProps = (day) => ({ onDragOver: (e) => { e.preventDefault(); if (over !== day) setOver(day); }, onDragLeave: () => setOver(""), onDrop: dropOn(day) });

  function step(n) {
    if (mode === "month") setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + n, 1));
    else setAnchor(addDays(anchor, n * (mode === "week" ? 7 : 1)));
  }
  const title = mode === "month" ? `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`
    : mode === "day" ? longDay(anchor)
      : `${weekStart(anchor).getDate()} ${MONTHS[weekStart(anchor).getMonth()].slice(0, 3)} – ${addDays(weekStart(anchor), 6).getDate()} ${MONTHS[addDays(weekStart(anchor), 6).getMonth()].slice(0, 3)} ${addDays(weekStart(anchor), 6).getFullYear()}`;

  const monthCells = useMemo(() => {
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const start = weekStart(first);
    return Array.from({ length: 42 }, (_, i) => addDays(start, i));
  }, [anchor]);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart(anchor), i)), [anchor]);
  const dayList = byDay[picked] || [];

  return (
    <div>
      <PageTitle title="Follow-up calendar" sub="Every follow-up date in one place. Drag a lead onto another day to move its follow-up." />
      <SalesTabs />
      {note && <Notice>{note}</Notice>}
      {error && <Notice tone="bad">{error}</Notice>}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <button type="button" className={btn.plain} onClick={() => step(-1)} aria-label="Previous"><Icon name="left" size={16} /></button>
          <button type="button" className={btn.plain} onClick={() => { setAnchor(new Date()); setPicked(today); }}>Today</button>
          <button type="button" className={btn.plain} onClick={() => step(1)} aria-label="Next"><Icon name="right" size={16} /></button>
        </div>
        <h2 key={title} className="s-fade min-w-[10rem] text-lg font-semibold text-slate-800">{title}</h2>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {has("see_all") && (
            <select className={`${fieldClass} !w-auto`} value={owner} onChange={(e) => setOwner(e.target.value)} aria-label="Whose leads">
              <option value="">Everyone's leads</option>
              <option value="me">My leads</option>
              <option value="none">Not given to anyone</option>
            </select>
          )}
          <div className="flex rounded-md border border-slate-300 bg-white p-0.5">
            {[["month", "Month"], ["week", "Week"], ["day", "Day"]].map(([k, l]) => (
              <button key={k} type="button" onClick={() => { setMode(k); if (k === "day") setAnchor(parse(picked)); }} className={`rounded px-3 py-1 text-sm font-medium transition-colors ${mode === k ? "bg-indcool-blue text-white" : "text-slate-600 hover:bg-slate-100"}`}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      {loading && !data && <p className="text-sm text-slate-500">Loading...</p>}

      {late.length > 0 && (
        <div className="s-fade mb-3 rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-rose-700">Late: {late.length} follow-up{late.length === 1 ? "" : "s"} past the date. Drag onto a day to move.</div>
          <div className="mt-1 flex flex-wrap gap-x-2">{late.slice(0, 12).map((l) => <div key={l.id} className="min-w-[9rem] max-w-[14rem] flex-1"><Chip lead={l} onDragStart={dragStart} late /></div>)}</div>
          {late.length > 12 && <div className="mt-1 text-xs text-rose-700">and {late.length - 12} more. Open My day to work them.</div>}
        </div>
      )}

      {mode === "month" && (
        <div key={`m-${title}`} className="s-fade overflow-x-auto">
          <div className="grid min-w-[640px] grid-cols-7 gap-1">
            {DAYS.map((d) => <div key={d} className="px-1 text-center text-[11px] font-bold uppercase tracking-wide text-slate-500">{d}</div>)}
            {monthCells.map((d) => {
              const k = key(d);
              const items = byDay[k] || [];
              const out = d.getMonth() !== anchor.getMonth();
              return (
                <div
                  key={k}
                  onClick={() => setPicked(k)}
                  {...dropProps(k)}
                  className={`s-cell min-h-[92px] cursor-pointer rounded-lg border p-1.5 ${out ? "border-slate-100 bg-slate-50 opacity-60" : "border-slate-200 bg-white"} ${k === picked ? "ring-2 ring-indcool-blue" : ""} ${over === k ? "s-drop" : ""}`}
                >
                  <span className={`inline-grid h-6 w-6 place-items-center rounded-full text-xs font-semibold ${k === today ? "bg-indcool-blue text-white" : "text-slate-600"}`}>{d.getDate()}</span>
                  {items.slice(0, 3).map((l) => <Chip key={l.id} lead={l} onDragStart={dragStart} late={k < today} />)}
                  {items.length > 3 && <div className="mt-1 text-[11px] font-semibold text-slate-500">+{items.length - 3} more</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {mode === "week" && (
        <div key={`w-${title}`} className="s-fade overflow-x-auto">
          <div className="grid min-w-[760px] grid-cols-7 gap-2">
            {weekDays.map((d) => {
              const k = key(d);
              const items = byDay[k] || [];
              return (
                <div key={k} {...dropProps(k)} className={`s-cell min-h-[240px] rounded-lg border p-2 ${k === today ? "border-indcool-blue bg-sky-50/50" : "border-slate-200 bg-white"} ${over === k ? "s-drop" : ""}`}>
                  <button type="button" onClick={() => { setPicked(k); setAnchor(d); setMode("day"); }} className="mb-1 block w-full text-left">
                    <div className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{DAYS[(d.getDay() + 6) % 7]}</div>
                    <div className={`text-lg font-semibold ${k === today ? "text-indcool-blue" : "text-slate-800"}`}>{d.getDate()}</div>
                  </button>
                  {items.map((l) => <Chip key={l.id} lead={l} onDragStart={dragStart} late={k < today} />)}
                  {items.length === 0 && <div className="pt-6 text-center text-xs text-slate-300">free</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {mode === "day" && (
        <div key={`d-${picked}`} {...dropProps(key(anchor))} className={`s-cell rounded-lg p-1 ${over === key(anchor) ? "s-drop" : ""}`}>
          <div className="grid gap-2 lg:grid-cols-2">
            {(byDay[key(anchor)] || []).map((l, i) => <LeadRow key={l.id} lead={l} today={today} onMove={move} busy={busy} index={i} />)}
          </div>
          {(byDay[key(anchor)] || []).length === 0 && <p className="s-fade py-8 text-center text-sm text-slate-500"><Icon name="calendar" size={28} className="mb-2 block mx-auto text-slate-300" />Nothing planned for this day. Drag a lead here to plan its follow-up.</p>}
        </div>
      )}

      {mode === "month" && (
        <section className="mt-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">{longDay(parse(picked))}: {dayList.length ? `${dayList.length} follow-up${dayList.length === 1 ? "" : "s"}` : "nothing planned"}</h3>
          <div key={picked} className="grid gap-2 lg:grid-cols-2">{dayList.map((l, i) => <LeadRow key={l.id} lead={l} today={today} onMove={move} busy={busy} index={i} />)}</div>
        </section>
      )}

      {noDate.length > 0 && <p className="mt-4 text-xs text-slate-500">{noDate.length} open lead{noDate.length === 1 ? " has" : "s have"} no follow-up date yet. Log a call on them, or open one and set the next follow-up.</p>}
    </div>
  );
}
