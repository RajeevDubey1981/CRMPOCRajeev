import { INSTALLATION_STAGES } from "../../utils/installationStages.js";

/** One chip per stage with its count, plus an optional "Needs Service Team" chip (a different axis --
 * whether assigned_service_user_id is set, not a status -- so it isn't one of INSTALLATION_STAGES and is
 * passed in separately). Click one to filter, click it again to clear. */
export default function InstallationStageChips({ counts, value, onChange, needsServiceTeamCount, needsServiceTeamActive, onToggleNeedsServiceTeam }) {
  const total = INSTALLATION_STAGES.reduce((sum, s) => sum + (counts?.[s.key] || 0), 0);
  const showNeedsServiceTeam = typeof onToggleNeedsServiceTeam === "function";
  return (
    <div>
      <div className="mb-1.5 text-xs text-slate-500">Stage (click to filter, click again to clear)</div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onChange("")}
          className={`min-w-[88px] rounded-lg border-t-[3px] px-3 py-1.5 text-left transition ${!value ? "border border-t-[3px] border-violet-500 bg-violet-50 text-violet-900" : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}
          style={{ borderTopColor: "#94a3b8" }}
        >
          <span className="block text-xl font-semibold leading-tight">{total}</span>
          <span className="text-[11px] text-slate-500">All</span>
        </button>
        {INSTALLATION_STAGES.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={() => onChange(value === s.key ? "" : s.key)}
            className={`min-w-[88px] rounded-lg px-3 py-1.5 text-left transition ${value === s.key ? "border border-violet-500 bg-violet-50 text-violet-900" : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}
            style={{ borderTopWidth: 3, borderTopColor: s.color }}
          >
            <span className="block text-xl font-semibold leading-tight">{counts?.[s.key] ?? 0}</span>
            <span className="text-[11px] text-slate-500">{s.label}</span>
          </button>
        ))}
        {showNeedsServiceTeam && (
          <button
            type="button"
            onClick={onToggleNeedsServiceTeam}
            title="Serial verified by the engineer, but nobody on the Service Team has been assigned yet"
            className={`relative min-w-[88px] rounded-lg border-t-[4px] px-3 py-1.5 text-left transition ${needsServiceTeamActive ? "border border-t-[4px] border-rose-500 bg-rose-50 text-rose-900" : "border border-slate-200 bg-white text-rose-700 hover:bg-rose-50"}`}
            style={{ borderTopColor: "#D64545" }}
          >
            <span className="block text-xl font-semibold leading-tight">{needsServiceTeamCount ?? 0}</span>
            <span className="text-[11px] text-slate-500">Needs Service Team</span>
          </button>
        )}
      </div>
    </div>
  );
}
