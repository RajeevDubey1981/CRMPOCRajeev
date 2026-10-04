import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { BOM_BADGE, accountsApi, accError, money } from "../../api/accounts.js";

const TABS = [["", "All"], ["Active", "Active"], ["Draft", "Drafts"], ["Retired", "Retired"]];

export default function BomList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const canCreate = hasPermission(user, "acc_items", "can_create");
  const statusFilter = params.get("status") || "";
  const [data, setData] = useState({ items: [], total: 0 });
  const [search, setSearch] = useState("");
  const [err, setErr] = useState("");
  const query = useMemo(() => ({ status: statusFilter || undefined, search: search || undefined, per_page: 200 }), [statusFilter, search]);

  useEffect(() => {
    let live = true;
    const t = setTimeout(() => accountsApi.boms(query).then((d) => live && setData(d)).catch((e) => live && setErr(accError(e, "Could not load BOMs"))), 200);
    return () => { live = false; clearTimeout(t); };
  }, [query]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Items and BOM</h1>
          <p className="text-sm text-slate-500">A BOM lists the parts one finished unit is made from. Items set to Make or Both can be assembled in our own store.</p>
        </div>
        {canCreate && <Link to="/accounts/boms/new" className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">+ New BOM</Link>}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {TABS.map(([v, label]) => (
            <button key={label} type="button" onClick={() => (v ? setParams({ status: v }) : setParams({}))} className={`rounded-full px-3 py-1 text-sm ${statusFilter === v ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{label}</button>
          ))}
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search item name or code" className="ml-auto w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-72" />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">Item</th><th className="px-3 py-2">Version</th><th className="px-3 py-2">Status</th><th className="px-3 py-2 text-right">Parts</th><th className="px-3 py-2 text-right">Cost per unit</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No BOMs yet. First set an item's source to Make or Both on its Item Master page, then add its BOM here.</td></tr>}
            {data.items.map((b) => (
              <tr key={b.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/accounts/boms/${b.id}`)}>
                <td className="px-3 py-2">{b.item_name} <span className="font-mono text-xs text-slate-500">{b.item_code}</span></td>
                <td className="px-3 py-2">v{b.version}</td>
                <td className="px-3 py-2"><span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${BOM_BADGE[b.status] || "bg-slate-100"}`}>{b.status}</span></td>
                <td className="px-3 py-2 text-right">{b.lines}</td>
                <td className="px-3 py-2 text-right">{b.unit_cost != null ? money(b.unit_cost) : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
