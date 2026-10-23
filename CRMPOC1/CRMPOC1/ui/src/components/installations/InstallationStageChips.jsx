import { INSTALLATION_STAGES } from "../../utils/installationStages.js";

/** One chip per stage with its count. Click one to filter, click it again to clear. */
export default function InstallationStageChips({ counts, value, onChange }) {
  const total = INSTALLATION_STAGES.reduce((sum, s) => sum + (counts?.[s.key] || 0), 0);
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
      </div>
    </div>
  );
}
