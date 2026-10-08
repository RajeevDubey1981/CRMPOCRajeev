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
export default function PlaceFields({ value, onChange, disabled = false, className = "", multiPin = false }) {
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
      {multiPin && (
        <div className="sm:col-span-3">
          <PinCodeChips
            label="Other pin codes this engineer also works in"
            value={value?.extra_pincodes || []}
            onChange={(list) => onChange({ extra_pincodes: list })}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
}

/** Several pin codes as small tags: type or paste them (comma, space or Enter between), click x to remove one. */
export function PinCodeChips({ value, onChange, label, disabled = false, max = 30 }) {
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");
  const list = value || [];

  // adds every good pin code; what is not a 6 digit pin code is returned so it stays in the box
  function add(raw) {
    const parts = String(raw || "").split(/[\s,;]+/).filter(Boolean);
    const next = [...list];
    const left = [];
    for (const part of parts) {
      if (!/^[1-9]\d{5}$/.test(part)) left.push(part);
      else if (!next.includes(part)) next.push(part);
    }
    if (next.length > max) {
      setProblem(`At most ${max} pin codes`);
      return String(raw);
    }
    setProblem(left.length ? `"${left.join(", ")}" is not a 6 digit pin code` : "");
    if (next.length !== list.length) onChange(next);
    return left.join(" ");
  }

  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1.5">
        {list.map((pin) => (
          <span key={pin} className="inline-flex items-center gap-1 rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-900">
            {pin}
            {!disabled && (
              <button type="button" onClick={() => onChange(list.filter((p) => p !== pin))} className="text-sky-700 hover:text-rose-600" aria-label={`Remove ${pin}`}>x</button>
            )}
          </span>
        ))}
        <input
          inputMode="numeric"
          disabled={disabled}
          value={text}
          onChange={(e) => {
            const v = e.target.value.replace(/[^\d\s,;]/g, "");
            if (/[\s,;]$/.test(v)) setText(add(v));
            else setText(v);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); setText(add(text)); }
            else if (e.key === "Backspace" && text === "" && list.length) onChange(list.slice(0, -1));
          }}
          onBlur={() => { if (text.trim()) setText(add(text)); }}
          placeholder={list.length ? "Add another" : "Type a pin code, then Enter"}
          className="min-w-[8rem] flex-1 border-0 bg-transparent px-1 py-0.5 text-sm outline-none"
        />
      </div>
      {problem ? <p className="mt-1 text-xs text-rose-700">{problem}</p> : <p className="mt-1 text-xs text-slate-500">Use this when the engineer also covers nearby pin codes. You can paste many at once.</p>}
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
