import { Link } from "react-router-dom";
import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, QUOTE_TONE, SalesTabs, fieldClass, fmtDate, useAsync, useSales } from "./salesUi.jsx";

export default function QuotationList() {
  const { has } = useSales();
  const [filter, setFilter] = useState(has("approve_quote") ? "waiting" : "");
  const { data, loading, error } = useAsync(() => salesApi.quotations({ status: filter }), [filter]);
  return (
    <div>
      <PageTitle title="Quotations" sub="Made from a lead. The Sales Manager approves; a discount above the limit also needs Admin or Sub Admin." right={
        <select className={`${fieldClass} !w-auto`} value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All</option><option value="waiting">Waiting for approval</option><option value="draft">Draft</option><option value="ret">Returned</option>
          <option value="appr">Approved, not sent</option><option value="sent">Sent</option><option value="acc">Accepted</option><option value="rej">Rejected</option>
        </select>
      } />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Number</th><th className="px-3 py-2">Customer</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Status</th><th className="px-3 py-2 text-right">Total</th><th className="px-3 py-2 text-right">Discount</th><th className="px-3 py-2">Made</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {(data || []).map((q) => (
              <tr key={q.id} className="hover:bg-sky-50/40">
                <td className="px-3 py-2"><Link to={`/sales/quotations/${q.id}`} className="font-semibold text-indcool-navy hover:underline">{q.quote_no}</Link></td>
                <td className="px-3 py-2">{q.party}</td>
                <td className="px-3 py-2">{q.currency === "USD" ? "Export (US$)" : "India (₹)"}</td>
                <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${QUOTE_TONE[q.status]}`}>{q.status_label}</span>{q.high_discount && ["wait", "wadm"].includes(q.status) && <span className="ml-1 text-[11px] font-semibold text-orange-700">high discount</span>}</td>
                <td className="px-3 py-2 text-right tabular-nums">{q.currency === "USD" ? "US$" : "₹"} {q.total.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="px-3 py-2 text-right tabular-nums">{q.discount_pct}%</td>
                <td className="px-3 py-2">{fmtDate(q.created_at)}</td>
              </tr>
            ))}
            {!loading && (data || []).length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">No quotation here. Open a lead and press "Make a quotation".</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
