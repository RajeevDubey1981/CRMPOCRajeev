import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { storeApi, storeError } from "../../api/store.js";
import { CameraScan } from "./GrnForm.jsx";
import { STAGE_BADGE } from "./DispatchList.jsx";
import { fmtDateTime } from "./GrnList.jsx";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";
const norm = (s) => (s || "").trim().toUpperCase();

export default function DispatchDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [couriers, setCouriers] = useState([]);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [scans, setScans] = useState([]);
  const [scanText, setScanText] = useState("");
  const [camera, setCamera] = useState(false);
  const [courierId, setCourierId] = useState("");
  const [lrn, setLrn] = useState("");
  const [remarks, setRemarks] = useState("");
  const [confirmRelease, setConfirmRelease] = useState(false);
  const scanRef = useRef(null);

  function say(text, error = false) { setMsg({ text, error }); }

  async function load() {
    try { setOrder(await storeApi.getOrder(id)); } catch (e) { say(storeError(e, "Failed to load the order"), true); }
  }

  useEffect(() => {
    load();
    storeApi.lookupCouriers().then(setCouriers).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const held = (order?.lines || []).filter((l) => l.unit_status === "Reserved");
  const scannedFor = (l) => scans.includes(norm(l.serial_no)) || (l.serial_no_2 && scans.includes(norm(l.serial_no_2)));
  const needScan = held.filter((l) => l.serial_no);
  const scannedCount = needScan.filter(scannedFor).length;

  function addScan(raw) {
    const code = norm(raw);
    if (!code) return;
    const hit = held.find((l) => norm(l.serial_no) === code || norm(l.serial_no_2) === code);
    if (!hit) { say(`${code} is not reserved for this order.`, true); return; }
    if (scans.includes(code)) { say(`${code} is already scanned.`, true); return; }
    setScans((cur) => [...cur, code]);
    say(`${code} matched.`);
  }

  function onScanKey(e) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    addScan(scanText);
    setScanText("");
    scanRef.current?.focus();
  }

  async function run(fn, okText) {
    setBusy(true);
    setMsg(null);
    try { const out = await fn(); return out; } catch (e) { say(storeError(e, "That did not work"), true); } finally { setBusy(false); }
    return null;
  }

  async function reserve() {
    const out = await run(() => storeApi.reserveOrder(id));
    if (!out) return;
    setOrder(out.order);
    if (out.short?.length) say(`Reserved ${out.reserved}. Still short: ${out.short.map((s) => `${s.missing} x ${s.item_name || s.item_code}`).join(", ")}.`, true);
    else say(`Reserved ${out.reserved} unit(s), oldest stock first.`);
  }

  async function release() {
    const out = await run(() => storeApi.releaseOrder(id));
    if (!out) return;
    setOrder(out);
    setScans([]);
    setConfirmRelease(false);
    say("Reserved stock went back to the shelf.");
  }

  async function dispatch() {
    if (needScan.length && scannedCount < needScan.length) { say(`Scan every unit first. ${needScan.length - scannedCount} still to scan.`, true); return; }
    if (!courierId) { say("Choose the courier.", true); return; }
    if (!lrn.trim()) { say("Enter the LR number.", true); return; }
    const out = await run(() => storeApi.dispatchOrder(id, { scans, courier_id: Number(courierId), lrn_no: lrn.trim(), remarks: remarks.trim() || null }));
    if (!out) return;
    setOrder(out);
    say(`${out.dispatch_no} done. The order is now Shipped.`);
  }

  if (!order) {
    return <div className="space-y-3"><Link to="/store/dispatch" className="text-sm text-brand-700 hover:underline">&larr; Back to dispatch</Link>{msg && <div className={`rounded-md px-3 py-2 text-sm ${msg.error ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"}`}>{msg.text}</div>}</div>;
  }

  const stage = order.stage;
  const dispatched = stage === "Dispatched";

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Link to="/store/dispatch" className="text-sm text-brand-700 hover:underline">&larr; Back to dispatch</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Order {order.order_no || `#${order.id}`}</h1>
        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${STAGE_BADGE[stage] || "bg-slate-100"}`}>{stage}</span>
      </div>

      {msg && <div className={`rounded-md px-3 py-2 text-sm ${msg.error ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"}`}>{msg.text}</div>}

      <section className="grid grid-cols-1 gap-4 rounded-lg bg-white p-5 shadow-sm md:grid-cols-3">
        <div><div className="text-xs text-slate-500">Customer</div><div className="text-sm font-medium">{order.customer_name || "-"}</div><div className="text-xs text-slate-500">{order.customer_city || ""}</div></div>
        <div><div className="text-xs text-slate-500">Ship to</div><div className="text-sm">{order.customer_address || "-"}</div></div>
        <div>
          <div className="text-xs text-slate-500">Bill or invoice no</div>
          <div className="font-mono text-sm font-bold">{order.oem_bill_no || "Not entered yet"}</div>
          {!order.oem_bill_no && <div className="text-xs text-amber-700">Admin enters it on the order. No bill number, no issue.</div>}
        </div>
      </section>

      <section className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">Item</th><th className="px-3 py-2">Serial 1</th><th className="px-3 py-2">Serial 2</th><th className="px-3 py-2">Stock</th><th className="px-3 py-2">Scan</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {order.lines.map((l) => (
              <tr key={l.order_item_id}>
                <td className="px-3 py-2">{l.item_name || l.item_code}</td>
                <td className="px-3 py-2 font-mono text-xs">{l.serial_no || (l.unit_status && l.serial_count === 0 ? "by quantity" : "-")}</td>
                <td className="px-3 py-2 font-mono text-xs">{l.serial_no_2 || "-"}</td>
                <td className="px-3 py-2">
                  {l.unit_status
                    ? <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${l.unit_status === "Issued" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{l.unit_status}</span>
                    : <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-800">Not reserved</span>}
                </td>
                <td className="px-3 py-2">
                  {l.unit_status === "Reserved" && l.serial_no && (scannedFor(l) ? <span className="font-semibold text-emerald-700">Scanned</span> : <span className="text-slate-400">To scan</span>)}
                  {l.unit_status === "Reserved" && !l.serial_no && <span className="text-slate-400">No scan needed</span>}
                  {l.unit_status === "Issued" && <span className="text-emerald-700">Sent</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {stage === "Needs stock" && (
        <section className="space-y-3 rounded-lg bg-white p-5 shadow-sm">
          <div className="text-sm text-slate-700">
            {order.stock_check.map((s) => (
              <div key={s.item_id}>{s.item_name}: needs {s.needed}, {s.available} free in the store{s.available < s.needed ? <span className="font-semibold text-rose-700"> (short {s.needed - s.available}, receive more with a GRN)</span> : ""}.</div>
            ))}
          </div>
          {order.can_reserve && <button type="button" disabled={busy} onClick={reserve} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Reserve stock (oldest first)</button>}
        </section>
      )}

      {stage === "Waiting for bill" && (
        <section className="rounded-lg bg-amber-50 p-5 text-sm text-amber-900 shadow-sm">
          Stock is held for this order. It cannot go out until the bill number is on the order.
        </section>
      )}

      {stage === "Ready to dispatch" && order.can_dispatch && (
        <section className="space-y-4 rounded-lg bg-white p-5 shadow-sm">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Scan the units</h2>
              <div className="text-sm text-slate-600">{scannedCount} of {needScan.length} scanned</div>
            </div>
            <div className="mb-2 flex gap-2">
              <button type="button" onClick={() => setCamera(false)} className={`rounded-full px-3 py-1 text-sm ${!camera ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700"}`}>Scanner or type</button>
              <button type="button" onClick={() => setCamera(true)} className={`rounded-full px-3 py-1 text-sm ${camera ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700"}`}>Phone camera</button>
            </div>
            {camera && <div className="mb-2"><CameraScan onCode={addScan} /></div>}
            <input
              ref={scanRef}
              autoFocus
              value={scanText}
              onChange={(e) => setScanText(e.target.value)}
              onKeyDown={onScanKey}
              placeholder="Click here, then scan a serial and it presses Enter by itself"
              className={fieldClass}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className={labelClass}>Courier <span className="text-red-500">*</span></label>
              <select value={courierId} onChange={(e) => setCourierId(e.target.value)} className={fieldClass}>
                <option value="">Choose courier</option>
                {couriers.map((c) => <option key={c.id} value={c.id}>{c.courier_name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>LR number <span className="text-red-500">*</span></label>
              <input value={lrn} onChange={(e) => setLrn(e.target.value)} className={fieldClass} />
            </div>
            <div>
              <label className={labelClass}>Remarks</label>
              <input value={remarks} onChange={(e) => setRemarks(e.target.value)} className={fieldClass} />
            </div>
          </div>
          <button type="button" disabled={busy} onClick={dispatch} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Dispatch order</button>
        </section>
      )}

      {dispatched && (
        <section className="rounded-lg bg-emerald-50 p-5 text-sm text-emerald-900 shadow-sm">
          <div className="font-semibold">{order.dispatch_no} sent {fmtDateTime(order.dispatched_at)}</div>
          <div>Courier {order.courier_name || "-"}, LR {order.lrn_no || "-"}. Order status is {order.status}.</div>
        </section>
      )}

      {order.can_release && (
        <div className="flex items-center gap-3">
          {!confirmRelease && <button type="button" onClick={() => setConfirmRelease(true)} className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">Release reserved stock</button>}
          {confirmRelease && (
            <>
              <span className="text-sm text-slate-700">Put the reserved units back on the shelf?</span>
              <button type="button" disabled={busy} onClick={release} className="rounded-md bg-rose-600 px-3 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50">Yes, release</button>
              <button type="button" onClick={() => setConfirmRelease(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Keep</button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
