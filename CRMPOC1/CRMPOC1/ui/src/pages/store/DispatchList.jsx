import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import { storeApi, storeError } from "../../api/store.js";

export const STAGE_BADGE = {
  "Needs stock": "bg-rose-100 text-rose-800",
  "Waiting for bill": "bg-amber-100 text-amber-800",
  "Ready to dispatch": "bg-sky-100 text-sky-800",
  Dispatched: "bg-emerald-100 text-emerald-800",
};

const STAGES = ["Needs stock", "Waiting for bill", "Ready to dispatch", "Dispatched"];

export default function DispatchList() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const stage = params.get("stage") || "";
  const [data, setData] = useState({ items: [], total: 0, counts: {} });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const query = useMemo(() => ({ stage: stage || undefined, search: search || undefined, page, per_page: perPage }), [stage, search, page, perPage]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setErr("");
    storeApi.listOrders(query)
      .then((d) => { if (live) setData(d); })
      .catch((e) => { if (live) setErr(storeError(e, "Failed to load orders")); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [query]);

  function pick(value) {
    setPage(1);
    if (value) setParams({ stage: value }); else setParams({});
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Dispatch</h1>
        <p className="text-sm text-slate-500">Orders shipped from our own store. Stock is reserved oldest first, and nothing leaves without a bill number.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {STAGES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => pick(stage === s ? "" : s)}
            className={`rounded-lg border px-4 py-3 text-left shadow-sm ${stage === s ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-white hover:bg-slate-50"}`}
          >
            <div className="text-2xl font-semibold text-slate-800">{data.counts?.[s] ?? 0}</div>
            <div className="text-sm text-slate-600">{s}</div>
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <input
          type="text"
          placeholder="Search order, customer, city or bill no"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-80"
        />
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Order</th>
              <th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">City</th>
              <th className="px-3 py-2 text-right">Units</th>
              <th className="px-3 py-2 text-right">Reserved</th>
              <th className="px-3 py-2">Bill no</th>
              <th className="px-3 py-2">Stage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No store orders here. Create an order and choose "Our store" as the place it ships from.</td></tr>
            )}
            {!loading && data.items.map((o) => (
              <tr key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/store/dispatch/${o.id}`)}>
                <td className="px-3 py-2 font-mono text-xs font-bold text-slate-800">{o.order_no || `#${o.id}`}</td>
                <td className="px-3 py-2">{o.customer_name || "-"}</td>
                <td className="px-3 py-2 text-slate-600">{o.customer_city || "-"}</td>
                <td className="px-3 py-2 text-right">{o.units}</td>
                <td className="px-3 py-2 text-right">{o.held}</td>
                <td className="px-3 py-2 font-mono text-xs">{o.oem_bill_no || "-"}</td>
                <td className="px-3 py-2"><span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${STAGE_BADGE[o.stage] || "bg-slate-100"}`}>{o.stage}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} perPage={perPage} total={data.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
    </div>
  );
}
