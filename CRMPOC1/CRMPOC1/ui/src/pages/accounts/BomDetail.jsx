import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { BOM_BADGE, accountsApi, accError, fieldClass, labelClass, money } from "../../api/accounts.js";

export default function BomDetail() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const { user } = useAuth();
  const canCreate = hasPermission(user, "acc_items", "can_create");

  const [bom, setBom] = useState(null);
  const [makeItems, setMakeItems] = useState([]);
  const [itemId, setItemId] = useState("");
  const [head, setHead] = useState({ notes: "", labour_cost: "0", overhead_cost: "0" });
  const [lines, setLines] = useState([]);
  const [compQuery, setCompQuery] = useState("");
  const [compList, setCompList] = useState([]);
  const [pick, setPick] = useState({ id: "", qty: 1, scrap: 0 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");

  const editable = isNew ? canCreate : !!bom?.can_edit;

  function fill(b) {
    setBom(b);
    setItemId(String(b.item_id));
    setHead({ notes: b.notes || "", labour_cost: String(b.labour_cost), overhead_cost: String(b.overhead_cost) });
    setLines(b.lines.map((l) => ({ key: `l${l.id}`, component_item_id: l.component_item_id, item_name: l.item_name, item_code: l.item_code, qty: String(Number(l.qty)), scrap_pct: String(Number(l.scrap_pct)) })));
  }

  useEffect(() => { if (isNew) accountsApi.lookupItems({ make_only: true }).then(setMakeItems).catch(() => {}); }, [isNew]);
  useEffect(() => { if (!isNew) accountsApi.getBom(id).then(fill).catch((e) => setErr(accError(e, "Could not load this BOM"))); }, [id, isNew]);
  useEffect(() => {
    if (!editable) return undefined;
    const t = setTimeout(() => accountsApi.lookupItems({ q: compQuery || undefined }).then(setCompList).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [compQuery, editable]);

  function addLine() {
    const it = compList.find((x) => String(x.id) === String(pick.id));
    if (!it) { setErr("Pick a component first."); return; }
    if (lines.some((l) => l.component_item_id === it.id)) { setErr(`${it.item_name} is already on this BOM.`); return; }
    if (!(Number(pick.qty) > 0)) { setErr("Enter how many go into one unit."); return; }
    setErr("");
    setLines((cur) => [...cur, { key: `n${Date.now()}`, component_item_id: it.id, item_name: it.item_name, item_code: it.item_code, qty: String(pick.qty), scrap_pct: String(pick.scrap || 0) }]);
    setPick({ id: "", qty: 1, scrap: 0 });
  }

  const setLine = (key, f, v) => setLines((cur) => cur.map((l) => (l.key === key ? { ...l, [f]: v } : l)));

  const payload = () => ({
    item_id: Number(itemId), notes: head.notes || null, labour_cost: Number(head.labour_cost) || 0, overhead_cost: Number(head.overhead_cost) || 0,
    lines: lines.map((l) => ({ component_item_id: l.component_item_id, qty: Number(l.qty), scrap_pct: Number(l.scrap_pct) || 0 })),
  });

  async function save() {
    if (!itemId) { setErr("Choose the finished item."); return; }
    setBusy(true); setErr(""); setNote("");
    try {
      const b = isNew ? await accountsApi.createBom(payload()) : await accountsApi.updateBom(bom.id, payload());
      if (isNew) { navigate(`/accounts/boms/${b.id}`, { replace: true }); return; }
      fill(b); setNote("Draft saved.");
    } catch (e) { setErr(accError(e, "Could not save the BOM")); }
    finally { setBusy(false); }
  }

  async function act(fn, okText, then) {
    setBusy(true); setErr(""); setNote("");
    try { const b = await fn(); if (then) { then(b); return; } fill(b); setNote(okText); }
    catch (e) { setErr(accError(e, "That did not work")); }
    finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/accounts/boms" className="text-sm text-slate-500 hover:underline">&larr; Back to BOMs</Link>
          <h1 className="text-2xl font-semibold text-slate-800">{isNew ? "New BOM" : `${bom?.item_name || "BOM"} v${bom?.version || ""}`}</h1>
        </div>
        {bom && <span className={`rounded-full px-3 py-1 text-sm font-semibold ${BOM_BADGE[bom.status] || "bg-slate-100"}`}>{bom.status}</span>}
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {note && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{note}</div>}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="md:col-span-2">
            <label className={labelClass}>Finished item *</label>
            {isNew ? (
              <select value={itemId} onChange={(e) => setItemId(e.target.value)} className={fieldClass}>
                <option value="">Choose an item set to Make or Both</option>
                {makeItems.map((i) => <option key={i.id} value={i.id}>{i.item_name} ({i.item_code})</option>)}
              </select>
            ) : <div className="rounded-md bg-slate-50 px-3 py-2 text-sm">{bom?.item_name} <span className="font-mono text-xs text-slate-500">{bom?.item_code}</span></div>}
            {isNew && makeItems.length === 0 && <p className="mt-1 text-xs text-amber-700">No item is set to Make or Both yet. Open the item on the Item Masters page and change "How we get it".</p>}
          </div>
          <div><label className={labelClass}>Labour per unit</label><input type="number" min="0" step="0.01" disabled={!editable} value={head.labour_cost} onChange={(e) => setHead({ ...head, labour_cost: e.target.value })} className={fieldClass} /></div>
          <div><label className={labelClass}>Overhead per unit</label><input type="number" min="0" step="0.01" disabled={!editable} value={head.overhead_cost} onChange={(e) => setHead({ ...head, overhead_cost: e.target.value })} className={fieldClass} /></div>
          <div className="md:col-span-4"><label className={labelClass}>Notes</label><input disabled={!editable} value={head.notes} onChange={(e) => setHead({ ...head, notes: e.target.value })} className={fieldClass} /></div>
        </div>
        {bom && <p className="mt-3 text-xs text-slate-500">Drafted by {bom.created_by_name || "-"}{bom.activated_by_name ? `. Activated by ${bom.activated_by_name}.` : ""}</p>}
      </div>

      {editable && (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-slate-800">Add a component</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
            <div className="md:col-span-3">
              <input value={compQuery} onChange={(e) => setCompQuery(e.target.value)} className={`${fieldClass} mb-2`} placeholder="Search component name or code" />
              <select value={pick.id} onChange={(e) => setPick({ ...pick, id: e.target.value })} className={fieldClass}>
                <option value="">Select a component</option>
                {compList.filter((i) => String(i.id) !== itemId).map((i) => <option key={i.id} value={i.id}>{i.item_name} ({i.item_code})</option>)}
              </select>
            </div>
            <div><label className={labelClass}>Per unit</label><input type="number" min="0" step="0.001" value={pick.qty} onChange={(e) => setPick({ ...pick, qty: e.target.value })} className={fieldClass} /></div>
            <div><label className={labelClass}>Scrap %</label><input type="number" min="0" max="100" step="0.01" value={pick.scrap} onChange={(e) => setPick({ ...pick, scrap: e.target.value })} className={fieldClass} /></div>
          </div>
          <button type="button" onClick={addLine} className="mt-3 rounded-md border border-brand-500 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50">Add component</button>
        </div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">Component</th><th className="px-3 py-2 text-right">Per unit</th><th className="px-3 py-2 text-right">Scrap %</th>{bom && <><th className="px-3 py-2 text-right">Unit cost</th><th className="px-3 py-2 text-right">Line cost</th><th className="px-3 py-2 text-right">In store</th></>}{editable && <th className="px-3 py-2" />}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lines.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No components yet.</td></tr>}
            {lines.map((l) => {
              const saved = bom?.lines.find((x) => `l${x.id}` === l.key);
              return (
                <tr key={l.key}>
                  <td className="px-3 py-2">{l.item_name} <span className="font-mono text-xs text-slate-500">{l.item_code}</span></td>
                  <td className="px-3 py-2 text-right">{editable ? <input type="number" min="0" step="0.001" value={l.qty} onChange={(e) => setLine(l.key, "qty", e.target.value)} className="w-24 rounded-md border border-slate-300 px-2 py-1 text-right" /> : Number(l.qty)}</td>
                  <td className="px-3 py-2 text-right">{editable ? <input type="number" min="0" max="100" step="0.01" value={l.scrap_pct} onChange={(e) => setLine(l.key, "scrap_pct", e.target.value)} className="w-20 rounded-md border border-slate-300 px-2 py-1 text-right" /> : Number(l.scrap_pct)}</td>
                  {bom && <>
                    <td className="px-3 py-2 text-right">{saved?.unit_cost != null ? money(saved.unit_cost) : <span className="text-amber-700">unknown</span>}</td>
                    <td className="px-3 py-2 text-right">{saved?.line_cost != null ? money(saved.line_cost) : "-"}</td>
                    <td className="px-3 py-2 text-right">{saved ? saved.in_store : "-"}</td>
                  </>}
                  {editable && <td className="px-3 py-2 text-right"><button type="button" onClick={() => setLines((c) => c.filter((x) => x.key !== l.key))} className="text-xs text-rose-600 hover:underline">Remove</button></td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {bom && bom.lines.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg bg-white p-4 shadow-sm"><div className="text-xs text-slate-500">Material per unit</div><div className="text-lg font-semibold">{bom.material_cost != null ? money(bom.material_cost) : "-"}</div></div>
          <div className="rounded-lg bg-white p-4 shadow-sm"><div className="text-xs text-slate-500">Cost per unit with labour and overhead</div><div className="text-lg font-semibold">{bom.unit_cost != null ? money(bom.unit_cost) : "-"}</div>{!bom.cost_complete && <div className="text-xs text-amber-700">Some parts have no known cost yet.</div>}</div>
          <div className="rounded-lg bg-white p-4 shadow-sm"><div className="text-xs text-slate-500">Can build from store stock</div><div className="text-lg font-semibold">{bom.can_build} unit(s)</div></div>
          <div className="rounded-lg bg-white p-4 shadow-sm"><div className="text-xs text-slate-500">Last bought complete at</div><div className="text-lg font-semibold">{bom.buy_price_hint != null ? money(bom.buy_price_hint) : "-"}</div></div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {editable && <button type="button" disabled={busy} onClick={save} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Save draft</button>}
        {bom?.can_activate && <button type="button" disabled={busy} onClick={() => act(() => accountsApi.activateBom(bom.id), "This version is now the active BOM. The old one is retired.")} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">Activate this version</button>}
        {bom && canCreate && <button type="button" disabled={busy} onClick={() => act(() => accountsApi.copyBom(bom.id), "", (b) => navigate(`/accounts/boms/${b.id}`))} className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50">New version from this</button>}
        {bom?.status === "Active" && <Link to="/accounts/assembly" className="rounded-md border border-brand-500 px-4 py-2 text-sm text-brand-600 hover:bg-brand-50">Plan an assembly</Link>}
        {bom?.can_edit && <button type="button" disabled={busy} onClick={async () => { if (!window.confirm("Delete this draft BOM?")) return; try { await accountsApi.deleteBom(bom.id); navigate("/accounts/boms", { replace: true }); } catch (e) { setErr(accError(e, "Could not delete")); } }} className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">Delete draft</button>}
      </div>
      {bom?.status === "Draft" && !bom.can_activate && <p className="text-sm text-slate-500">An accounts manager activates a BOM once it is checked.</p>}
    </div>
  );
}
