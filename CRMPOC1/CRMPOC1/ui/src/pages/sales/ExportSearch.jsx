import { useState } from "react";
import { Link } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import UploadModal from "./UploadModal.jsx";
import { Notice, btn, errText, fieldClass, useAsync, useSales } from "./salesUi.jsx";

// The export-market search: company lists loaded from Kompass, TradeInt, a chamber of commerce or any directory export.
// A company found here has not asked us for anything. It becomes a (cold) lead only when someone presses "Make lead".
export default function ExportSearch({ onLeadsMade }) {
  const { has } = useSales();
  const [f, setF] = useState({ country: "", kind: "", product: "", q: "", open_only: true });
  const [applied, setApplied] = useState(f);
  const facets = useAsync(() => salesApi.prospectFacets(), []);
  const found = useAsync(() => salesApi.prospects({ ...applied, open_only: applied.open_only ? true : undefined, limit: 300 }), [JSON.stringify(applied)]);
  const [picked, setPicked] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const items = found.data?.items || [];
  const open = items.filter((p) => !p.lead_id);
  const toggle = (id) => setPicked((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  async function make(ids) {
    setBusy(true); setMsg("");
    try {
      const r = await salesApi.makeProspectLeads(ids);
      setMsg(`${r.made} lead(s) made${r.linked_to_existing ? `, ${r.linked_to_existing} joined a lead that was already open` : ""}${r.no_phone ? `, ${r.no_phone} have no phone number yet (add it to the list first)` : ""}.`);
      setPicked(new Set()); found.reload(); onLeadsMade?.();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <section className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Search the export market</h2>
          <p className="text-xs text-slate-500">Company lists you load from Kompass, import-record services (TradeInt and others), a chamber of commerce or any Excel. Search them by country, kind and product, and make a lead of the companies you want to approach.</p>
        </div>
        <button type="button" className={btn.primary} onClick={() => setLoading(true)}>Load a company list</button>
      </div>
      {msg && <div className="mt-2"><Notice>{msg}</Notice></div>}
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <label className="text-xs text-slate-600">Country<br /><select className={`${fieldClass} !w-auto`} value={f.country} onChange={(e) => setF({ ...f, country: e.target.value })}><option value="">All countries</option>{(facets.data?.countries || []).map((c) => <option key={c}>{c}</option>)}</select></label>
        <label className="text-xs text-slate-600">Kind<br /><select className={`${fieldClass} !w-auto`} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}><option value="">Any kind</option>{(facets.data?.kinds || []).map((c) => <option key={c}>{c}</option>)}</select></label>
        <label className="text-xs text-slate-600">Product<br /><input className={`${fieldClass} !w-44`} value={f.product} onChange={(e) => setF({ ...f, product: e.target.value })} placeholder="air conditioner" /></label>
        <label className="text-xs text-slate-600">Name or city<br /><input className={`${fieldClass} !w-44`} value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} /></label>
        <label className="flex items-center gap-1.5 pb-2 text-xs text-slate-600"><input type="checkbox" checked={f.open_only} onChange={(e) => setF({ ...f, open_only: e.target.checked })} /> Not yet a lead</label>
        <button type="button" className={btn.primary} onClick={() => setApplied({ ...f })}>Search</button>
      </div>
      {facets.data && (facets.data.batches || []).length === 0 && <p className="mt-3 text-sm text-slate-500">No list is loaded yet. Press <b>Load a company list</b> and choose the Excel or CSV you exported.</p>}
      {items.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-sm"><b>{found.data.total} found</b>
            <span className="flex gap-2"><button type="button" className={btn.go} disabled={busy || picked.size === 0} onClick={() => make([...picked])}>Make leads of the {picked.size} ticked</button><button type="button" className={btn.plain} disabled={busy || open.length === 0} onClick={() => make(open.map((p) => p.id))}>Make leads of all {open.length} shown</button></span></div>
          <div className="max-h-96 overflow-auto rounded border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-2 py-1.5" /><th className="px-2 py-1.5">Company</th><th className="px-2 py-1.5">Place</th><th className="px-2 py-1.5">Kind</th><th className="px-2 py-1.5">Products</th><th className="px-2 py-1.5">Why it matches</th><th className="px-2 py-1.5">Found in</th><th className="px-2 py-1.5">Contact</th><th className="px-2 py-1.5" /></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((p) => (
                  <tr key={p.id} className="align-top">
                    <td className="px-2 py-1.5">{!p.lead_id && <input type="checkbox" checked={picked.has(p.id)} onChange={() => toggle(p.id)} aria-label={`Tick ${p.company}`} />}</td>
                    <td className="px-2 py-1.5 font-medium">{p.company}{p.contact_name && <div className="text-xs font-normal text-slate-500">{p.contact_name}</div>}</td>
                    <td className="px-2 py-1.5">{[p.city, p.country].filter(Boolean).join(", ")}</td>
                    <td className="px-2 py-1.5">{p.kind || "—"}</td>
                    <td className="px-2 py-1.5">{p.products || "—"}</td>
                    <td className="px-2 py-1.5 text-xs">{p.why || "—"}</td>
                    <td className="px-2 py-1.5 text-xs">{p.source}</td>
                    <td className="px-2 py-1.5 text-xs">{p.phone || <span className="text-amber-700">no phone</span>}{p.email && <div>{p.email}</div>}</td>
                    <td className="px-2 py-1.5">{p.lead_id ? <Link className="text-xs font-semibold text-indcool-blue hover:underline" to={`/sales/leads/${p.lead_id}`}>Lead made</Link> : <button type="button" className={btn.plain} disabled={busy} onClick={() => make([p.id])}>Make lead</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-1 text-xs text-slate-500">A lead made here starts Cold, says where it was found, and its first contact should be a short introduction by e-mail or phone, not a mass WhatsApp. Each country has its own rules for contacting companies: please have them checked before an outreach campaign.</p>
        </div>
      )}
      {(facets.data?.batches || []).length > 0 && (
        <details className="mt-3 text-xs text-slate-600"><summary className="cursor-pointer font-medium">Lists that are loaded ({facets.data.batches.length})</summary>
          <ul className="mt-1 space-y-1">{facets.data.batches.map((b) => (
            <li key={b.batch} className="flex flex-wrap items-center gap-2">{b.source} <span className="text-slate-400">· {b.count} companies · {b.batch}</span>
              <button type="button" className="text-rose-600 hover:underline" onClick={async () => { if (window.confirm("Remove this list? Companies that already became a lead are kept.")) { try { const r = await salesApi.deleteProspectBatch(b.batch); setMsg(`${r.deleted} companies removed`); found.reload(); facets.reload(); } catch (e) { setMsg(errText(e)); } } }}>Remove this list</button></li>
          ))}</ul></details>
      )}
      {loading && <UploadModal mode="prospects" onClose={() => setLoading(false)} onDone={(r) => { setLoading(false); if (r) { setMsg(`${r.added} companies loaded`); found.reload(); facets.reload(); } }} />}
    </section>
  );
}
