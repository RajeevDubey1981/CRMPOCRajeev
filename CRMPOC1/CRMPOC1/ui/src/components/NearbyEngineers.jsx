import { useEffect, useState } from "react";

import { installationsApi } from "../api/installations.js";
import { ENGINEER_MATCH_TEXT } from "../utils/engineerAssignment.js";

/**
 * "Engineers near this address": shown on the new complaint / installation / service forms as soon as a pin code,
 * state or district is chosen. Only engineers who work in the same pin code, area, district or state are listed.
 */
export default function NearbyEngineers({ place, address }) {
  const [rows, setRows] = useState(null);
  const pincode = (place?.pincode || "").trim();
  const state = place?.state || "";
  const district = (place?.district || "").trim();
  const ready = /^[1-9]\d{5}$/.test(pincode) || state !== "" || district !== "";

  useEffect(() => {
    if (!ready) { setRows(null); return undefined; }
    let cancelled = false;
    const timer = setTimeout(() => {
      installationsApi
        .engineerAssignmentOptions(address, { pincode: /^[1-9]\d{5}$/.test(pincode) ? pincode : "", state, district })
        .then((data) => { if (!cancelled) setRows(data.filter((e) => e.match)); })
        .catch(() => { if (!cancelled) setRows(null); });
    }, 400);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [ready, pincode, state, district, address]);

  if (!ready || rows === null) return null;
  return (
    <div className="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm">
      <div className="mb-1 font-medium text-sky-900">Engineers near this address</div>
      {rows.length === 0 ? (
        <p className="text-amber-800">No engineer is registered for this area yet.</p>
      ) : (
        <ul className="space-y-1">
          {rows.slice(0, 5).map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-x-2 text-slate-800">
              <span className="rounded bg-sky-600 px-1.5 py-0.5 text-xs font-medium text-white">{ENGINEER_MATCH_TEXT[e.match]}</span>
              <span className="font-medium">{e.name}</span>
              <span className="text-xs text-slate-600">{[e.district, e.state, e.pincode].filter(Boolean).join(", ")}</span>
              <span className="text-xs text-slate-500">Pending: {e.pending_requests}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
