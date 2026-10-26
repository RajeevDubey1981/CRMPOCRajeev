import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";

export default function InstallationReturns({ rows = [], orderId, installationId, onUpdated }) {
  const { user } = useAuth();
  const [returns, setReturns] = useState([]);
  const [remarks, setRemarks] = useState({});
  const [err, setErr] = useState("");
  const remarkFields = useRef({});
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    const { data } = await api.get("/api/installation-returns", { params: { order_id: orderId || undefined, installation_id: installationId || undefined } });
    setReturns(installationId ? data.filter(r => r.id === Number(installationId)) : orderId ? data : data.filter(r => rows.some(row => Number(row.id) === r.id)));
  }
  useEffect(() => { load().catch(e => setErr(e.response?.data?.detail || "Could not load returns")); }, [orderId, installationId, user?.id]);
  async function act(fn) {
    setErr(""); setSuccess(""); setBusy(true);
    try { await fn(); await load(); await onUpdated?.(); }
    catch (e) { setErr(typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Could not save return. Enter a reason and try again."); }
    finally { setBusy(false); }
  }
  async function decideReturn(row, decision) {
    const remark = (remarks[row.id] || "").trim();
    if (remark.length < 2) {
      setSuccess("");
      setErr("Enter a review remark of at least 2 characters before approving or rejecting the return.");
      remarkFields.current[row.id]?.focus();
      return;
    }
    await act(async () => {
      const { data } = await api.post(`/api/installation-returns/${row.id}/decision`, { decision, remark });
      setSuccess(decision === "reject"
        ? `Return rejected. Installation #${row.id} is back at ${data.status}; the serial remains assigned to the engineer.`
        : `Installation #${row.id}: ${data.status}.`);
    });
  }
  const field = "rounded border border-slate-300 px-3 py-2 text-sm";
  if (!returns.length && !err) return null;
  const pending = returns.filter(row => row.status === "Pending Return Approval");
  if (!installationId) return <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
    <h2 className="font-semibold text-slate-800">Serial return history</h2>
    {err && <p role="alert" className="text-sm text-rose-700">{err}</p>}
    {returns.map(row => <Link key={row.id} to={`/installations/${row.id}`} className={`block rounded-md border px-3 py-2 text-sm font-semibold ${row.status === "Pending Return Approval" ? "installation-return-alert border-red-500 bg-red-50 text-red-800" : "border-slate-200 text-slate-700"}`}>
      Installation #{row.id} - {row.status} - View return details
    </Link>)}
  </section>;
  return <section className={`space-y-3 rounded-lg border-2 p-4 ${pending.length ? "installation-return-alert border-red-500 bg-red-50" : "border-amber-300 bg-amber-50"}`}>
    <h2 className={`font-semibold ${pending.length ? "text-red-800" : "text-slate-800"}`}>{pending.length ? "Pending Return Approval" : "Serial return history"}</h2>
    {err && <p role="alert" className="text-sm text-rose-700">{err}</p>}
    {success && <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{success}</p>}
    {returns.map(row => <article key={row.id} className="space-y-2 rounded border border-amber-300 bg-white p-3 text-sm">
      <div className="font-semibold">Installation #{row.id} - {row.status}</div>
      <div>Order {row.order_no || "-"} | {row.product_name} | {row.item_code}</div>
      <div className="font-mono">{row.serial_no} / {row.serial_no_2 || "-"}</div>
      <div>Engineer: {row.engineer_name}</div>
      {row.status === "Return Approved - Closed" && <p className="text-sm font-medium text-slate-700">This installation row is closed. The serial remains on the order and can be used in a new installation request.</p>}
      {row.history.map((h, i) => <p key={i}>{new Date(h.at).toLocaleString()} - {h.action} by {h.actor_name || (h.actor_id ? `User #${h.actor_id}` : "System")}: {h.remark}</p>)}
      {row.can_review && row.status === "Pending Return Approval" && <div className="flex flex-wrap gap-2">
        <label className="block w-full text-sm font-medium text-slate-700">
          Review remark <span className="text-rose-600">* (required)</span>
          <textarea ref={element => { remarkFields.current[row.id] = element; }} aria-label={`Review remark for ${row.id}`} required minLength={2} rows={2} className={`${field} mt-1 block w-full font-normal`} placeholder="Explain your approval or why the engineer should continue the installation" value={remarks[row.id] || ""} disabled={busy} onChange={e => { setRemarks(s => ({...s, [row.id]: e.target.value})); setErr(""); }} />
          <span className="mt-1 block text-xs font-normal text-slate-500">Reject return keeps the serial assigned and sends the row back to its previous installation stage.</span>
        </label>
        {[["approve", "Approve return"], ["reject", "Reject return"]].map(([decision, label]) => <button key={decision} type="button" className={`${field} bg-amber-50 disabled:cursor-wait disabled:opacity-50`} disabled={busy} onClick={() => decideReturn(row, decision)}>{busy ? "Saving..." : label}</button>)}
      </div>}
    </article>)}
  </section>;
}
