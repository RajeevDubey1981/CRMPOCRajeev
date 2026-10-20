import { useEffect, useMemo, useState } from "react";

import DateRangeFilter from "../../components/DateRangeFilter.jsx";
import Modal from "../../components/Modal.jsx";
import PartySummary from "../../components/claims/PartySummary.jsx";
import { shortageClaimsApi, ITEMS_MISSING, RESP_LABEL } from "../../api/shortageClaims.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { roleKey } from "../../utils/roles.js";

const APPROVAL_CAP_AMOUNT = 2500;

function stagePill(stage) {
  if (stage === "done") return <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Closed</span>;
  if (stage === "rejected") return <span className="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">Rejected</span>;
  if (stage === "sub") return <span className="inline-flex rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">Pending Admin</span>;
  return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending Service Manager</span>;
}
function respPill(c) {
  if (!c.responsible_type) return <span className="text-xs text-slate-400">{c.stage === "rejected" ? "—" : "Not yet decided"}</span>;
  const cls = c.responsible_type === "mfg" ? "bg-blue-100 text-blue-800" : c.responsible_type === "trans" ? "bg-orange-100 text-orange-800" : "bg-violet-100 text-violet-800";
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{RESP_LABEL[c.responsible_type]}</span>;
}
function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }); } catch { return s; }
}

