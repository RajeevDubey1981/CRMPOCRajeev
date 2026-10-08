import { useMemo, useState } from "react";

import { INDIAN_STATES } from "../constants/indianStates.js";
import { districtsOf, sameDistrict } from "../constants/indianDistricts.js";
import { formatEngineerOptionLabel } from "../utils/engineerAssignment.js";

const smallClass = "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs";

const TAG_STYLE = {
  "Same pin code": "bg-emerald-600 text-white",
  "Pin code starts alike": "bg-emerald-500 text-white",
  "Same area": "bg-sky-600 text-white",
  "Same district": "bg-indigo-600 text-white",
  "Same state": "bg-slate-600 text-white",
};

function pinsOf(engineer) {
  return [engineer.pincode, ...(engineer.extra_pincodes || [])].filter(Boolean);
}

/**
 * How well an engineer fits what was typed in the three search boxes, or null when the engineer does not fit.
 * Lower rank is nearer: same pin code, pin code starting with the digits typed, same area (first 3 digits),
 * then district and state alone.
 */
function fit(engineer, pin, state, district) {
  let rank = 9;
  let tag = "";
  if (pin) {
    const pins = pinsOf(engineer);
    if (pins.includes(pin)) { rank = 0; tag = "Same pin code"; }
    else if (pins.some((p) => p.startsWith(pin))) { rank = 1; tag = "Pin code starts alike"; }
    else if (pin.length >= 3 && pins.some((p) => p.slice(0, 3) === pin.slice(0, 3))) { rank = 2; tag = "Same area"; }
    else return null;
  }
  if (state && engineer.state !== state) return null;
  if (district && !sameDistrict(engineer.district, district)) return null;
  if (!tag) {
    if (district) { rank = 3; tag = "Same district"; }
    else if (state) { rank = 4; tag = "Same state"; }
  }
  return { rank, tag };
}

/**
 * The "choose an engineer" box with a search by pin code, state and district above it.
 * As soon as something is typed or chosen, the engineers who fit show right below, nearest first, each with the
 * rating and the pending jobs: one click picks one. The drop-down underneath stays, narrowed the same way.
 * onChange gets a change-like event ({ target: { value } }), as the plain <select> it replaces did.
 */
export default function EngineerSelect({
  engineers,
  value,
  onChange,
  disabled = false,
  emptyLabel = "Select engineer",
  selectClassName = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500",
  className = "",
}) {
  const [pin, setPin] = useState("");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");

  const list = engineers || [];
  const searching = pin !== "" || state !== "" || district !== "";
  const ranked = useMemo(() => {
    if (!searching) return [];
    return list
      .map((engineer) => ({ engineer, hit: fit(engineer, pin, state, district) }))
      .filter((row) => row.hit)
      .sort((a, b) => (
        a.hit.rank - b.hit.rank
        || Number(a.engineer.pending_requests ?? 0) - Number(b.engineer.pending_requests ?? 0)
        || Number(b.engineer.rating ?? 0) - Number(a.engineer.rating ?? 0)
        || String(a.engineer.name).localeCompare(String(b.engineer.name))
      ));
  }, [list, searching, pin, state, district]);

  const shown = useMemo(() => {
    if (!searching) return list;
    const ids = new Set(ranked.map((row) => String(row.engineer.id)));
    const picked = list.filter((e) => String(e.id) === String(value) && !ids.has(String(e.id)));
    return [...ranked.map((row) => row.engineer), ...picked];
  }, [list, searching, ranked, value]);

  const districts = districtsOf(state);
  const clear = () => { setPin(""); setState(""); setDistrict(""); };
  const pick = (id) => onChange?.({ target: { value: String(id) } });

  return (
    <div className={className}>
      <div className="mb-2 space-y-2 rounded-md border border-sky-200 bg-sky-50 p-2">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <input
            inputMode="numeric"
            maxLength={6}
            value={pin}
            disabled={disabled}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            placeholder="Search by pin code"
            className={smallClass}
          />
          <select value={state} disabled={disabled} onChange={(e) => { setState(e.target.value); setDistrict(""); }} className={smallClass}>
            <option value="">Search by state</option>
            {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={district} disabled={disabled || !state} onChange={(e) => setDistrict(e.target.value)} className={smallClass}>
            <option value="">{state ? "Search by district" : "Choose a state for districts"}</option>
            {districts.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        {searching && (
          <>
            <div className="flex items-center justify-between text-xs text-sky-900">
              <span>
                {ranked.length === 0 ? "No engineer works in this area." : `${ranked.length} of ${list.length} engineers match, nearest first.`}
              </span>
              <button type="button" onClick={clear} className="font-medium underline">Clear search</button>
            </div>
            {ranked.length > 0 && (
              <ul className="max-h-56 space-y-1 overflow-y-auto" aria-label="Matching engineers">
                {ranked.map(({ engineer, hit }) => {
                  const chosen = String(engineer.id) === String(value);
                  const rating = Number(engineer.rating ?? 0);
                  return (
                    <li key={engineer.id}>
                      <button
                        type="button"
                        disabled={disabled}
                        onClick={() => pick(engineer.id)}
                        className={`flex w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-md border px-2 py-1.5 text-left text-xs transition ${
                          chosen ? "border-emerald-500 bg-emerald-50" : "border-slate-200 bg-white hover:border-sky-400 hover:bg-sky-50"
                        }`}
                      >
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${TAG_STYLE[hit.tag] || "bg-slate-500 text-white"}`}>{hit.tag}</span>
                        <span className="text-sm font-medium text-slate-800">{engineer.name}</span>
                        <span className="text-slate-500">
                          {[engineer.district, engineer.state, pinsOf(engineer).join("/")].filter(Boolean).join(", ")}
                        </span>
                        <span className="ml-auto flex items-center gap-2 whitespace-nowrap">
                          <span className="font-semibold text-amber-600" title="Rating">★ {rating.toFixed(1)}/5</span>
                          <span className="text-slate-600" title="Active jobs">Pending {Number(engineer.pending_requests ?? 0)}</span>
                          {chosen && <span className="font-semibold text-emerald-700">✓ Chosen</span>}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
      </div>
      <select value={value} onChange={onChange} disabled={disabled} className={selectClassName}>
        <option value="">{emptyLabel}</option>
        {shown.map((engineer) => (
          <option key={engineer.id} value={engineer.id}>{formatEngineerOptionLabel(engineer)}</option>
        ))}
      </select>
    </div>
  );
}
