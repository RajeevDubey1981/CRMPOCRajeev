import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import DateRangeFilter from "../../components/DateRangeFilter.jsx";
import Modal from "../../components/Modal.jsx";
import LinkedClaimsPanel from "../../components/claims/LinkedClaimsPanel.jsx";
import PartySummary from "../../components/claims/PartySummary.jsx";
import { partsApi, REQUEST_KINDS } from "../../api/parts.js";
import { shortageClaimsApi } from "../../api/shortageClaims.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { roleKey } from "../../utils/roles.js";

// Service Team, Service Manager, Admin, Incool, Sub Admin — the same roles that can act on a parts
// request's approval — can also claim it out from there. The engineer who raised it never can.
const CLAIM_ROLES = new Set(["service", "indcool_service", "indcool", "indcool service", "service_manager", "admin", "incool", "sub_admin"]);

const KIND_LABEL = Object.fromEntries(REQUEST_KINDS.map((k) => [k.value, k.label]));
const KIND_PILL = { part: "bg-blue-100 text-blue-800", expense: "bg-amber-100 text-amber-800", ondemand: "bg-violet-100 text-violet-800", unit: "bg-rose-100 text-rose-800" };

function stagePill(stage) {
  if (stage === "done") return <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Approved</span>;
  if (stage === "rejected") return <span className="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">Not approved</span>;
  if (stage === "returned") return <span className="inline-flex rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">Returned to Service Team</span>;
  if (stage === "sub") return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending Admin</span>;
  return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending Service Manager</span>;
}

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch { return s; }
}

