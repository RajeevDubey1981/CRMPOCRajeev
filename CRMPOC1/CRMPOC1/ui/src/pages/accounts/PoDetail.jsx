import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { PO_BADGE, accountsApi, accError, fieldClass, labelClass, money } from "../../api/accounts.js";

const r2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;

export default function PoDetail() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const canCreate = hasPermission(user, "acc_purchase", "can_create");

  const [meta, setMeta] = useState({ company_state: "", maker_checker: true });
  const [po, setPo] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [head, setHead] = useState({ supplier_id: "", po_date: new Date().toISOString().slice(0, 10), expected_date: "", payment_terms_days: "", terms: "", remarks: "" });
  const [lines, setLines] = useState([]);
  const [itemQuery, setItemQuery] = useState("");
  const [itemList, setItemList] = useState([]);
  const [pick, setPick] = useState({ item_id: "", qty: 1, rate: "", gst_rate: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [reasonFor, setReasonFor] = useState("");

  const editable = isNew ? canCreate : !!po?.can_edit;

  function fill(p) {
    setPo(p);
    setHead({ supplier_id: String(p.supplier_id), po_date: p.po_date, expected_date: p.expected_date || "", payment_terms_days: String(p.payment_terms_days), terms: p.terms || "", remarks: p.remarks || "" });
    setLines(p.lines.map((l) => ({ key: `l${l.id}`, item_id: l.item_id, item_code: l.item_code, item_name: l.item_name, qty: l.qty, rate: l.rate, gst_rate: l.gst_rate })));
  }

  useEffect(() => { if (location.state?.err) setErr(location.state.err); }, [location.state]);
  useEffect(() => { accountsApi.meta().then(setMeta).catch(() => {}); accountsApi.suppliers({ active_only: true, per_page: 200 }).then((d) => setSuppliers(d.items)).catch(() => {}); }, []);
  useEffect(() => { if (!isNew) accountsApi.getPo(id).then(fill).catch((e) => setErr(accError(e, "Could not load this purchase order"))); }, [id, isNew]);
  useEffect(() => {
    if (!editable) return undefined;
    const t = setTimeout(() => accountsApi.lookupItems({ q: itemQuery || undefined }).then(setItemList).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [itemQuery, editable]);

  const supplier = suppliers.find((s) => String(s.id) === String(head.supplier_id));
  const intra = supplier ? supplier.state === meta.company_state : po?.intra_state ?? true;

  const totals = useMemo(() => {
    let taxable = 0, tax = 0;
    lines.forEach((l) => { const t = r2(Number(l.qty) * Number(l.rate || 0)); taxable += t; tax += r2(t * Number(l.gst_rate || 0) / 100); });
    return { taxable: r2(taxable), tax: r2(tax), total: r2(taxable + tax) };
  }, [lines]);

  function chooseSupplier(v) {
    const s = suppliers.find((x) => String(x.id) === String(v));
    setHead((h) => ({ ...h, supplier_id: v, payment_terms_days: s ? String(s.payment_terms_days) : h.payment_terms_days }));
  }

  function choosePickItem(v) {
    const it = itemList.find((x) => String(x.id) === String(v));
    setPick({ item_id: v, qty: 1, rate: "", gst_rate: it?.gst_rate != null ? String(it.gst_rate) : "18" });
  }

  function addLine() {
    const it = itemList.find((x) => String(x.id) === String(pick.item_id));
    if (!it) { setErr("Pick an item first."); return; }
    if (!(Number(pick.qty) >= 1)) { setErr("Enter a quantity of 1 or more."); return; }
    setErr("");
    setLines((cur) => [...cur, { key: `n${Date.now()}${Math.random()}`, item_id: it.id, item_code: it.item_code, item_name: it.item_name, qty: Number(pick.qty), rate: pick.rate === "" ? 0 : Number(pick.rate), gst_rate: pick.gst_rate === "" ? 18 : Number(pick.gst_rate) }]);
    setPick({ item_id: "", qty: 1, rate: "", gst_rate: "" });
  }

  const setLine = (key, field, v) => setLines((cur) => cur.map((l) => (l.key === key ? { ...l, [field]: v } : l)));
  const removeLine = (key) => setLines((cur) => cur.filter((l) => l.key !== key));

  const payload = () => ({
    supplier_id: Number(head.supplier_id), po_date: head.po_date || null, expected_date: head.expected_date || null,
    payment_terms_days: head.payment_terms_days === "" ? null : Number(head.payment_terms_days), terms: head.terms || null, remarks: head.remarks || null,
    lines: lines.map((l) => ({ item_id: l.item_id, qty: Number(l.qty), rate: Number(l.rate || 0), gst_rate: l.gst_rate === "" ? null : Number(l.gst_rate) })),
  });

  async function save(thenSubmit = false) {
    if (!head.supplier_id) { setErr("Choose the supplier."); return; }
    setBusy(true); setErr(""); setNote("");
    try {
      let p = isNew ? await accountsApi.createPo(payload()) : await accountsApi.updatePo(po.id, payload());
      if (thenSubmit) {
        try { p = await accountsApi.submitPo(p.id); } catch (e2) {
          const msg = `Saved as a draft, but it could not be submitted: ${accError(e2, "submit failed")}`;
          if (isNew) { navigate(`/accounts/pos/${p.id}`, { replace: true, state: { err: msg } }); return; }
          fill(p); setErr(msg); return;
        }
      }
      if (isNew) { navigate(`/accounts/pos/${p.id}`, { replace: true }); return; }
      fill(p);
      setNote(thenSubmit ? "Submitted. A second person must approve it." : "Draft saved.");
    } catch (e) { setErr(accError(e, "Could not save the purchase order")); }
    finally { setBusy(false); }
  }

  async function act(fn, okText) {
    setBusy(true); setErr(""); setNote("");
    try { const p = await fn(); fill(p); setNote(okText); setReason(""); setReasonFor(""); }
    catch (e) { setErr(accError(e, "That did not work")); }
    finally { setBusy(false); }
  }

  const dueText = po?.supplier_is_msme ? "MSME supplier: pay within 45 days of the goods being accepted." : null;

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/accounts/pos" className="text-sm text-slate-500 hover:underline">&larr; Back to purchase orders</Link>
          <h1 className="text-2xl font-semibold text-slate-800">{isNew ? "New purchase order" : po?.po_no || "Purchase order"}</h1>
        </div>
        {po && <span className={`rounded-full px-3 py-1 text-sm font-semibold ${PO_BADGE[po.status] || "bg-slate-100"}`}>{po.status}</span>}
      </div>

      {po?.reject_reason && <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">Sent back: {po.reject_reason}</div>}
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {note && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{note}</div>}
      {dueText && <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{dueText}</div>}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="md:col-span-2">
            <label className={labelClass}>Supplier *</label>
            <select disabled={!editable} value={head.supplier_id} onChange={(e) => chooseSupplier(e.target.value)} className={fieldClass}>
              <option value="">Choose supplier</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}{s.gstin ? ` (${s.gstin})` : " (unregistered)"}</option>)}
              {po && !suppliers.find((s) => s.id === po.supplier_id) && <option value={po.supplier_id}>{po.supplier_name}</option>}
            </select>
            {supplier && <p className="mt-1 text-xs text-slate-500">Place of supply {supplier.state}. {intra ? "Same state as us: CGST + SGST." : "Other state: IGST."}</p>}
          </div>
          <div><label className={labelClass}>PO date</label><input type="date" disabled={!editable} value={head.po_date} onChange={(e) => setHead({ ...head, po_date: e.target.value })} className={fieldClass} /></div>
          <div><label className={labelClass}>Expected by</label><input type="date" disabled={!editable} value={head.expected_date} onChange={(e) => setHead({ ...head, expected_date: e.target.value })} className={fieldClass} /></div>
          <div><label className={labelClass}>Payment terms (days)</label><input type="number" min="0" disabled={!editable} value={head.payment_terms_days} onChange={(e) => setHead({ ...head, payment_terms_days: e.target.value })} className={fieldClass} /></div>
          <div className="md:col-span-3"><label className={labelClass}>Terms and remarks</label><input disabled={!editable} value={head.terms} onChange={(e) => setHead({ ...head, terms: e.target.value })} className={fieldClass} placeholder="Delivery, packing, warranty terms" /></div>
        </div>
        {po && <p className="mt-3 text-xs text-slate-500">Raised by {po.created_by_name || "-"}{po.approved_by_name ? `. Approved by ${po.approved_by_name}.` : ""}</p>}
      </div>

      {editable && (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-slate-800">Add a line</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-6">
            <div className="md:col-span-3">
              <input value={itemQuery} onChange={(e) => setItemQuery(e.target.value)} className={`${fieldClass} mb-2`} placeholder="Search item name or code" />
              <select value={pick.item_id} onChange={(e) => choosePickItem(e.target.value)} className={fieldClass}>
                <option value="">Select an item</option>
                {itemList.map((i) => <option key={i.id} value={i.id}>{i.item_name} ({i.item_code})</option>)}
              </select>
            </div>
            <div><label className={labelClass}>Qty</label><input type="number" min="1" value={pick.qty} onChange={(e) => setPick({ ...pick, qty: e.target.value })} className={fieldClass} /></div>
            <div><label className={labelClass}>Rate (ex GST)</label><input type="number" min="0" step="0.01" value={pick.rate} onChange={(e) => setPick({ ...pick, rate: e.target.value })} className={fieldClass} /></div>
            <div><label className={labelClass}>GST %</label><input type="number" min="0" max="40" step="0.01" value={pick.gst_rate} onChange={(e) => setPick({ ...pick, gst_rate: e.target.value })} className={fieldClass} /></div>
          </div>
          <button type="button" onClick={addLine} className="mt-3 rounded-md border border-brand-500 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50">Add line</button>
        </div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">Item</th><th className="px-3 py-2 text-right">Qty</th><th className="px-3 py-2 text-right">Rate</th><th className="px-3 py-2 text-right">GST %</th><th className="px-3 py-2 text-right">Taxable</th>{po && po.status !== "Draft" && <th className="px-3 py-2 text-right">Received</th>}{editable && <th className="px-3 py-2" />}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lines.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No lines yet.</td></tr>}
            {lines.map((l) => {
              const saved = po?.lines.find((x) => `l${x.id}` === l.key);
              return (
                <tr key={l.key}>
                  <td className="px-3 py-2">{l.item_name} <span className="font-mono text-xs text-slate-500">{l.item_code}</span></td>
                  <td className="px-3 py-2 text-right">{editable ? <input type="number" min="1" value={l.qty} onChange={(e) => setLine(l.key, "qty", e.target.value)} className="w-20 rounded-md border border-slate-300 px-2 py-1 text-right" /> : l.qty}</td>
                  <td className="px-3 py-2 text-right">{editable ? <input type="number" min="0" step="0.01" value={l.rate} onChange={(e) => setLine(l.key, "rate", e.target.value)} className="w-28 rounded-md border border-slate-300 px-2 py-1 text-right" /> : money(l.rate)}</td>
                  <td className="px-3 py-2 text-right">{editable ? <input type="number" min="0" max="40" step="0.01" value={l.gst_rate} onChange={(e) => setLine(l.key, "gst_rate", e.target.value)} className="w-20 rounded-md border border-slate-300 px-2 py-1 text-right" /> : `${Number(l.gst_rate)}%`}</td>
                  <td className="px-3 py-2 text-right">{money(r2(Number(l.qty) * Number(l.rate || 0)))}</td>
                  {po && po.status !== "Draft" && <td className="px-3 py-2 text-right">{saved ? `${saved.received_qty} of ${saved.qty}` : "-"}</td>}
                  {editable && <td className="px-3 py-2 text-right"><button type="button" onClick={() => removeLine(l.key)} className="text-xs text-rose-600 hover:underline">Remove</button></td>}
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="space-y-1 border-t border-slate-100 px-4 py-3 text-sm">
          <div className="flex justify-between"><span className="text-slate-600">Taxable value</span><span>{money(editable ? totals.taxable : po?.taxable_value)}</span></div>
          {intra ? (
            <>
              <div className="flex justify-between"><span className="text-slate-600">CGST</span><span>{money(editable ? r2(totals.tax / 2) : po?.cgst)}</span></div>
              <div className="flex justify-between"><span className="text-slate-600">SGST</span><span>{money(editable ? r2(totals.tax - r2(totals.tax / 2)) : po?.sgst)}</span></div>
            </>
          ) : (
            <div className="flex justify-between"><span className="text-slate-600">IGST</span><span>{money(editable ? totals.tax : po?.igst)}</span></div>
          )}
          <div className="flex justify-between border-t border-slate-100 pt-1 text-base font-semibold"><span>Total</span><span>{money(editable ? totals.total : po?.total)}</span></div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {editable && <button type="button" disabled={busy} onClick={() => save(false)} className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50">Save draft</button>}
        {editable && <button type="button" disabled={busy} onClick={() => save(true)} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Submit for approval</button>}
        {po?.can_approve && <button type="button" disabled={busy} onClick={() => act(() => accountsApi.approvePo(po.id), "Approved. The store can now receive goods against it.")} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">Approve</button>}
        {po?.can_approve && <button type="button" onClick={() => setReasonFor("reject")} className="rounded-md border border-amber-400 px-4 py-2 text-sm text-amber-800 hover:bg-amber-50">Send back</button>}
        {po?.can_cancel && <button type="button" onClick={() => setReasonFor("cancel")} className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">Cancel PO</button>}
      </div>
      {po && po.status === "Pending Approval" && !po.can_approve && <p className="text-sm text-slate-500">Waiting for another person with approval rights. {meta.maker_checker ? "The person who raised a PO cannot approve it." : ""}</p>}

      {reasonFor && (
        <div className="space-y-2 rounded-lg bg-white p-4 shadow-sm">
          <label className={labelClass}>{reasonFor === "reject" ? "Why is it being sent back?" : "Why is it being cancelled?"}</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} className={fieldClass} />
          <div className="flex gap-2">
            <button type="button" disabled={busy || !reason.trim()} onClick={() => act(() => (reasonFor === "reject" ? accountsApi.rejectPo(po.id, reason.trim()) : accountsApi.cancelPo(po.id, reason.trim())), reasonFor === "reject" ? "Sent back to the person who raised it." : "Purchase order cancelled.")} className="rounded-md bg-rose-600 px-3 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50">Confirm</button>
            <button type="button" onClick={() => { setReasonFor(""); setReason(""); }} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Back</button>
          </div>
        </div>
      )}
    </div>
  );
}
