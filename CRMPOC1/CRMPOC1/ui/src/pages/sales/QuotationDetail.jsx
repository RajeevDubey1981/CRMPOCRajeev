import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import logo from "../../assets/indcool-logo.png";
import Modal from "../../components/Modal.jsx";
import { Footer } from "./LeadModals.jsx";
import { Field, Notice, PageTitle, QUOTE_TONE, SalesTabs, btn, errText, fieldClass, fmtDate, fmtDateTime, moneyIn, useAsync, useSales } from "./salesUi.jsx";

const ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
const two = (x) => (x < 20 ? ONES[x] : TENS[Math.floor(x / 10)] + (x % 10 ? ` ${ONES[x % 10]}` : ""));
const three = (x) => (x >= 100 ? `${ONES[Math.floor(x / 100)]} Hundred${x % 100 ? " " : ""}` : "") + (x % 100 ? two(x % 100) : "");

export function amountInWords(value, usd) {
  let n = Math.round(Number(value) || 0);
  if (n === 0) return "Zero";
  const out = [];
  if (usd) {
    const m = Math.floor(n / 1e6); n %= 1e6; const t = Math.floor(n / 1e3); n %= 1e3;
    if (m) out.push(`${three(m)} Million`);
    if (t) out.push(`${three(t)} Thousand`);
    if (n) out.push(three(n));
  } else {
    const cr = Math.floor(n / 1e7); n %= 1e7; const lk = Math.floor(n / 1e5); n %= 1e5; const th = Math.floor(n / 1e3); n %= 1e3;
    if (cr) out.push(`${three(cr)} Crore`);
    if (lk) out.push(`${three(lk)} Lakh`);
    if (th) out.push(`${three(th)} Thousand`);
    if (n) out.push(three(n));
  }
  return out.join(" ");
}

