import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { storeApi, storeError } from "../../api/store.js";

export const GRN_BADGE = {
  Draft: "bg-slate-100 text-slate-700",
  "Pending Approval": "bg-amber-100 text-amber-800",
  Posted: "bg-emerald-100 text-emerald-800",
};

export function fmtDateTime(s) {
  if (!s) return "-";
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

const TABS = [
  ["", "All"],
  ["Pending Approval", "Waiting for approval"],
  ["Draft", "Drafts"],
  ["Posted", "Posted"],
];

export default function GrnList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const canCreate = hasPermission(user, "store_receiving", "can_create");
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const statusFilter = params.get("status") || "";

  const query = useMemo(() => ({ page, per_page: perPage, search: search || undefined, status: statusFilter || undefined }), [page, perPage, search, statusFilter]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setErr("");
    storeApi.listGrns(query)
      .then((d) => { if (live) setData(d); })
      .catch((e) => { if (live) setErr(storeError(e, "Failed to load GRNs")); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [query]);

  function setTab(value) {
    setPage(1);
    if (value) setParams({ status: value }); else setParams({});
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Receive goods (GRN)</h1>
          <p className="text-sm text-slate-500">Nothing is in stock until a GRN is approved and posted.</p>
        </div>
        {canCreate && (
          <Link to="/store/grns/new" className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">
            + New GRN
          </Link>
        )}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {TABS.map(([value, label]) => (
            <button
              key={label}
              type="button"
              onClick={() => setTab(value)}
              className={`rounded-full px-3 py-1 text-sm ${statusFilter === value ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
            >
              {label}
            </button>
          ))}
          <input
            type="text"
            placeholder="Search GRN no, bill or supplier"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="ml-auto w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-72"
          />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">GRN no</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Bill / challan</th>
              <th className="px-3 py-2">Supplier</th>
              <th className="px-3 py-2 text-right">Units</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Created by</th>
              <th className="px-3 py-2">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">No GRNs found.</td></tr>
            )}
            {!loading && data.items.map((g) => (
              <tr key={g.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/store/grns/${g.id}`)}>
                <td className="px-3 py-2 font-mono text-xs font-bold text-slate-800">{g.grn_no}</td>
                <td className="px-3 py-2 text-slate-600">{g.source_type}</td>
                <td className="px-3 py-2 text-slate-600">{g.reference_no || "-"}</td>
                <td className="px-3 py-2 text-slate-600">{g.supplier_name || "-"}</td>
                <td className="px-3 py-2 text-right">{g.total_units}</td>
                <td className="px-3 py-2"><span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${GRN_BADGE[g.status] || "bg-slate-100"}`}>{g.status}</span></td>
                <td className="px-3 py-2 text-slate-600">{g.created_by_name || "-"}</td>
                <td className="px-3 py-2 text-slate-600">{fmtDateTime(g.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} perPage={perPage} total={data.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
    </div>
  );
}
