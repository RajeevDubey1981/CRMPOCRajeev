import { useEffect, useState } from "react";

import { INDIAN_STATES } from "../constants/indianStates.js";
import { districtsOf } from "../constants/indianDistricts.js";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";
const OTHER = "__other__";

/**
 * Pin code, State and District. Choosing a state fills the District list with that state's districts;
 * a district that is not in the list can be typed with "Other (type it)".
 * value = { pincode, state, district }, onChange(patch) gets only what changed.
 */
export default function PlaceFields({ value, onChange, disabled = false, className = "" }) {
  const pincode = value?.pincode || "";
  const state = value?.state || "";
  const district = value?.district || "";
  const list = districtsOf(state);
  const notInList = district !== "" && !list.some((d) => d.toLowerCase() === district.toLowerCase());
  const [typing, setTyping] = useState(false);
  const showTyped = typing || notInList || (state !== "" && list.length === 0);

  useEffect(() => {
    // a different state means a different list: go back to picking
    setTyping(false);
  }, [state]);

  return (
    <div className={`grid grid-cols-1 gap-3 sm:grid-cols-3 ${className}`}>
      <div>
        <label className={labelClass}>Pin code</label>
        <input
          inputMode="numeric"
          maxLength={6}
          disabled={disabled}
          value={pincode}
          onChange={(e) => onChange({ pincode: e.target.value.replace(/\D/g, "") })}
          placeholder="6 digits"
          className={fieldClass}
        />
      </div>
      <div>
        <label className={labelClass}>State</label>
        <select
          disabled={disabled}
          value={state}
          onChange={(e) => onChange({ state: e.target.value, district: "" })}
          className={fieldClass}
        >
          <option value="">Choose the state</option>
          {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div>
        <label className={labelClass}>District</label>
        {showTyped ? (
          <div className="flex gap-2">
            <input
              disabled={disabled}
              value={district}
              onChange={(e) => onChange({ district: e.target.value })}
              placeholder="Type the district"
              className={fieldClass}
            />
            {list.length > 0 && (
              <button
                type="button"
                disabled={disabled}
                onClick={() => { setTyping(false); onChange({ district: "" }); }}
                className="shrink-0 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-600 hover:bg-slate-50"
                title="Choose from the list again"
              >
                List
              </button>
            )}
          </div>
        ) : (
          <select
            disabled={disabled || !state}
            value={district}
            onChange={(e) => {
              if (e.target.value === OTHER) { setTyping(true); onChange({ district: "" }); } else onChange({ district: e.target.value });
            }}
            className={fieldClass}
          >
            <option value="">{state ? "Choose the district" : "Choose the state first"}</option>
            {list.map((d) => <option key={d} value={d}>{d}</option>)}
            {state && <option value={OTHER}>Other (type it)</option>}
          </select>
        )}
      </div>
    </div>
  );
}

export const emptyPlace = { pincode: "", state: "", district: "" };

/** Pin code / state / district ready for the API: empty boxes become "" so an old value is cleared. */
export function placeForApi(place) {
  return {
    pincode: (place?.pincode || "").trim(),
    state: place?.state || "",
    district: (place?.district || "").trim(),
  };
}

/** Message when the pin code is typed but not 6 digits, else "". */
export function placeProblem(place) {
  const pin = (place?.pincode || "").trim();
  return pin && !/^[1-9]\d{5}$/.test(pin) ? "Pin code must be 6 digits and cannot start with 0." : "";
}