function Paper({ q }) {
  const usd = q.currency === "USD";
  const stamp = ["appr", "sent", "acc"].includes(q.status) ? ["APPROVED", "border-emerald-700 text-emerald-700"] : ["wait", "wadm"].includes(q.status) ? ["WAITING FOR APPROVAL", "border-amber-700 text-amber-700"] : ["rej", "cancel", "cust_rej"].includes(q.status) ? ["NOT VALID", "border-rose-700 text-rose-700"] : ["DRAFT", "border-amber-700 text-amber-700"];
  const m = (v) => moneyIn(q.currency, v);
  return (
    <div id="quote-paper" className="rounded border border-slate-300 bg-white p-5 text-[12.5px] text-slate-900 shadow-sm" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-[3px] border-[#1e3a78] pb-3">
        <div className="flex items-center gap-3">
          <img src={logo} alt="INDcool" className="h-14 w-auto" />
          <div className="text-[11px] leading-snug text-slate-600">
            <div className="text-xs font-bold text-slate-900">{q.company.name}</div>
            <div>{q.company.tagline}</div>
            <div>{q.company.address}</div>
            {q.company.gstin && <div>GSTIN {q.company.gstin}</div>}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[15px] font-bold tracking-widest text-[#1e3a78]">QUOTATION</div>
          <div className="font-bold">{q.quote_no}</div>
          <div>Date: {fmtDate(q.created_at)}</div>
          <div>Valid for {q.valid_days} days</div>
          <span className={`mt-1 inline-block -rotate-3 rounded border-2 px-2 py-0.5 text-xs font-extrabold tracking-wider ${stamp[1]}`}>{stamp[0]}</span>
        </div>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div><b>To</b><br />{q.party}<br />{[q.address, q.state].filter(Boolean).join(", ")}<br />{usd ? "Importer reg. no." : "GSTIN"}: {q.gstin || "-"}{q.reference_line && <><br /><b>Ref:</b> {q.reference_line}</>}</div>
        <div><b>Approved by</b><br />{["appr", "sent", "acc"].includes(q.status) ? q.approved_by_name || "—" : "—"}</div>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-[12px]">
          <thead><tr className="bg-[#1e3a78] text-white">{["#", "Item", "HSN", "Qty", "Rate", "Disc %", "Taxable", "GST", "Amount"].map((h, i) => <th key={h} className={`px-2 py-1.5 ${i >= 3 ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
          <tbody>
            {q.lines.map((l, i) => (
              <tr key={l.id} className="border-t border-slate-200">
                <td className="px-2 py-1.5">{i + 1}</td>
                <td className="px-2 py-1.5"><b>{l.item_name}</b><br /><span className="text-[11px] text-slate-500">{l.item_code}</span></td>
                <td className="px-2 py-1.5">{l.hsn}</td>
                <td className="px-2 py-1.5 text-right">{l.qty}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m(l.rate)}</td>
                <td className="px-2 py-1.5 text-right">{l.discount_pct}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m(l.taxable)}</td>
                <td className="px-2 py-1.5 text-right">{l.gst_pct}%</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m(l.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ml-auto mt-2 w-full max-w-xs">
        {[["Total before discount", m(q.gross)], [`Discount (${q.discount_pct}%)`, `- ${m(q.discount)}`], ["Taxable value", m(q.taxable)]].map(([a, b]) => <div key={a} className="flex justify-between py-0.5"><span>{a}</span><span className="tabular-nums">{b}</span></div>)}
        {usd ? <div className="flex justify-between py-0.5"><span>GST</span><span>Nil: export under LUT</span></div>
          : q.intra_state ? <><div className="flex justify-between py-0.5"><span>CGST</span><span className="tabular-nums">{m(q.tax / 2)}</span></div><div className="flex justify-between py-0.5"><span>SGST</span><span className="tabular-nums">{m(q.tax / 2)}</span></div></>
            : <div className="flex justify-between py-0.5"><span>IGST</span><span className="tabular-nums">{m(q.tax)}</span></div>}
        <div className="mt-1 flex justify-between border-t-2 border-[#1e3a78] pt-1 text-sm font-extrabold"><span>Grand total</span><span className="tabular-nums">{m(q.total)}</span></div>
      </div>
      <p className="mt-2 text-[11.5px] text-slate-700"><b>In words:</b> {usd ? "US Dollars" : "Rupees"} {amountInWords(q.total, usd)} only</p>
      <div className="mt-2"><b>Terms</b>
        <ol className="ml-5 list-decimal text-[11.5px]">
          <li>Payment: {q.payment_terms}.</li><li>Delivery: {q.delivery_terms}.</li><li>Warranty: {q.warranty_terms}.</li>
          <li>Prices are valid for {q.valid_days} days from the date above.{usd ? " Exported under LUT: no GST is charged. Import duty and taxes in the destination country are paid by the buyer." : " GST as applicable."}</li>
          {usd && <li>Documents with the shipment: commercial invoice, packing list, Bill of Lading, certificate of origin, and any certificate the buyer's country asks for.</li>}
        </ol>
      </div>
      <div className="mt-6 flex justify-between text-[11.5px] text-slate-600"><span>Customer's acceptance (sign and stamp)</span><span className="text-right">For {q.company.name}<br /><br />Authorised signatory</span></div>
      <div className="mt-4 border-t border-slate-300 pt-1 text-center text-[10.5px] text-slate-500">{q.company.name} · {q.company.address} · This quotation is made by computer and needs no stamp when it is approved</div>
    </div>
  );
}

function ReasonModal({ title, text, onClose, onOk }) {
  const [reason, setReason] = useState("");
  return (
    <Modal open onClose={onClose} title={title}>
      <p className="mb-2 text-sm text-slate-600">{text}</p>
      <Field label="Reason *"><textarea className={fieldClass} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
      <Footer onClose={onClose}><button type="button" className={btn.primary} onClick={() => onOk(reason)}>Confirm</button></Footer>
    </Modal>
  );
}

export default function QuotationDetail() {
  const { id } = useParams();
  const { has } = useSales();
  const { data: q, loading, error, reload } = useAsync(() => salesApi.quotation(id), [id]);
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [reasonFor, setReasonFor] = useState(null);
  const [find, setFind] = useState("");
  const [found, setFound] = useState([]);

  useEffect(() => {
    if (q) setForm({ party: q.party, address: q.address || "", state: q.state || "", gstin: q.gstin || "", valid_days: q.valid_days, payment_terms: q.payment_terms || "", delivery_terms: q.delivery_terms || "", warranty_terms: q.warranty_terms || "", note: q.note || "", items: q.lines.map((l) => ({ item_code: l.item_code, item_name: l.item_name, hsn: l.hsn, qty: l.qty, rate: l.rate, discount_pct: l.discount_pct, gst_pct: l.gst_pct })) });
  }, [q]);
  useEffect(() => {
    if (find.trim().length < 2) { setFound([]); return undefined; }
    const t = setTimeout(() => salesApi.items(find).then(setFound).catch(() => setFound([])), 250);
    return () => clearTimeout(t);
  }, [find]);

  const editable = q && ["draft", "ret"].includes(q.status) && has("make_quote");
  const usd = q?.currency === "USD";
  const fx = q?.fx_rate || 88;
  const setItem = (i, k, v) => setForm((s) => ({ ...s, items: s.items.map((it, n) => (n === i ? { ...it, [k]: v } : it)) }));
  const addItem = (it) => {
    const rate = usd ? Math.round((it.mrp / fx) * 100) / 100 : it.mrp;
    setForm((s) => ({ ...s, items: [...s.items, { item_code: it.item_code, item_name: it.item_name, hsn: it.hsn, qty: 1, rate, discount_pct: 0, gst_pct: String(it.hsn || "").startsWith("8415") ? 28 : 18 }] }));
    setFind(""); setFound([]);
  };
  const body = useMemo(() => form && ({ ...form, valid_days: Number(form.valid_days), items: form.items.map((i) => ({ ...i, qty: Number(i.qty), rate: Number(i.rate), discount_pct: Number(i.discount_pct), gst_pct: Number(i.gst_pct) })) }), [form]);

  async function run(fn, ok) {
    setBusy(true); setMsg("");
    try { await fn(); setMsg(ok); reload(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  const save = () => run(() => salesApi.updateQuotation(q.id, body), "Saved");
  const act = (action, reason) => run(async () => { if (editable && action === "submit") await salesApi.updateQuotation(q.id, body); await salesApi.quotationAction(q.id, action, reason); }, "Done");

  if (error) return <div><SalesTabs /><Notice tone="bad">{error}</Notice></div>;
  if (!q || !form) return <div><SalesTabs />{loading && <p className="text-sm text-slate-500">Loading...</p>}</div>;
  const s = q.status;
  const buttons = [];
  const add = (key, label, cls, fn) => buttons.push(<button key={key} type="button" className={cls} disabled={busy} onClick={fn}>{label}</button>);
  if (editable) { add("save", "Save draft", btn.plain, save); add("submit", "Submit for approval", btn.primary, () => act("submit")); }
  if (s === "wait" && has("approve_quote")) { add("ap", "Approve", btn.go, () => act("approve")); add("up", "Send to Admin / Sub Admin", btn.plain, () => act("send_up")); }
  if (s === "wadm" && has("approve_high")) add("ap2", "Approve (high discount)", btn.go, () => act("approve"));
  if (["wait", "wadm"].includes(s) && (has("approve_quote") || has("approve_high"))) { add("ret", "Return for changes", btn.plain, () => setReasonFor({ action: "return", title: "Return for changes", text: "The Sales Team gets it back with your reason." })); add("rej", "Reject", btn.danger, () => setReasonFor({ action: "reject", title: "Reject the quotation", text: "It cannot be sent. Admin or Sub Admin can still override." })); }
  if (["wait", "wadm", "rej"].includes(s) && has("override")) add("ov", "Override: approve it", btn.go, () => setReasonFor({ action: "override_approve", title: "Admin override: approve", text: "You approve over the decision or the limit. The reason is kept in the history for the team only." }));
  if (s === "appr" && has("send_quote")) add("send", "Send to the customer (mark as sent)", btn.go, () => act("send"));
  if (s === "sent") { if (has("send_quote") || has("make_quote")) { add("acc", "Customer accepted", btn.go, () => act("accept")); add("dec", "Customer declined", btn.plain, () => act("decline")); } }
  if (["appr", "sent"].includes(s) && has("override")) add("can", "Override: cancel it", btn.danger, () => setReasonFor({ action: "cancel", title: "Admin override: cancel", text: "The quotation becomes not valid. If it was sent, tell the customer." }));
  add("print", "Print or save as PDF", btn.plain, () => window.print());

  return (
    <div>
      <style>{"@media print { body * { visibility: hidden !important; } #quote-paper, #quote-paper * { visibility: visible !important; } #quote-paper { position: absolute; left: 0; top: 0; width: 100%; border: 0; box-shadow: none; } }"}</style>
      <PageTitle title={q.quote_no} sub={q.party} right={<span className={`rounded-full px-3 py-1 text-xs font-semibold ${QUOTE_TONE[s]}`}>{q.status_label}</span>} />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      {q.high_discount && ["draft", "ret", "wait", "wadm"].includes(s) && <Notice tone="warn">High discount: {q.discount_pct}% overall (the limit is {q.discount_limit}%). This quotation needs Admin or Sub Admin as well as the Sales Manager.</Notice>}
      {q.lead_id && <p className="mb-2 text-sm"><Link className="text-indcool-blue hover:underline" to={`/sales/leads/${q.lead_id}`}>Open the lead</Link></p>}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,28rem)_minmax(0,1fr)]">
        <div className="space-y-3 print:hidden">
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h3 className="mb-2 text-sm font-semibold">{editable ? "Make the quotation" : "Quotation details"}</h3>
            <Field label="Customer"><input className={fieldClass} value={form.party} disabled={!editable} onChange={(e) => setForm({ ...form, party: e.target.value })} /></Field>
            <div className="grid gap-x-3 sm:grid-cols-2">
              <Field label="Address"><input className={fieldClass} value={form.address} disabled={!editable} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
              <Field label={usd ? "Country (export: no GST)" : "State (decides CGST + SGST or IGST)"}><input className={fieldClass} value={form.state} disabled={!editable} onChange={(e) => setForm({ ...form, state: e.target.value })} /></Field>
              <Field label={usd ? "Importer registration no." : "GSTIN"}><input className={fieldClass} value={form.gstin} disabled={!editable} onChange={(e) => setForm({ ...form, gstin: e.target.value })} /></Field>
              <Field label="Valid for (days)"><input className={fieldClass} type="number" min="1" value={form.valid_days} disabled={!editable} onChange={(e) => setForm({ ...form, valid_days: e.target.value })} /></Field>
            </div>
            {usd && <p className="mb-2 text-xs text-slate-500">Export quotation in US dollars at ₹{fx} to the dollar. No GST (exported under a LUT).</p>}
            <div className="space-y-2">
              {form.items.map((it, i) => (
                <div key={i} className="rounded border border-slate-200 bg-slate-50 p-2">
                  <div className="flex items-start gap-1">
                    <input className={fieldClass} value={it.item_name} disabled={!editable} onChange={(e) => setItem(i, "item_name", e.target.value)} aria-label="Item" />
                    {editable && form.items.length > 1 && <button type="button" aria-label="Remove line" className="px-1 text-rose-600" onClick={() => setForm((st) => ({ ...st, items: st.items.filter((_x, n) => n !== i) }))}>✕</button>}
                  </div>
                  <div className="mb-1 text-[10px] text-slate-400">{it.item_code} {it.hsn ? `· HSN ${it.hsn}` : ""}</div>
                  <div className="grid grid-cols-4 gap-1 text-[11px] text-slate-500">
                    <label>Qty<input className={fieldClass} type="number" min="1" value={it.qty} disabled={!editable} onChange={(e) => setItem(i, "qty", e.target.value)} /></label>
                    <label>Rate<input className={fieldClass} type="number" min="0" step="0.01" value={it.rate} disabled={!editable} onChange={(e) => setItem(i, "rate", e.target.value)} /></label>
                    <label>Disc %<input className={fieldClass} type="number" min="0" max="40" value={it.discount_pct} disabled={!editable} onChange={(e) => setItem(i, "discount_pct", e.target.value)} /></label>
                    {!usd && <label>GST %<input className={fieldClass} type="number" min="0" max="28" value={it.gst_pct} disabled={!editable} onChange={(e) => setItem(i, "gst_pct", e.target.value)} /></label>}
                  </div>
                </div>
              ))}
            </div>
            {editable && (
              <div className="relative mt-2">
                <input className={fieldClass} placeholder="Add an item: type its code or name from the Item Master" value={find} onChange={(e) => setFind(e.target.value)} />
                {found.length > 0 && <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded border border-slate-200 bg-white text-sm shadow-lg">{found.map((it) => <li key={it.item_code}><button type="button" className="block w-full px-3 py-1.5 text-left hover:bg-sky-50" onClick={() => addItem(it)}>{it.item_name} <span className="text-xs text-slate-500">{it.item_code} · MRP ₹{it.mrp}</span></button></li>)}</ul>}
                <button type="button" className="mt-1 text-xs text-indcool-blue hover:underline" onClick={() => setForm((st) => ({ ...st, items: [...st.items, { item_code: "", item_name: "New item", hsn: "", qty: 1, rate: 0, discount_pct: 0, gst_pct: 18 }] }))}>+ Add a line by hand</button>
              </div>
            )}
            <Field label="Payment terms"><textarea className={fieldClass} rows={2} value={form.payment_terms} disabled={!editable} onChange={(e) => setForm({ ...form, payment_terms: e.target.value })} /></Field>
            <Field label="Delivery"><input className={fieldClass} value={form.delivery_terms} disabled={!editable} onChange={(e) => setForm({ ...form, delivery_terms: e.target.value })} /></Field>
            <Field label="Warranty"><input className={fieldClass} value={form.warranty_terms} disabled={!editable} onChange={(e) => setForm({ ...form, warranty_terms: e.target.value })} /></Field>
            <Field label="Note for the approver"><textarea className={fieldClass} rows={2} value={form.note} disabled={!editable} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="Why this discount, any special price" /></Field>
            <div className="flex flex-wrap gap-2">{buttons}</div>
          </section>
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h3 className="mb-2 text-sm font-semibold">History</h3>
            <ol className="space-y-2 border-l-2 border-slate-200 pl-3 text-sm">{q.history.map((h, i) => <li key={i}>{h.text}<div className="text-xs text-slate-400">{fmtDateTime(h.at)} · {h.by}</div></li>)}</ol>
          </section>
        </div>
        <div><p className="mb-1 text-xs text-slate-500 print:hidden">The quotation as the customer gets it:</p><Paper q={q} /></div>
      </div>
      {reasonFor && <ReasonModal title={reasonFor.title} text={reasonFor.text} onClose={() => setReasonFor(null)} onOk={(r) => { const a = reasonFor.action; setReasonFor(null); act(a, r); }} />}
    </div>
  );
}