export default function ShortageClaimsTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [flow, setFlow] = useState("");
  const [item, setItem] = useState("");
  const [resp, setResp] = useState("");
  const [range, setRange] = useState({ from: "", to: "" });
  const [detailId, setDetailId] = useState(null);

  const params = useMemo(() => ({
    flow: flow || undefined, item: item || undefined, responsible_type: resp || undefined,
    date_from: range.from || undefined, date_to: range.to || undefined,
  }), [flow, item, resp, range]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setRows(await shortageClaimsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  const open = rows.filter((c) => c.stage === "svm" || c.stage === "sub");

  function exportCsv() {
    const url = shortageClaimsApi.exportUrl(params);
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) return r.json().then((body) => { throw new Error(body.detail || `Server error ${r.status}`); });
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `shortage_claims_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(obj);
      })
      .catch((e) => alert(e.message || "Export failed"));
  }

  return (
    <div className="space-y-4">
      <PartySummary active={resp} onPick={setResp} />
      {open.length > 0 && (
        <div className="flex items-center gap-3 rounded-lg bg-rose-600 px-4 py-3 text-white shadow-sm">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/20 text-lg">⚠</span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold">{open.length} claim{open.length > 1 ? "s" : ""} waiting on a decision</div>
            <div className="text-xs text-white/90">Oldest: {open[open.length - 1].claim_no}, raised {fmtDate(open[open.length - 1].created_at)}.</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <DateRangeFilter from={range.from} to={range.to} onChange={(from, to) => setRange({ from, to })} label="Raised" />
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">Item</label>
          <select value={item} onChange={(e) => setItem(e.target.value)} className="mt-0.5 rounded-md border border-slate-300 px-2 py-1.5 text-sm">
            <option value="">All items</option>
            {ITEMS_MISSING.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">Flow</label>
          <select value={flow} onChange={(e) => setFlow(e.target.value)} className="mt-0.5 rounded-md border border-slate-300 px-2 py-1.5 text-sm">
            <option value="">Both</option>
            <option value="installation">Installation</option>
            <option value="service">Service</option>
          </select>
        </div>
        <div className="flex gap-1.5">
          {["", "mfg", "trans", "ins"].map((k) => (
            <button
              key={k}
              onClick={() => setResp(k)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${resp === k ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"}`}
            >
              {k ? RESP_LABEL[k] : "All parties"}
            </button>
          ))}
        </div>
        <button onClick={exportCsv} className="ml-auto rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
          ⬇ Export CSV
        </button>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Claim No</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Flow</th>
              <th className="px-3 py-2">Item(s)</th>
              <th className="px-3 py-2">Raised by</th>
              <th className="px-3 py-2">Responsible</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No claims match these filters.</td></tr>}
            {!loading && rows.map((c) => (
              <tr key={c.id} onClick={() => setDetailId(c.id)} className="cursor-pointer hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs">{c.claim_no}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(c.created_at)}</td>
                <td className="px-3 py-2">{c.flow === "installation" ? "Installation" : "Service"}</td>
                <td className="px-3 py-2">{c.items.join(", ")}</td>
                <td className="px-3 py-2">{c.raised_by_name}</td>
                <td className="px-3 py-2">{respPill(c)}</td>
                <td className="px-3 py-2">{stagePill(c.stage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailId && <ClaimDetail id={detailId} onClose={() => setDetailId(null)} onChanged={load} />}
    </div>
  );
}

function ClaimDetail({ id, onClose, onChanged }) {
  const { user } = useAuth();
  const isServiceManager = roleKey(user?.role) === "service_manager";
  const [claim, setClaim] = useState(null);
  const [parties, setParties] = useState({ vendors: [], couriers: [] });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [respType, setRespType] = useState("");
  const [vendorId, setVendorId] = useState("");
  const [courierId, setCourierId] = useState("");
  const [insurer, setInsurer] = useState("");
  const [amount, setAmount] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  async function load() {
    try {
      const [c, p] = await Promise.all([shortageClaimsApi.get(id), shortageClaimsApi.parties()]);
      setClaim(c);
      setParties(p);
      setRespType(c.responsible_type || "");
      setAmount(c.amount != null ? String(c.amount) : "");
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not load this claim");
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id]);

  async function act(fn) {
    setBusy(true);
    setErr("");
    try {
      await fn();
      await load();
      onChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not do that");
    } finally {
      setBusy(false);
    }
  }

  async function saveDecision() {
    const body = { responsible_type: respType };
    if (respType === "mfg") body.vendor_id = Number(vendorId);
    if (respType === "trans") body.courier_id = Number(courierId);
    if (respType === "ins") body.insurer_name = insurer;
    if (amount.trim() !== "") body.amount = Number(amount);
    await act(() => shortageClaimsApi.decide(id, body));
  }

  if (!claim) return <Modal open onClose={onClose} title="Claim"><p className="text-sm text-slate-500">{err || "Loading…"}</p></Modal>;

  return (
    <Modal open onClose={onClose} title={`${claim.claim_no} — ${claim.items.join(", ")}`} maxWidth="max-w-2xl">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-xs uppercase tracking-wide text-slate-500">Raised by</span><p>{claim.raised_by_name}</p></div>
          <div><span className="text-xs uppercase tracking-wide text-slate-500">Status</span><p>{stagePill(claim.stage)}</p></div>
          <div><span className="text-xs uppercase tracking-wide text-slate-500">Flow</span><p>{claim.flow === "installation" ? "Installation" : "Service"}</p></div>
          {claim.item_code && <div><span className="text-xs uppercase tracking-wide text-slate-500">Item code</span><p className="font-mono text-xs">{claim.item_code}</p></div>}
          {claim.amount != null && <div><span className="text-xs uppercase tracking-wide text-slate-500">Amount</span><p>₹{Number(claim.amount).toLocaleString("en-IN")}</p></div>}
        </div>
        <div><span className="text-xs uppercase tracking-wide text-slate-500">Description</span><p className="text-sm text-slate-800">{claim.description}</p></div>

        {claim.photos?.length > 0 && (
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Photos ({claim.photos.length}/{claim.required_photos})</span>
            <div className="mt-1 grid grid-cols-4 gap-2">
              {claim.photos.map((p) => (
                <a key={p.id} href={p.file_path} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-md border border-slate-200">
                  <img src={p.file_path} alt={p.label || "photo"} className="h-20 w-full object-cover" />
                </a>
              ))}
            </div>
          </div>
        )}

        <div>
          <span className="text-xs uppercase tracking-wide text-slate-500">Timeline</span>
          <ul className="mt-1 space-y-1 border-l-2 border-slate-200 pl-3">
            {(claim.timeline || []).map((e) => (
              <li key={e.id} className="text-sm"><span className="text-xs text-slate-400">{new Date(e.at).toLocaleString()}</span> — {e.text}</li>
            ))}
          </ul>
        </div>

        {claim.stage === "svm" && claim.can_act && (
          <div className="rounded-md border border-slate-200 p-3">
            <label className="text-xs uppercase tracking-wide text-slate-500">Term of claim — on whom, and on whose account</label>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {[["mfg", "Manufacturer"], ["trans", "Transporter"], ["ins", "Insurance"]].map(([k, l]) => (
                <button key={k} onClick={() => setRespType(k)} className={`rounded-md border px-2 py-2 text-xs font-semibold ${respType === k ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 text-slate-600"}`}>
                  {l}
                </button>
              ))}
            </div>
            {respType === "mfg" && (
              <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Select manufacturer</option>
                {parties.vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            )}
            {respType === "trans" && (
              <select value={courierId} onChange={(e) => setCourierId(e.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Select transporter</option>
                {parties.couriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            )}
            {respType === "ins" && (
              <input value={insurer} onChange={(e) => setInsurer(e.target.value)} placeholder="Insurer / policy" className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
            )}
            <div className="mt-2">
              <label className="text-xs uppercase tracking-wide text-slate-500">Claimed amount (₹)</label>
              <input
                type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)}
                placeholder={`At or under ₹${APPROVAL_CAP_AMOUNT.toLocaleString("en-IN")}, Service Manager can close it outright`}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div className="mt-2 flex justify-end">
              <button disabled={busy || !respType} onClick={saveDecision} className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Save decision</button>
            </div>
          </div>
        )}
        {claim.responsible_type && !(claim.stage === "svm" && claim.can_act) && (
          <div className="text-sm">{respPill(claim)} <b>{claim.party_name}</b></div>
        )}

        {err && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{err}</p>}

        {claim.can_act && (claim.stage === "svm" || claim.stage === "sub") && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 pt-3">
            <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Reason to reject" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button disabled={busy || !rejectReason.trim()} onClick={() => act(() => shortageClaimsApi.reject(id, rejectReason.trim()))} className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50">
              Reject
            </button>
            <button disabled={busy} onClick={() => act(() => shortageClaimsApi.approve(id))} className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-800 disabled:opacity-50">
              {claim.stage === "svm"
                ? (isServiceManager && claim.amount != null && claim.amount <= APPROVAL_CAP_AMOUNT ? "Claim this — close" : "Claim this — forward to Admin")
                : "Claim this — close"}
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
