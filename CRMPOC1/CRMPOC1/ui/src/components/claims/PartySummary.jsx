import { useEffect, useState } from "react";

import { shortageClaimsApi, RESP_LABEL } from "../../api/shortageClaims.js";

const PARTY_STYLE = {
  mfg: { bar: "border-t-blue-500", chip: "bg-blue-50 text-blue-700" },
  trans: { bar: "border-t-orange-500", chip: "bg-orange-50 text-orange-700" },
  ins: { bar: "border-t-violet-500", chip: "bg-violet-50 text-violet-700" },
};

// Totals every missing-item claim ever raised, by who it's pinned on — so admin/service-manager
// can see "how much is claimed on the manufacturer" etc. without opening each one.
export default function PartySummary({ onPick, active }) {
  const [counts, setCounts] = useState(null);

  useEffect(() => {
    let live = true;
    shortageClaimsApi.list({}).then((rows) => {
      if (!live) return;
      const c = { mfg: 0, trans: 0, ins: 0, undecided: 0, total: rows.length };
      for (const r of rows) {
        if (r.responsible_type && c[r.responsible_type] != null) c[r.responsible_type] += 1;
        else c.undecided += 1;
      }
      setCounts(c);
    }).catch(() => setCounts(null));
    return () => { live = false; };
  }, []);

  if (!counts || counts.total === 0) return null;

  return (
    <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
      {["mfg", "trans", "ins"].map((k) => (
        <button
          key={k}
          type="button"
          onClick={() => onPick?.(active === k ? "" : k)}
          className={`rounded-lg border-t-[3px] bg-white p-2.5 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${PARTY_STYLE[k].bar} ${active === k ? "ring-2 ring-offset-1 ring-indcool-navy/30" : ""}`}
        >
          <div className="text-xl font-extrabold tabular-nums text-slate-800">{counts[k]}</div>
          <div className={`mt-0.5 inline-block rounded-full px-1.5 py-0.5 text-[11px] font-semibold ${PARTY_STYLE[k].chip}`}>Claimed on {RESP_LABEL[k]}</div>
        </button>
      ))}
      <div className="rounded-lg border-t-[3px] border-t-slate-300 bg-white p-2.5 shadow-sm">
        <div className="text-xl font-extrabold tabular-nums text-slate-500">{counts.undecided}</div>
        <div className="mt-0.5 text-[11px] font-semibold text-slate-500">Not yet decided</div>
      </div>
    </div>
  );
}
