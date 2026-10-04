import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ASM_BADGE, accountsApi, accError, money } from "../../api/accounts.js";
import { fmtDateTime } from "../store/GrnList.jsx";

export default function AssemblyDetail() {
  const { id } = useParams();
  const [asm, setAsm] = useState(null);
  const [units, setUnits] = useState([]);
  const [scan, setScan] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const scanRef = useRef(null);

  function load(a) {
    setAsm(a);
    setUnits(Array.from({ length: a.qty }, () => ({ serial_no: "", serial_no_2: "" })));
  }
  useEffect(() => { accountsApi.getAssembly(id).then(load).catch((e) => setErr(accError(e, "Could not load this assembly"))); }, [id]);

  const need = asm?.serial_count ?? 0;
  const keys = need >= 2 ? ["serial_no", "serial_no_2"] : need === 1 ? ["serial_no"] : [];

  function setUnit(i, k, v) { setUnits((cur) => cur.map((u, idx) => (idx === i ? { ...u, [k]: v.toUpperCase() } : u))); }

  function onScan(e) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const v = scan.trim().toUpperCase();
    setScan("");
    if (!v) return;
    const all = units.flatMap((u) => keys.map((k) => u[k]));
    if (all.includes(v)) { setErr(`${v} is already entered.`); return; }
    setErr("");
    for (let i = 0; i < units.length; i += 1) {
      for (const k of keys) {
        if (!units[i][k]) { setUnit(i, k, v); scanRef.current?.focus(); return; }
      }
    }
    setErr("Every serial box is already filled.");
  }

  async function complete() {
    setBusy(true); setErr(""); setNote("");
    try {
      const a = await accountsApi.completeAssembly(asm.id, { units: need ? units.map((u) => ({ serial_no: u.serial_no || null, serial_no_2: u.serial_no_2 || null })) : [] });
      setAsm(a);
      setNote(`${a.asm_no} complete. The finished units are in stock and the parts are issued.`);
    } catch (e) { setErr(accError(e, "Could not complete the assembly")); }
    finally { setBusy(false); }
  }

  async function cancel() {
    setBusy(true); setErr("");
    try { setAsm(await accountsApi.cancelAssembly(asm.id)); setNote("Assembly cancelled."); }
    catch (e) { setErr(accError(e, "Could not cancel")); }
    finally { setBusy(false); }
  }

  if (!asm) return <div className="space-y-3"><Link to="/accounts/assembly" className="text-sm text-slate-500 hover:underline">&larr; Back to assembly</Link>{err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}</div>;

  const planned = asm.status === "Planned";
  const short = asm.needs.some((n) => n.short > 0);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/accounts/assembly" className="text-sm text-slate-500 hover:underline">&larr; Back to assembly</Link>
          <h1 className="text-2xl font-semibold text-slate-800">{asm.asm_no}: {asm.qty} x {asm.item_name}</h1>
          <p className="text-sm text-slate-500">BOM v{asm.bom_version}. Planned by {asm.created_by_name || "-"}{asm.completed_by_name ? `, completed by ${asm.completed_by_name} on ${fmtDateTime(asm.completed_at)}` : ""}.</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${ASM_BADGE[asm.status] || "bg-slate-100"}`}>{asm.status}</span>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {note && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{note}</div>}

      {planned && (
        <div className="crm-scroll rounded-lg bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-700"><tr><th className="px-3 py-2">Part needed</th><th className="px-3 py-2 text-right">Needed</th><th className="px-3 py-2 text-right">In store</th><th className="px-3 py-2">Check</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {asm.needs.map((n) => (
                <tr key={n.component_item_id}>
                  <td className="px-3 py-2">{n.item_name} <span className="font-mono text-xs text-slate-500">{n.item_code}</span></td>
                  <td className="px-3 py-2 text-right">{n.needed}</td>
                  <td className="px-3 py-2 text-right">{n.in_store}</td>
                  <td className="px-3 py-2">{n.short > 0 ? <span className="font-semibold text-rose-700">Short {n.short}. Raise a purchase order.</span> : <span className="text-emerald-700">Enough</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {asm.unit_cost != null && <p className="border-t border-slate-100 px-4 py-2 text-sm text-slate-600">Expected cost per finished unit: {money(asm.unit_cost)}</p>}
        </div>
      )}

      {planned && asm.can_complete && need > 0 && (
        <div className="space-y-3 rounded-lg bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800">Serial numbers of the finished units</h2>
          <input ref={scanRef} value={scan} onChange={(e) => setScan(e.target.value)} onKeyDown={onScan} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Click here and scan. Each scan fills the next empty box." />
          <div className="space-y-2">
            {units.map((u, i) => (
              <div key={i} className="grid grid-cols-1 items-center gap-2 md:grid-cols-5">
                <div className="text-sm text-slate-600">Unit {i + 1}</div>
                {keys.map((k, j) => (
                  <input key={k} value={u[k]} onChange={(e) => setUnit(i, k, e.target.value)} placeholder={`Serial ${j + 1}`} className="rounded-md border border-slate-300 px-3 py-2 font-mono text-sm md:col-span-2" />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {planned && (
        <div className="flex flex-wrap items-center gap-2">
          {asm.can_complete && <button type="button" disabled={busy} onClick={complete} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">Complete assembly</button>}
          {asm.can_cancel && <button type="button" disabled={busy} onClick={cancel} className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">Cancel</button>}
          {!asm.can_complete && short && <span className="text-sm text-rose-700">Receive the missing parts first, then complete the assembly.</span>}
          {!asm.can_complete && !short && <span className="text-sm text-slate-500">Completing an assembly is done by the store.</span>}
        </div>
      )}

      {asm.status === "Completed" && (
        <div className="crm-scroll rounded-lg bg-white shadow-sm">
          <h2 className="px-4 pt-3 text-base font-semibold text-slate-800">Unit passport: parts that went in</h2>
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-700"><tr><th className="px-3 py-2">Finished serial</th><th className="px-3 py-2">Part</th><th className="px-3 py-2">Part serial</th><th className="px-3 py-2 text-right">Qty</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {asm.parts.map((p, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 font-mono text-xs">{p.finished_serial || "-"}</td>
                  <td className="px-3 py-2">{p.item_name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{p.component_serial || "by quantity"}</td>
                  <td className="px-3 py-2 text-right">{p.qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
