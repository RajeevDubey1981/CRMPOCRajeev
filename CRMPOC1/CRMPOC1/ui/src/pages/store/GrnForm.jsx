import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { storeApi, storeError } from "../../api/store.js";
import { accountsApi } from "../../api/accounts.js";
import CameraScan from "../../components/scan/CameraScan.jsx";
import { GRN_BADGE, fmtDateTime } from "./GrnList.jsx";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";
const MODES = [["scanner", "Scanner"], ["camera", "Phone camera"], ["type", "Type it"]];

const EMPTY_HEAD = { source_type: "Purchase", supplier_name: "", reference_no: "", remarks: "", po_id: "" };

export default function GrnForm() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const canOverride = hasPermission(user, "store_receiving", "can_delete");
  const canCreate = hasPermission(user, "store_receiving", "can_create");

  const [meta, setMeta] = useState({ sources: ["Purchase"], stock_types: ["Fresh", "Spare", "Returned"], conditions: ["OK", "Damaged"], maker_checker: true });
  const [grn, setGrn] = useState(null);
  const [head, setHead] = useState(EMPTY_HEAD);
  const [lines, setLines] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);

  const [itemQuery, setItemQuery] = useState("");
  const [itemList, setItemList] = useState([]);
  const [item, setItem] = useState(null);
  const [stockType, setStockType] = useState("Fresh");
  const [condition, setCondition] = useState("OK");
  const [unitCost, setUnitCost] = useState("");
  const [bin, setBin] = useState("");
  const [qty, setQty] = useState(1);
  const [mode, setMode] = useState("scanner");
  const [s1, setS1] = useState("");
  const [s2, setS2] = useState("");
  const [serialInput, setSerialInput] = useState("");
  const [capMsg, setCapMsg] = useState({ text: "", error: false });
  const inputRef = useRef(null);

  const editable = isNew ? canCreate : grn?.status === "Draft" && (grn.created_by === user?.id || canOverride);

  const [openPos, setOpenPos] = useState([]);

  useEffect(() => { if (location.state?.err) setErr(location.state.err); }, [location.state]);
  useEffect(() => { storeApi.meta().then(setMeta).catch(() => {}); }, []);
  useEffect(() => { accountsApi.openPos().then(setOpenPos).catch(() => {}); }, []);

  function pickPo(value) {
    const po = openPos.find((p) => String(p.id) === String(value));
    setHead((h) => ({ ...h, po_id: value, supplier_name: po && !h.supplier_name ? po.supplier_name || "" : h.supplier_name }));
  }

  useEffect(() => {
    if (isNew) return;
    storeApi.getGrn(id).then((g) => {
      setGrn(g);
      setHead({ source_type: g.source_type, supplier_name: g.supplier_name || "", reference_no: g.reference_no || "", remarks: g.remarks || "", po_id: g.po_id ? String(g.po_id) : "" });
      setLines(g.lines.map((l) => ({ ...l, key: `l${l.id}`, via: "Saved" })));
    }).catch((e) => setErr(storeError(e, "Could not load this GRN")));
  }, [id, isNew]);

  useEffect(() => {
    if (!editable) return undefined;
    const t = setTimeout(() => { storeApi.lookupItems(itemQuery).then(setItemList).catch(() => {}); }, 250);
    return () => clearTimeout(t);
  }, [itemQuery, editable]);

  function pickItem(value) {
    const it = itemList.find((x) => String(x.id) === String(value)) || null;
    setItem(it);
    setS1(""); setS2(""); setSerialInput(""); setCapMsg({ text: "", error: false });
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  const need = item?.serial_count ?? 0;
  const nextSlot = !s1 ? 1 : (need >= 2 && !s2 ? 2 : 0);

  function cap(text, error = false) { setCapMsg({ text, error }); }

  function usedSerials() {
    const used = new Set();
    lines.forEach((l) => { if (l.serial_no) used.add(l.serial_no.toUpperCase()); if (l.serial_no_2) used.add(l.serial_no_2.toUpperCase()); });
    return used;
  }

  function pushLine(serialA, serialB, via) {
    setLines((cur) => [...cur, {
      key: `n${Date.now()}${Math.random()}`, item_id: item.id, item_code: item.item_code, item_name: item.item_name,
      serial_count: item.serial_count, stock_type: stockType, serial_no: serialA || null, serial_no_2: serialB || null,
      qty: serialA ? 1 : Number(qty) || 1, unit_cost: unitCost === "" ? null : unitCost, condition, bin_location: bin || null, via,
    }]);
  }

  async function addSerial(raw, via) {
    const v = String(raw || "").trim().toUpperCase();
    setSerialInput("");
    if (!v) return;
    if (!item) { cap("Pick the item first.", true); return; }
    if (need === 0) { cap("This item is counted by quantity, so no serial is needed.", true); return; }
    if (usedSerials().has(v) || v === s1) { cap(`${v} is already captured on this GRN. Duplicates are blocked.`, true); return; }
    try {
      const res = await storeApi.checkSerial(v, grn?.id);
      if (!res.ok) { cap(res.reason, true); return; }
    } catch (e) { cap(storeError(e, "Could not check the serial"), true); return; }
    if (!s1) {
      if (need === 1) { pushLine(v, null, via); cap(`${v} added (${via}).`); return; }
      setS1(v); cap(`${v} captured as serial 1 (${via}). Now serial 2.`);
    } else {
      pushLine(s1, v, via); setS1(""); cap(`${s1} and ${v} added (${via}).`);
    }
    setTimeout(() => inputRef.current?.focus(), 30);
  }

  function addQuantity() {
    if (!item) { cap("Pick the item first.", true); return; }
    if (!(Number(qty) > 0)) { cap("Enter a quantity above zero.", true); return; }
    pushLine(null, null, "Typed");
    cap(`${qty} x ${item.item_name} added.`);
  }

  function removeLine(key) { setLines((cur) => cur.filter((l) => l.key !== key)); }

  const payload = useMemo(() => ({
    source_type: head.source_type,
    supplier_name: head.supplier_name || null,
    reference_no: head.reference_no || null,
    remarks: head.remarks || null,
    po_id: head.po_id ? Number(head.po_id) : null,
    lines: lines.map((l) => ({
      item_id: l.item_id, stock_type: l.stock_type, serial_no: l.serial_no || null, serial_no_2: l.serial_no_2 || null,
      qty: Number(l.qty) || 1, unit_cost: l.unit_cost === "" || l.unit_cost == null ? null : Number(l.unit_cost),
      condition: l.condition, bin_location: l.bin_location || null,
    })),
  }), [head, lines]);

  async function save(thenSubmit = false) {
    setBusy(true); setErr(""); setNote("");
    try {
      let g = isNew ? await storeApi.createGrn(payload) : await storeApi.updateGrn(grn.id, payload);
      if (thenSubmit) {
        try { g = await storeApi.submitGrn(g.id); } catch (e2) {
          const msg = `Saved as a draft, but it could not be submitted: ${storeError(e2, "submit failed")}`;
          if (isNew) { navigate(`/store/grns/${g.id}`, { replace: true, state: { err: msg } }); return; }
          setGrn(g); setLines(g.lines.map((l) => ({ ...l, key: `l${l.id}`, via: "Saved" }))); setErr(msg); return;
        }
      }
      if (isNew) { navigate(`/store/grns/${g.id}`, { replace: true }); return; }
      setGrn(g); setLines(g.lines.map((l) => ({ ...l, key: `l${l.id}`, via: "Saved" })));
      setNote(thenSubmit ? "Submitted. A manager must approve it before the stock changes." : "Draft saved.");
    } catch (e) { setErr(storeError(e, "Could not save the GRN")); }
    finally { setBusy(false); }
  }

  async function act(fn, okText) {
    setBusy(true); setErr(""); setNote("");
    try {
      const g = await fn();
      setGrn(g); setLines(g.lines.map((l) => ({ ...l, key: `l${l.id}`, via: "Saved" })));
      setNote(okText); setShowReject(false); setRejectReason("");
    } catch (e) { setErr(storeError(e, "That did not work")); }
    finally { setBusy(false); }
  }

  async function removeDraft() {
    if (!window.confirm("Delete this draft GRN?")) return;
    setBusy(true);
    try { await storeApi.deleteGrn(grn.id); navigate("/store/grns", { replace: true }); }
    catch (e) { setErr(storeError(e, "Could not delete")); setBusy(false); }
  }

  const slotLabel = nextSlot === 2 ? "serial 2" : "serial 1";
  const totalUnits = lines.reduce((s, l) => s + (Number(l.qty) || 1), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/store/grns" className="text-sm text-slate-500 hover:underline">&larr; Back to GRNs</Link>
          <h1 className="text-2xl font-semibold text-slate-800">{isNew ? "New GRN" : grn?.grn_no || "GRN"}</h1>
        </div>
        {grn && <span className={`rounded-full px-3 py-1 text-sm font-semibold ${GRN_BADGE[grn.status] || "bg-slate-100"}`}>{grn.status}</span>}
      </div>

      {grn?.reject_reason && <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">Sent back: {grn.reject_reason}</div>}
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {note && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{note}</div>}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div>
            <label className={labelClass}>Received from</label>
            <select disabled={!editable} value={head.source_type} onChange={(e) => setHead({ ...head, source_type: e.target.value })} className={fieldClass}>
              {meta.sources.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Bill, challan or LR no *</label>
            <input disabled={!editable} value={head.reference_no} onChange={(e) => setHead({ ...head, reference_no: e.target.value })} className={fieldClass} placeholder="e.g. COM/143" />
          </div>
          <div>
            <label className={labelClass}>Supplier</label>
            <input disabled={!editable} value={head.supplier_name} onChange={(e) => setHead({ ...head, supplier_name: e.target.value })} className={fieldClass} placeholder="OEM or supplier name" />
          </div>
          <div>
            <label className={labelClass}>Remarks</label>
            <input disabled={!editable} value={head.remarks} onChange={(e) => setHead({ ...head, remarks: e.target.value })} className={fieldClass} />
          </div>
        </div>
        {head.source_type === "Purchase" && (openPos.length > 0 || head.po_id) && (
          <div className="mt-3 md:w-1/2">
            <label className={labelClass}>Against purchase order (optional)</label>
            <select disabled={!editable} value={head.po_id} onChange={(e) => pickPo(e.target.value)} className={fieldClass}>
              <option value="">Not against a purchase order</option>
              {openPos.map((p) => <option key={p.id} value={p.id}>{p.po_no} - {p.supplier_name}</option>)}
              {grn?.po_id && !openPos.find((p) => p.id === grn.po_id) && <option value={grn.po_id}>{grn.po_no}</option>}
            </select>
            {head.po_id && openPos.find((p) => String(p.id) === String(head.po_id)) && (
              <p className="mt-1 text-xs text-slate-500">Still to receive: {openPos.find((p) => String(p.id) === String(head.po_id)).lines.map((l) => `${l.outstanding} x ${l.item_name}`).join(", ")}</p>
            )}
          </div>
        )}
        {grn && (
          <p className="mt-3 text-xs text-slate-500">
            Created by {grn.created_by_name || "-"} on {fmtDateTime(grn.created_at)}
            {grn.approved_by_name ? `. Approved by ${grn.approved_by_name} on ${fmtDateTime(grn.approved_at)}.` : ""}
          </p>
        )}
      </div>

      {editable && (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-slate-800">Add goods</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <div className="md:col-span-2">
              <label className={labelClass}>Item (from the Item Master)</label>
              <input value={itemQuery} onChange={(e) => setItemQuery(e.target.value)} className={`${fieldClass} mb-2`} placeholder="Search item name or code" />
              <select value={item?.id || ""} onChange={(e) => pickItem(e.target.value)} className={fieldClass}>
                <option value="">Select an item</option>
                {itemList.map((it) => (
                  <option key={it.id} value={it.id}>{it.item_name} ({it.item_code}) - {it.serial_count === 0 ? "by quantity" : `${it.serial_count} serial${it.serial_count > 1 ? "s" : ""}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Stock type</label>
              <select value={stockType} onChange={(e) => setStockType(e.target.value)} className={fieldClass}>
                {meta.stock_types.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Condition</label>
              <select value={condition} onChange={(e) => setCondition(e.target.value)} className={fieldClass}>
                {meta.conditions.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Unit cost (optional)</label>
              <input type="number" min="0" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} className={fieldClass} />
            </div>
            <div>
              <label className={labelClass}>Bin location (optional)</label>
              <input value={bin} onChange={(e) => setBin(e.target.value)} className={fieldClass} placeholder="e.g. A-01-2" />
            </div>
          </div>

          {item && need > 0 && (
            <div className="mt-4 rounded-md border border-slate-200 p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                {MODES.map(([k, label]) => (
                  <button key={k} type="button" onClick={() => setMode(k)} className={`rounded-full px-3 py-1 text-sm ${mode === k ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{label}</button>
                ))}
                <span className="text-sm text-slate-500">Next: {slotLabel}{s1 ? ` (serial 1 is ${s1})` : ""}</span>
              </div>
              {mode === "camera" && <div className="mb-2"><CameraScan onCode={(c) => addSerial(c, "Phone camera")} /></div>}
              <div className="flex flex-wrap gap-2">
                <input
                  ref={inputRef}
                  value={serialInput}
                  onChange={(e) => setSerialInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSerial(serialInput, mode === "type" ? "Typed" : "Scanner"); } }}
                  placeholder={mode === "type" ? `Type ${slotLabel}, then Enter` : `Click here, then scan ${slotLabel}`}
                  className={`${fieldClass} flex-1`}
                  aria-label="Serial number"
                />
                <button type="button" onClick={() => addSerial(serialInput, mode === "type" ? "Typed" : "Scanner")} className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50">Add serial</button>
              </div>
              <p className="mt-2 text-xs text-slate-500">A USB or Bluetooth scanner types the serial and presses Enter by itself. Typed serials get the same checks and are marked Typed.</p>
            </div>
          )}

          {item && need === 0 && (
            <div className="mt-4 flex flex-wrap items-end gap-2 rounded-md border border-slate-200 p-3">
              <div>
                <label className={labelClass}>Quantity</label>
                <input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} className={`${fieldClass} w-32`} />
              </div>
              <button type="button" onClick={addQuantity} className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50">Add quantity</button>
            </div>
          )}

          {capMsg.text && <p className={`mt-3 text-sm ${capMsg.error ? "text-rose-700" : "text-emerald-700"}`}>{capMsg.text}</p>}
        </div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Item</th>
              <th className="px-3 py-2">Serial 1</th>
              <th className="px-3 py-2">Serial 2</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2">Stock type</th>
              <th className="px-3 py-2">Condition</th>
              <th className="px-3 py-2">Bin</th>
              <th className="px-3 py-2">Entered by</th>
              {editable && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lines.length === 0 && <tr><td colSpan={9} className="px-3 py-6 text-center text-slate-500">Nothing added yet.</td></tr>}
            {lines.map((l) => (
              <tr key={l.key}>
                <td className="px-3 py-2">{l.item_name} <span className="text-xs text-slate-500">({l.item_code})</span></td>
                <td className="px-3 py-2 font-mono text-xs">{l.serial_no || "-"}</td>
                <td className="px-3 py-2 font-mono text-xs">{l.serial_no_2 || "-"}</td>
                <td className="px-3 py-2 text-right">{l.qty}</td>
                <td className="px-3 py-2">{l.stock_type}</td>
                <td className="px-3 py-2"><span className={l.condition === "Damaged" ? "font-semibold text-rose-700" : ""}>{l.condition}</span></td>
                <td className="px-3 py-2 text-slate-600">{l.bin_location || "-"}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{l.via}</td>
                {editable && <td className="px-3 py-2"><button type="button" onClick={() => removeLine(l.key)} className="text-rose-600 hover:underline">Remove</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-sm text-slate-600">{lines.length} line(s), {totalUnits} unit(s). Damaged goods go to quarantine and cannot be issued.</div>

      <div className="flex flex-wrap items-center gap-2">
        {editable && (
          <>
            <button disabled={busy} onClick={() => save(false)} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50">Save draft</button>
            <button disabled={busy || lines.length === 0} onClick={() => save(true)} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">Submit for approval</button>
            {!isNew && <button disabled={busy} onClick={removeDraft} className="ml-auto rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">Delete draft</button>}
          </>
        )}
        {grn?.status === "Pending Approval" && grn.can_approve && (
          <>
            <button disabled={busy} onClick={() => act(() => storeApi.approveGrn(grn.id), "Approved and posted. The units are now in stock.")} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">Approve and post</button>
            <button disabled={busy} onClick={() => setShowReject((v) => !v)} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Send back</button>
          </>
        )}
        {grn?.status === "Pending Approval" && !grn.can_approve && (
          <span className="text-sm text-slate-500">
            {meta.maker_checker && grn.created_by === user?.id ? "You created this GRN, so someone else must approve it." : "Waiting for a manager to approve."}
          </span>
        )}
      </div>

      {showReject && (
        <div className="flex flex-wrap gap-2 rounded-lg bg-white p-4 shadow-sm">
          <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Why is it being sent back?" className={`${fieldClass} flex-1`} />
          <button disabled={busy || rejectReason.trim().length < 3} onClick={() => act(() => storeApi.rejectGrn(grn.id, rejectReason.trim()), "Sent back to the keeper.")} className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50">Send back</button>
        </div>
      )}
    </div>
  );
}