export default function PartsApprovals() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [kind, setKind] = useState("");
  const [mineOnly, setMineOnly] = useState(true);
  const [range, setRange] = useState({ from: "", to: "" });
  const [detailId, setDetailId] = useState(null);

  const params = useMemo(() => ({
    kind: kind || undefined, mine: mineOnly || undefined,
    date_from: range.from || undefined, date_to: range.to || undefined,
  }), [kind, mineOnly, range]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setRows(await partsApi.requests(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  const pendingCount = rows.filter((r) => r.stage === "svm" || r.stage === "sub").length;

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 text-[11px] font-bold uppercase tracking-wide text-slate-400">Missing-item claims, by who it's on</div>
        <PartySummary />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1">
          <button onClick={() => setKind("")} className={`rounded-full px-3 py-1 text-xs font-medium ${!kind ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"}`}>All</button>
          {REQUEST_KINDS.map((k) => (
            <button key={k.value} onClick={() => setKind(k.value)} className={`rounded-full px-3 py-1 text-xs font-medium ${kind === k.value ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"}`}>
              {k.label}
            </button>
          ))}
        </div>
        <DateRangeFilter from={range.from} to={range.to} onChange={(from, to) => setRange({ from, to })} label="Raised" />
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} />
          Only what's waiting on me ({pendingCount})
        </label>
        <Link to="/queries" className="ml-auto rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 hover:bg-sky-100">
          💬 Queries
        </Link>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Request</th>
              <th className="px-3 py-2">What</th>
              <th className="px-3 py-2">Raised by</th>
              <th className="px-3 py-2">Raised</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Nothing here.</td></tr>}
            {!loading && rows.map((r) => (
              <tr key={r.id} onClick={() => setDetailId(r.id)} className="cursor-pointer hover:bg-slate-50">
                <td className="px-3 py-2"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${KIND_PILL[r.kind]}`}>{KIND_LABEL[r.kind]}</span></td>
                <td className="px-3 py-2 font-mono text-xs">{r.request_no}</td>
                <td className="px-3 py-2 text-slate-800">{r.description}{r.crm_query_id && <span className="ml-2" title="Discussion open">💬</span>}</td>
                <td className="px-3 py-2">{r.crm_raised_by_name}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(r.created_at)}</td>
                <td className="px-3 py-2">{stagePill(r.stage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailId && <RequestDetail id={detailId} onClose={() => setDetailId(null)} onChanged={load} />}
    </div>
  );
}

export function RequestDetail({ id, onClose, onChanged }) {
  const { user } = useAuth();
  const canClaim = CLAIM_ROLES.has(roleKey(user?.role));
  const [req, setReq] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [deciding, setDeciding] = useState("");
  const [reasonErr, setReasonErr] = useState("");
  const [discussMsg, setDiscussMsg] = useState("");
  const [discussing, setDiscussing] = useState(false);
  const [note, setNote] = useState("");
  const [resubmitDesc, setResubmitDesc] = useState("");
  const [resubmitting, setResubmitting] = useState(false);
  const [linkedClaims, setLinkedClaims] = useState([]);

  async function load() {
    let detail = null;
    try {
      detail = await partsApi.requestDetail(id);
      setReq(detail);
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not load this request");
    }
    if (canClaim && detail) loadClaims(detail);
  }

  // Claims raised on this request itself, plus the ones the engineer raised from the service request for the same unit.
  async function loadClaims(detail) {
    try {
      const own = await shortageClaimsApi.list({ item_request_id: id });
      let all = own;
      if (detail.crm_service_request_id) {
        const fromService = await shortageClaimsApi.list({ service_request_id: detail.crm_service_request_id });
        const sameUnit = fromService.filter((c) => !detail.crm_serial_no || !c.serial_no || c.serial_no === detail.crm_serial_no);
        const seen = new Set(own.map((c) => c.id));
        all = [...own, ...sameUnit.filter((c) => !seen.has(c.id))];
      }
      setLinkedClaims(all);
    } catch {
      /* the request itself still shows */
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
      return true;
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not do that");
      return false;
    } finally {
      setBusy(false);
    }
  }

  // Reject and Return both need the reason, so the other person knows why. Nothing is greyed out: asking for it is clearer.
  async function decide(kind) {
    const reason = rejectReason.trim();
    if (reason.length < 2) {
      setReasonErr(kind === "return" ? "Write why you are sending it back, so the Service Manager knows what to look at." : kind === "team" ? "Write what the service team should fix or add." : "Write why it is not approved, so the engineer knows what to fix.");
      return;
    }
    setReasonErr("");
    setDeciding(kind);
    const ok = await act(() => (kind === "return" ? partsApi.returnToManager(req.id, reason) : kind === "team" ? partsApi.returnToTeam(req.id, reason) : partsApi.reject(req.id, reason)));
    setDeciding("");
    if (ok) setRejectReason("");
  }

  if (!req) {
    return <Modal open onClose={onClose} title="Request"><p className="text-sm text-slate-500">{err || "Loading…"}</p></Modal>;
  }

  return (
    <Modal open onClose={onClose} title={`${req.request_no} — ${KIND_LABEL[req.kind]}`} maxWidth="max-w-2xl">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-xs uppercase tracking-wide text-slate-500">Raised by</span><p>{req.crm_raised_by_name}</p></div>
          <div><span className="text-xs uppercase tracking-wide text-slate-500">Status</span><p>{req.stage_label}</p></div>
          {req.crm_item_code && <div><span className="text-xs uppercase tracking-wide text-slate-500">Item code</span><p className="font-mono text-xs">{req.crm_item_code}</p></div>}
          {req.crm_serial_no && <div><span className="text-xs uppercase tracking-wide text-slate-500">Serial</span><p className="font-mono text-xs">{req.crm_serial_no}</p></div>}
          {req.amount != null && <div><span className="text-xs uppercase tracking-wide text-slate-500">Amount</span><p>₹{Number(req.amount).toLocaleString("en-IN")}</p></div>}
          {req.crm_service_request_id && <div><span className="text-xs uppercase tracking-wide text-slate-500">Service request</span><p>{req.crm_service_request_no || req.crm_service_request_id}</p></div>}
          {req.crm_installation_request_id && <div><span className="text-xs uppercase tracking-wide text-slate-500">Installation</span><p>{req.crm_installation_request_no || req.crm_installation_request_id}</p></div>}
        </div>
        <div><span className="text-xs uppercase tracking-wide text-slate-500">Description</span><p className="text-sm text-slate-800">{req.description}</p></div>

        {req.engineer_photos?.length > 0 && (
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Engineer's photos ({req.engineer_photos.length}) — taken at the unit</span>
            <div className="mt-1 grid grid-cols-4 gap-2">
              {req.engineer_photos.map((p) => (
                <a key={`fp-${p.id}`} href={p.file_path} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-md border border-slate-200" title={p.uploaded_by_name ? `By ${p.uploaded_by_name}` : ""}>
                  <img src={p.file_path} alt="Engineer's photo" className="h-20 w-full object-cover" />
                </a>
              ))}
            </div>
          </div>
        )}

        {req.photos?.length > 0 && (
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Photos ({req.photos.length}/{req.required_photos || req.photos.length})</span>
            <div className="mt-1 grid grid-cols-4 gap-2">
              {req.photos.map((p) => (
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
            {(req.timeline || []).map((e) => (
              <li key={e.id} className="text-sm">
                <span className="text-xs text-slate-400">{fmtDate(e.at)}</span> — {e.text}
              </li>
            ))}
          </ul>
        </div>

        {req.crm_query_id ? (
          <Link to={`/queries/${req.crm_query_id}`} className="inline-block rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
            💬 Open the discussion in Queries
          </Link>
        ) : (
          <div className="flex items-center gap-2">
            <input value={discussMsg} onChange={(e) => setDiscussMsg(e.target.value)} placeholder="Ask a question before deciding…" className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button
              disabled={discussing || !discussMsg.trim()}
              onClick={() => { setDiscussing(true); act(() => partsApi.discuss(req.id, discussMsg.trim())).finally(() => setDiscussing(false)); setDiscussMsg(""); }}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              💬 Discuss
            </button>
          </div>
        )}

        {err && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{err}</p>}

        <LinkedClaimsPanel claims={linkedClaims} onChanged={load} isServiceManager={roleKey(user?.role) === "service_manager"} />

        {req.can_act && (
          <div className="space-y-2 border-t border-slate-200 pt-3">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">Your decision</label>
            <input
              value={rejectReason}
              onChange={(e) => { setRejectReason(e.target.value); setReasonErr(""); }}
              placeholder="Reason (needed for Not approved or Return)"
              aria-invalid={!!reasonErr}
              className={`w-full rounded-md border px-3 py-2 text-sm ${reasonErr ? "border-rose-400 bg-rose-50" : "border-slate-300"}`}
            />
            {reasonErr && <p className="text-xs font-medium text-rose-700">{reasonErr}</p>}
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => decide("reject")}
                className="rounded-md border border-rose-400 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              >
                {deciding === "reject" ? "…" : "Not approved"}
              </button>
              {req.can_return_team && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => decide("team")}
                  className="rounded-md border border-orange-400 px-4 py-2 text-sm font-medium text-orange-800 hover:bg-orange-50 disabled:opacity-50"
                >
                  {deciding === "team" ? "…" : "Return to Service Team"}
                </button>
              )}
              {req.can_return && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => decide("return")}
                  className="rounded-md border border-amber-400 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-50"
                >
                  {deciding === "return" ? "…" : "Return to Service Manager"}
                </button>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => act(() => partsApi.approve(req.id))}
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
              >
                {req.stage === "svm" && req.stage_label?.includes("then Admin") ? "Recommend" : "Approve"}
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Not approved closes the request, and the engineer can fix it and send it again. Return to Service Team keeps it open for the engineer to fix or add something, then it comes back to you.
              {req.can_return ? " Return to Service Manager keeps it open and sends it back to be checked again." : ""}
            </p>
          </div>
        )}

        {(req.stage === "rejected" || req.stage === "returned") && (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-3">
            <p className="mb-2 text-xs text-rose-800">
              {req.stage === "returned" ? "Returned to the Service Team" : "Not approved"} — see the reason in the timeline above. Fixing it below sends this same request (<span className="font-mono">{req.request_no}</span>) back through approval instead of starting over.
            </p>
            <div className="flex items-center gap-2">
              <input
                value={resubmitDesc}
                onChange={(e) => setResubmitDesc(e.target.value)}
                placeholder="Update the description (optional — leave blank to resubmit as-is)"
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                disabled={resubmitting}
                onClick={() => {
                  setResubmitting(true);
                  act(() => partsApi.resubmit(req.id, resubmitDesc.trim() ? { description: resubmitDesc.trim() } : {})).finally(() => setResubmitting(false));
                  setResubmitDesc("");
                }}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm text-white hover:bg-amber-700 disabled:opacity-50"
              >
                {resubmitting ? "…" : "Resubmit"}
              </button>
            </div>
          </div>
        )}

        {req.stage === "done" && (
          <div className="flex items-center gap-2 border-t border-slate-200 pt-3">
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (who handed it over, courier AWB, etc.)" className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button disabled={busy} onClick={() => act(() => partsApi.supplied(req.id, note.trim() || null))} className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50">
              Mark supplied
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
