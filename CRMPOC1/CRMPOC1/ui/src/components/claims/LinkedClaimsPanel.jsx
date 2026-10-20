import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { shortageClaimsApi, RESP_LABEL } from "../../api/shortageClaims.js";

const APPROVAL_CAP_AMOUNT = 2500;

function stageLabel(stage) {
  if (stage === "done") return "Closed";
  if (stage === "rejected") return "Rejected";
  if (stage === "sub") return "Pending Admin";
  return "Pending Service Manager";
}

/**
 * Claims already raised against this request/unit/part — shown inline wherever that thing is being
 * decided, with the same decide/approve/reject actions the standalone Claims page has, so nobody has
 * to leave this screen to act on a claim someone else already raised here.
 */
export default function LinkedClaimsPanel({ claims, onChanged, isServiceManager = false }) {
  const [parties, setParties] = useState({ vendors: [], couriers: [] });
  const [forms, setForms] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [err, setErr] = useState("");

  const needsParties = (claims || []).some((c) => c.can_approve && c.stage === "svm" && !c.responsible_type);
  useEffect(() => {
    if (needsParties) shortageClaimsApi.parties().then(setParties).catch(() => {});
  }, [needsParties]);

  if (!claims || claims.length === 0) return null;

  function setForm(id, patch) {
    setForms((cur) => ({ ...cur, [id]: { ...(cur[id] || {}), ...patch } }));
  }

  async function saveDecision(c) {
    const f = forms[c.id] || {};
    if (!f.respType) { setErr("Pick who this claim is on"); return; }
    const body = { responsible_type: f.respType };
    if (f.respType === "mfg") body.vendor_id = Number(f.vendorId);
    if (f.respType === "trans") body.courier_id = Number(f.courierId);
    if (f.respType === "ins") body.insurer_name = f.insurer;
    if (f.amount) body.amount = Number(f.amount);
    setBusyId(c.id); setErr("");
    try {
      await shortageClaimsApi.decide(c.id, body);
      onChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not save the decision");
    } finally {
      setBusyId(null);
    }
  }

  async function doApprove(c) {
    setBusyId(c.id); setErr("");
    try {
      await shortageClaimsApi.approve(c.id);
      onChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not approve");
    } finally {
      setBusyId(null);
    }
  }

  async function doReject(c) {
    const reason = (forms[c.id]?.rejectReason || "").trim();
    if (!reason) { setErr("Give a reason to reject"); return; }
    setBusyId(c.id); setErr("");
    try {
      await shortageClaimsApi.reject(c.id, reason);
      onChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not reject");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-2">
      {claims.map((c) => {
        const f = forms[c.id] || {};
        const canDecideParty = c.can_approve && c.stage === "svm" && !c.responsible_type;
        const canAct = (c.can_act || c.can_approve) && (c.stage === "svm" || c.stage === "sub");
        return (
          <div key={c.id} className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm">
            <div>
              <Link to="/claims" className="font-mono font-semibold text-brand-700 hover:underline">{c.claim_no}</Link>
              {" — "}{stageLabel(c.stage)}
              {c.raised_by_name && <span className="text-slate-500"> · raised by {c.raised_by_name}</span>}
            </div>
            {c.responsible_type && (
              <div className="mt-1 text-xs text-slate-600">
                On {RESP_LABEL[c.responsible_type]}{c.party_name ? ` — ${c.party_name}` : ""}
                {c.amount != null && ` · ₹${Number(c.amount).toLocaleString("en-IN")}`}
              </div>
            )}
            {canDecideParty && (
              <div className="mt-2 rounded-md border border-slate-200 bg-white p-2">
                <div className="grid grid-cols-4 gap-1.5">
                  {[["mfg", "Manufacturer"], ["trans", "Transporter"], ["ins", "Insurance"], ["company", "Company"]].map(([k, l]) => (
                    <button
                      key={k} type="button" onClick={() => setForm(c.id, { respType: k })}
                      className={`rounded-md border px-2 py-1.5 text-xs font-semibold ${f.respType === k ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 text-slate-600"}`}
                    >
                      {l}
                    </button>
                  ))}
                </div>
                {f.respType === "mfg" && (
                  <select value={f.vendorId || ""} onChange={(e) => setForm(c.id, { vendorId: e.target.value })} className="mt-1.5 w-full rounded-md border border-slate-300 px-2 py-1 text-xs">
                    <option value="">Select manufacturer</option>
                    {parties.vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                  </select>
                )}
                {f.respType === "trans" && (
                  <select value={f.courierId || ""} onChange={(e) => setForm(c.id, { courierId: e.target.value })} className="mt-1.5 w-full rounded-md border border-slate-300 px-2 py-1 text-xs">
                    <option value="">Select transporter</option>
                    {parties.couriers.map((co) => <option key={co.id} value={co.id}>{co.name}</option>)}
                  </select>
                )}
                {f.respType === "ins" && (
                  <input value={f.insurer || ""} onChange={(e) => setForm(c.id, { insurer: e.target.value })} placeholder="Insurer / policy" className="mt-1.5 w-full rounded-md border border-slate-300 px-2 py-1 text-xs" />
                )}
                <input
                  type="number" min="0" step="0.01" value={f.amount || ""} onChange={(e) => setForm(c.id, { amount: e.target.value })}
                  placeholder={`Claimed amount (₹) — at or under ₹${APPROVAL_CAP_AMOUNT.toLocaleString("en-IN")}, Service Manager can close it`}
                  className="mt-1.5 w-full rounded-md border border-slate-300 px-2 py-1 text-xs"
                />
                <div className="mt-1.5 flex justify-end">
                  <button type="button" disabled={busyId === c.id || !f.respType} onClick={() => saveDecision(c)} className="rounded-md bg-brand-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">
                    Save decision
                  </button>
                </div>
              </div>
            )}
            {canAct && (
              <div className="mt-2 flex flex-wrap items-center justify-end gap-1.5">
                {c.can_act && (
                  <>
                    <input value={f.rejectReason || ""} onChange={(e) => setForm(c.id, { rejectReason: e.target.value })} placeholder="Reason to reject" className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-xs" />
                    <button type="button" disabled={busyId === c.id} onClick={() => doReject(c)} className="rounded-md border border-rose-300 px-3 py-1 text-xs text-rose-700 disabled:opacity-50">Reject</button>
                  </>
                )}
                {c.can_approve && (
                  <button type="button" disabled={busyId === c.id || !c.responsible_type} onClick={() => doApprove(c)} className="rounded-md bg-emerald-700 px-3 py-1 text-xs text-white disabled:opacity-50">
                    {c.stage === "svm" ? (isServiceManager && c.amount != null && c.amount <= APPROVAL_CAP_AMOUNT ? "Close" : "Forward to Admin") : "Close"}
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
      {err && <p className="text-xs text-rose-700">{err}</p>}
    </div>
  );
}
