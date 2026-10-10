import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, SalesTabs, fmtDateTime, useAsync } from "./salesUi.jsx";

export default function SalesLog() {
  const { data, loading, error } = useAsync(() => salesApi.inboxLog(), []);
  return (
    <div>
      <PageTitle title="Registered first, then lead" sub="Everything the CRM registered that Sales picked up, newest first. The CRM number is the one the CRM made." />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">When</th><th className="px-3 py-2">Source</th><th className="px-3 py-2">CRM number</th><th className="px-3 py-2">What happened</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {(data || []).map((r, i) => (
              <tr key={i}>
                <td className="whitespace-nowrap px-3 py-2">{fmtDateTime(r.at)}</td>
                <td className="px-3 py-2">{r.source}</td>
                <td className="px-3 py-2 font-semibold">{r.crm_ref || "—"}</td>
                <td className="px-3 py-2">{r.lead_id ? <Link className="text-indcool-blue hover:underline" to={`/sales/leads/${r.lead_id}`}>{r.result}</Link> : r.result}</td>
              </tr>
            ))}
            {!loading && (data || []).length === 0 && <tr><td colSpan={4} className="px-3 py-8 text-center text-slate-500">Nothing yet. New Sales enquiries and partner registrations appear here a minute after the CRM registers them.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
