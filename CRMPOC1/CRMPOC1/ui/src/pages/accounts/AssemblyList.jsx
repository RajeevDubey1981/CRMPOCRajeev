import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { ASM_BADGE, accountsApi, accError, fieldClass, labelClass } from "../../api/accounts.js";

export default function AssemblyList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const canCreate = hasPermission(user, "acc_assembly", "can_create");
  const [data, setData] = useState({ items: [], total: 0 });
  const [makeItems, setMakeItems] = useState([]);
  const [itemId, setItemId] = useState("");
  const [qty, setQty] = useState(1);
  const [remarks, setRemarks] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    accountsApi.assemblies({ per_page: 100 }).then(setData).catch((e) => setErr(accError(e, "Could not load assembly orders")));
    accountsApi.lookupItems({ make_only: true }).then(setMakeItems).catch(() => {});
  }, []);

  async function plan(e) {
    e.preventDefault();
    if (!itemId) { setErr("Choose what to build."); return; }
    setBusy(true); setErr("");
    try {
      const a = await accountsApi.createAssembly({ item_id: Number(itemId), qty: Number(qty), remarks: remarks || null });
      navigate(`/accounts/assembly/${a.id}`);
    } catch (e2) { setErr(accError(e2, "Could not plan the assembly")); setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Assembly</h1>
        <p className="text-sm text-slate-500">Build finished units from a BOM. Parts leave the store, finished units come in with their own serial numbers and a passport of the parts inside.</p>
      </div>
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {canCreate && (
        <form onSubmit={plan} className="rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-slate-800">Plan an assembly</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
            <div className="md:col-span-2">
              <label className={labelClass}>Finished item</label>
              <select value={itemId} onChange={(e) => setItemId(e.target.value)} className={fieldClass}>
                <option value="">Choose an item with an active BOM</option>
                {makeItems.map((i) => <option key={i.id} value={i.id}>{i.item_name} ({i.item_code})</option>)}
              </select>
            </div>
            <div><label className={labelClass}>How many</label><input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} className={fieldClass} /></div>
            <div className="md:col-span-2"><label className={labelClass}>Remarks</label><input value={remarks} onChange={(e) => setRemarks(e.target.value)} className={fieldClass} /></div>
          </div>
          <button type="submit" disabled={busy} className="mt-3 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Plan assembly</button>
        </form>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700"><tr><th className="px-3 py-2">Assembly</th><th className="px-3 py-2">Item</th><th className="px-3 py-2 text-right">Units</th><th className="px-3 py-2">Status</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.length === 0 && <tr><td colSpan={4} className="px-3 py-6 text-center text-slate-500">No assembly orders yet.</td></tr>}
            {data.items.map((a) => (
              <tr key={a.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/accounts/assembly/${a.id}`)}>
                <td className="px-3 py-2 font-mono text-xs font-bold">{a.asm_no}</td>
                <td className="px-3 py-2">{a.item_name}</td>
                <td className="px-3 py-2 text-right">{a.qty}</td>
                <td className="px-3 py-2"><span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${ASM_BADGE[a.status] || "bg-slate-100"}`}>{a.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
