import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { servicesApi } from "../api/services.js";
import { fmtIST } from "../utils/time.js";

// Loud banner for the service manager: service requests a service user has handed back and nobody has
// picked up again yet. It is hidden when there are none (and for roles that cannot see the filter).
export default function ReturnedServicesAlert() {
  const [data, setData] = useState({ total: 0, items: [] });

  useEffect(() => {
    let active = true;
    const load = () =>
      servicesApi
        .list({ returned: true, per_page: 20 })
        .then((r) => { if (active) { const rows = (r.items || []).filter((i) => i.returned_by_name); setData({ total: rows.length ? r.total || rows.length : 0, items: rows }); }; })
        .catch(() => { if (active) setData({ total: 0, items: [] }); });
    load();
    const timer = setInterval(load, 60000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  if (!data.total) return null;

  return (
    <div className="overflow-hidden rounded-xl border-2 border-rose-500 bg-rose-50 shadow-lg shadow-rose-200/60 ring-4 ring-rose-200/70" role="alert">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-rose-600 px-4 py-3 text-white">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3.5 w-3.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
            <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-white" />
          </span>
          <div>
            <div className="text-base font-bold uppercase tracking-wide">
              {data.total} service request{data.total === 1 ? "" : "s"} returned: reassign now
            </div>
            <div className="text-xs text-rose-100">A service user handed these back. Nobody is working on them until you assign them again.</div>
          </div>
        </div>
        <Link to="/services?service_user=returned" className="rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-rose-700 hover:bg-rose-100">
          Open all returned
        </Link>
      </div>
      <ul className="divide-y divide-rose-200">
        {data.items.slice(0, 5).map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-semibold text-slate-800">{s.request_no}</span>
                <span className="text-sm text-slate-700">{s.customer_name}</span>
                {s.complaint_no && <span className="font-mono text-xs text-slate-500">{s.complaint_no}</span>}
              </div>
              <div className="mt-0.5 text-sm text-rose-800">
                Returned by <b>{s.returned_by_name || "a service user"}</b>
                {s.returned_at ? <span className="text-rose-600"> &middot; {fmtIST(s.returned_at, "String")}</span> : null}
                {s.returned_reason ? <span>: &ldquo;{s.returned_reason}&rdquo;</span> : null}
              </div>
            </div>
            <Link to={`/services/${s.id}`} className="shrink-0 rounded-md bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-rose-700">
              Reassign
            </Link>
          </li>
        ))}
      </ul>
      {data.total > 5 && <div className="bg-rose-100 px-4 py-2 text-xs text-rose-700">and {data.total - 5} more. Use &ldquo;Open all returned&rdquo;.</div>}
    </div>
  );
}
