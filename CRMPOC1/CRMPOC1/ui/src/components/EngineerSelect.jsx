import { useMemo, useState } from "react";

import { INDIAN_STATES } from "../constants/indianStates.js";
import { districtsOf, sameDistrict } from "../constants/indianDistricts.js";
import { formatEngineerOptionLabel } from "../utils/engineerAssignment.js";

const smallClass = "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs";

/**
 * The "choose an engineer" box with a search by pin code, state and district above it.
 * Searching only narrows the list; the engineer already chosen always stays in it.
 * onChange gets the select's change event, as the plain <select> it replaces did.
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
  const shown = useMemo(() => {
    if (!searching) return list;
    return list.filter((e) => {
      if (String(e.id) === String(value)) return true;
      if (pin && ![e.pincode, ...(e.extra_pincodes || [])].some((p) => (p || "").startsWith(pin))) return false;
      if (state && e.state !== state) return false;
      if (district && !sameDistrict(e.district, district)) return false;
      return true;
    });
  }, [list, searching, pin, state, district, value]);

  const districts = districtsOf(state);
  const clear = () => { setPin(""); setState(""); setDistrict(""); };

  return (
    <div className={className}>
      <div className="mb-2 grid grid-cols-1 gap-2 rounded-md border border-sky-200 bg-sky-50 p-2 sm:grid-cols-3">
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
        {searching && (
          <div className="flex items-center justify-between text-xs text-sky-900 sm:col-span-3">
            <span>
              {shown.length === 0 ? "No engineer works in this area." : `Showing ${shown.length} of ${list.length} engineers.`}
            </span>
            <button type="button" onClick={clear} className="font-medium underline">Clear search</button>
          </div>
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
