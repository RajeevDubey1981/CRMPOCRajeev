import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, SalesTabs, btn, errText, fieldClass, useAsync, useSales } from "./salesUi.jsx";

export default function TypesPage() {
  const { reload: reloadStatus } = useSales();
  const { data, loading, error, reload } = useAsync(() => salesApi.types(), []);
  const [msg, setMsg] = useState("");
  const [fresh, setFresh] = useState({ label: "", color: "#475569" });
  const [edit, setEdit] = useState({});
  const [busy, setBusy] = useState(false);

  async function run(fn, ok) {
    setBusy(true); setMsg("");
    try { await fn(); setMsg(ok); reload(); reloadStatus(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  const val = (t, k) => (edit[t.key] && k in edit[t.key] ? edit[t.key][k] : t[k]);
  const change = (t, k, v) => setEdit((s) => ({ ...s, [t.key]: { ...(s[t.key] || {}), [k]: v } }));
  const save = (t) => run(async () => { await salesApi.patchType(t.key, { label: val(t, "label"), color: val(t, "color") }); setEdit((s) => { const n = { ...s }; delete n[t.key]; return n; }); }, `Saved: ${val(t, "label")}`);

  return (
    <div>
      <PageTitle title="Lead types" sub="The list of types a lead can have. Admin and Sub Admin add, rename, recolour or switch them off. A type is never deleted: switch it off instead, and the leads that have it keep it." />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Colour</th><th className="px-3 py-2">Leads</th><th className="px-3 py-2">On</th><th className="px-3 py-2" /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {(data || []).map((t) => (
              <tr key={t.key} className={t.active ? "" : "bg-slate-50 text-slate-400"}>
                <td className="px-3 py-2"><input className={`${fieldClass} !w-64`} value={val(t, "label")} onChange={(e) => change(t, "label", e.target.value)} /><div className="text-[11px] text-slate-400">{t.key}{t.builtin ? " · built in" : ""}</div></td>
                <td className="px-3 py-2"><input type="color" value={val(t, "color")} onChange={(e) => change(t, "color", e.target.value)} aria-label="Colour" className="h-8 w-12 cursor-pointer rounded border border-slate-300" /> <span className="ml-1 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: `${val(t, "color")}1f`, color: val(t, "color") }}>{val(t, "label")}</span></td>
                <td className="px-3 py-2 tabular-nums">{t.used}</td>
                <td className="px-3 py-2"><label className="flex items-center gap-1.5"><input type="checkbox" checked={t.active} disabled={busy} onChange={(e) => run(() => salesApi.patchType(t.key, { is_active: e.target.checked }), e.target.checked ? `${t.label} is on` : `${t.label} is off. It cannot be chosen for a new lead.`)} /> {t.active ? "On" : "Off"}</label></td>
                <td className="px-3 py-2">{edit[t.key] && <button type="button" className={btn.primary} disabled={busy} onClick={() => save(t)}>Save</button>}</td>
              </tr>
            ))}
            {!loading && (data || []).length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No type yet.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold">Add a lead type</h3>
        <div className="flex flex-wrap items-center gap-2">
          <input className={`${fieldClass} !w-64`} placeholder="For example: Hotel chain" value={fresh.label} onChange={(e) => setFresh({ ...fresh, label: e.target.value })} />
          <input type="color" value={fresh.color} onChange={(e) => setFresh({ ...fresh, color: e.target.value })} aria-label="Colour" className="h-9 w-12 cursor-pointer rounded border border-slate-300" />
          <button type="button" className={btn.go} disabled={busy || fresh.label.trim().length < 2} onClick={() => run(async () => { await salesApi.addType(fresh); setFresh({ label: "", color: "#475569" }); }, "Type added")}>Add</button>
        </div>
        <p className="mt-2 text-xs text-slate-500">The words in an enquiry make the first eight types by themselves (CSD, GeM, Spare parts and so on). A type you add is chosen by hand, by a connection's "default lead type", or when a list is loaded. After adding one, tick it for the people who handle it in Team and profiles.</p>
      </div>
    </div>
  );
}
