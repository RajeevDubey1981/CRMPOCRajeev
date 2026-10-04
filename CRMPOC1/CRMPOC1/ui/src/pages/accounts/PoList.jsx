import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { PO_BADGE, accountsApi, accError, money } from "../../api/accounts.js";

const TABS = [["", "All"], ["Pending Approval", "Waiting for approval"], ["Approved", "Approved"], ["Part received", "Part received"], ["Received", "Received"], ["Draft", "Drafts"]];

export default function PoList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const canCreate = hasPermission(user, "acc_purchase", "can_create");
  const statusFilter = params.get("status") || "";
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const query = useMemo(() => ({ status: statusFilter || undefined, search: search || undefined, page, per_page: perPage }), [statusFilter, search, page, perPage]);

  useEffect(() => {
    let live = true;
    setLoading(true); setErr("");
    accountsApi.pos(query).then((d) => live && setData(d)).catch((e) => live && setErr(accError(e, "Could not load purchase orders"))).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [query]);

  function pick(v) { setPage(1); if (v) setParams({ status: v }); else setParams({}); }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Purchase orders</h1>
          <p className="text-sm text-slate-500">Raise, approve and track what we buy. Goods are received against an approved PO in the Store.</p>
        </div>
        {canCreate && <Link to="/accounts/pos/new" className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">+ New PO</Link>}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {TABS.map(([v, label]) => (
            <button key={label} type="button" onClick={() => pick(v)} className={`rounded-full px-3 py-1 text-sm ${statusFilter === v ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{label}</button>
          ))}
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search PO no or supplier" className="ml-auto w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-72" />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">PO no</th><th className="px-3 py-2">Date</th><th className="px-3 py-2">Supplier</th><th className="px-3 py-2 text-right">Total</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Raised by</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>}
            {!loading && data.items.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">No purchase orders found.</td></tr>}
            {!loading && data.items.map((p) => (
              <tr key={p.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/accounts/pos/${p.id}`)}>
                <td className="px-3 py-2 font-mono text-xs font-bold text-slate-800">{p.po_no}</td>
                <td className="px-3 py-2 text-slate-600">{p.po_date}</td>
                <td className="px-3 py-2">{p.supplier_name}</td>
                <td className="px-3 py-2 text-right">{money(p.total)}</td>
                <td className="px-3 py-2"><span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${PO_BADGE[p.status] || "bg-slate-100"}`}>{p.status}</span></td>
                <td className="px-3 py-2 text-slate-600">{p.created_by_name || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination page={page} perPage={perPage} total={data.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
    </div>
  );
}
