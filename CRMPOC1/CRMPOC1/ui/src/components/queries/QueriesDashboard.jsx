import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { partsApi } from "../../api/parts.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { CountUp } from "../../pages/sales/salesUi.jsx";

const APPROVAL_ROLES = new Set(["admin", "incool", "sub_admin", "service_manager", "service", "indcool", "indcool service", "indcool_service"]);

// The tiles above the Queries list. A tile filters the list; the cards below filter it by kind or by person.
export const TILES = [
  { key: "new", label: "New", sub: "Not opened by you yet", color: "#2563eb", count: "new", icon: '<path d="M12 5v14M5 12h14"/>' },
  { key: "active", label: "Active", sub: "Not closed", color: "#0891b2", count: "active", icon: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>' },
  { key: "waiting", label: "Waiting for reply", sub: "Waiting for an answer", color: "#b45309", count: "waiting", icon: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>' },
  { key: "late", label: "No reply in 24 h", sub: "The alarm is ringing", color: "#c62839", count: "late", icon: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M10.3 21a1.9 1.9 0 0 0 3.4 0"/>' },
  { key: "priority", label: "High and urgent", sub: "Marked by the Admin team", color: "#ea580c", count: "priority", icon: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>' },
  { key: "done", label: "Answered and closed", sub: "Done", color: "#0b7a4b", count: "done", icon: '<path d="m5 12 4.5 4.5L19 7"/>' },
];

const initials = (n) => String(n || "").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

function Week({ week }) {
  const W = 420, H = 130, L = 22, B = 20, T = 8;
  const max = Math.max(4, ...week.opened, ...week.solved);
  const top = Math.ceil(max / 4) * 4;
  const x = (i) => L + i * ((W - L - 8) / 6);
  const y = (v) => T + (H - T - B) * (1 - v / top);
  const path = (s) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Queries opened and solved in the last 7 days">
      {[0, top / 2, top].map((v) => (
        <g key={v}><line x1={L} x2={W - 8} y1={y(v)} y2={y(v)} stroke="#eef2f7" /><text x={L - 5} y={y(v) + 3} textAnchor="end" fontSize="10" fill="#64748b">{v}</text></g>
      ))}
      {week.days.map((d, i) => <text key={`${d}${i}`} x={x(i)} y={H - 5} textAnchor="middle" fontSize="10" fill="#64748b">{d}</text>)}
      <path d={`${path(week.opened)} L${x(6)} ${y(0)} L${x(0)} ${y(0)}Z`} fill="#2563eb" opacity=".13" className="s-fade" />
      <path d={path(week.opened)} fill="none" stroke="#2563eb" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" pathLength="400" strokeDasharray="400" strokeDashoffset="400" style={{ animation: "s-draw 1.3s ease forwards .4s" }} />
      <path d={path(week.solved)} fill="none" stroke="#0b7a4b" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" pathLength="400" strokeDasharray="400" strokeDashoffset="400" style={{ animation: "s-draw 1.3s ease forwards .8s" }} />
    </svg>
  );
}

export default function QueriesDashboard({ data, tile, onTile, kind, onKind, holder, onHolder }) {
  const [grow, setGrow] = useState(false);
  const [approvalsCount, setApprovalsCount] = useState(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const canSeeApprovals = APPROVAL_ROLES.has((user?.role || "").trim().toLowerCase());

  useEffect(() => { const t = setTimeout(() => setGrow(true), 150); return () => clearTimeout(t); }, []);
  useEffect(() => {
    if (!canSeeApprovals) return;
    let live = true;
    partsApi.requests({ mine: true }).then((rows) => {
      if (!live) return;
      setApprovalsCount(rows.filter((r) => r.stage === "svm" || r.stage === "sub").length);
    }).catch(() => { if (live) setApprovalsCount(null); });
    return () => { live = false; };
  }, [canSeeApprovals]);

  if (!data) return <div className="h-24 rounded-lg bg-white/60 shadow-sm" aria-hidden="true" />;
  const t = data.tiles;
  const kmax = Math.max(1, ...data.by_kind.map((r) => r.count));
  return (
    <div className="space-y-3">
      <div className={`grid grid-cols-2 gap-3 sm:grid-cols-3 ${canSeeApprovals ? "xl:grid-cols-7" : "xl:grid-cols-6"}`}>
        {TILES.map((x, i) => {
          const n = t[x.count] ?? 0;
          const alarm = x.key === "late" && n > 0;
          return (
            <button
              key={x.key}
              type="button"
              onClick={() => onTile(tile === x.key ? "" : x.key)}
              aria-pressed={tile === x.key}
              style={{ "--i": i, "--c": x.color, borderColor: tile === x.key ? x.color : "transparent" }}
              className="s-rise s-lift s-press relative overflow-hidden rounded-xl border-2 bg-white p-3.5 text-left shadow-sm"
            >
              <span style={{ "--i": i, background: x.color }} className="s-grow absolute inset-x-0 top-0 h-1.5" />
              <span className={`absolute right-3 top-4 grid h-7 w-7 place-items-center rounded-full ${alarm ? "q-bell" : ""}`} style={{ background: `${x.color}22`, color: x.color }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" dangerouslySetInnerHTML={{ __html: x.icon }} />
              </span>
              <div className={`mt-1 text-[30px] font-extrabold leading-tight tabular-nums ${alarm ? "text-rose-600" : "text-slate-800"}`}><CountUp value={n} /></div>
              <div className="text-sm font-bold text-slate-800">{x.label}</div>
              <div className="text-[11px] text-slate-500">{x.key === "late" && t.late_for_me > 0 ? `${t.late_for_me} for you to answer` : x.sub}</div>
            </button>
          );
        })}
        {canSeeApprovals && (
          <button
            type="button"
            onClick={() => navigate("/approvals?tab=parts")}
            style={{ "--i": TILES.length, "--c": "#7c3aed", borderColor: "transparent" }}
            className="s-rise s-lift s-press relative overflow-hidden rounded-xl border-2 bg-white p-3.5 text-left shadow-sm q-approvals-pulse"
          >
            <span style={{ "--i": TILES.length, background: "#7c3aed" }} className="s-grow absolute inset-x-0 top-0 h-1.5" />
            <span className="absolute right-3 top-4 grid h-7 w-7 place-items-center rounded-full" style={{ background: "#7c3aed22", color: "#7c3aed" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
            </span>
            <div className="mt-1 text-[30px] font-extrabold leading-tight tabular-nums text-violet-700"><CountUp value={approvalsCount ?? 0} /></div>
            <div className="text-sm font-bold text-slate-800">Approvals</div>
            <div className="text-[11px] text-slate-500">Parts waiting on a decision</div>
          </button>
        )}
      </div>

      <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_1fr]">
        <div className="s-rise rounded-xl bg-white p-3.5 shadow-sm" style={{ "--i": 6 }}>
          <h3 className="mb-2 text-xs font-bold tracking-wide text-slate-500">OPENED AND SOLVED, LAST 7 DAYS</h3>
          <Week week={data.week} />
          <div className="mt-1 flex flex-wrap gap-4 text-xs">
            <span className="text-blue-600">● Opened</span><span className="text-emerald-700">● Solved</span>
            {data.first_answer_hours != null && <span className="ml-auto text-slate-500">First answer takes {data.first_answer_hours < 1 ? "under an hour" : `${data.first_answer_hours} h`} on average</span>}
          </div>
        </div>

        <div className="s-rise rounded-xl bg-white p-3.5 shadow-sm" style={{ "--i": 7 }}>
          <h3 className="mb-2 text-xs font-bold tracking-wide text-slate-500">ACTIVE, BY KIND</h3>
          {data.by_kind.length === 0 ? <p className="text-sm text-slate-500">Nothing active.</p> : (
            <div className="space-y-2.5">
              {data.by_kind.slice(0, 6).map((r) => (
                <button key={r.kind} type="button" onClick={() => onKind(kind === r.kind ? "" : r.kind)} className="block w-full rounded-md p-1 text-left hover:bg-slate-50">
                  <div className="mb-1 flex justify-between text-xs"><span className={kind === r.kind ? "font-bold text-indcool-navy" : ""}>{r.kind}</span><b className="tabular-nums">{r.count}</b></div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indcool-blue transition-all duration-1000" style={{ width: grow ? `${(r.count / kmax) * 100}%` : 0 }} /></div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="s-rise rounded-xl bg-white p-3.5 shadow-sm" style={{ "--i": 8 }}>
          <h3 className="mb-2 text-xs font-bold tracking-wide text-slate-500">WAITING FOR WHOM</h3>
          {data.by_holder.length === 0 ? <p className="text-sm text-slate-500">Nobody is waiting.</p> : (
            <div className="space-y-1">
              {data.by_holder.map((h) => (
                <button key={h.name} type="button" onClick={() => onHolder(holder === h.name ? "" : h.name)} className={`flex w-full items-center gap-2.5 rounded-md p-1.5 text-left hover:bg-slate-50 ${holder === h.name ? "bg-sky-50" : ""}`}>
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-blue-100 text-[11px] font-extrabold text-blue-800">{initials(h.name)}</span>
                  <span className="min-w-0 flex-1 truncate text-sm">{h.name}<span className="block text-[11px] text-slate-500">{h.waiting} waiting</span></span>
                  {h.late > 0 ? <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-700">{h.late} late</span> : <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">on time</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
