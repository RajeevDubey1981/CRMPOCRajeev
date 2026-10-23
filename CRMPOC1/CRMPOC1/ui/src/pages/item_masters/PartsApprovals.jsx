import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import DateRangeFilter from "../../components/DateRangeFilter.jsx";
import Modal from "../../components/Modal.jsx";
import LinkedClaimsPanel from "../../components/claims/LinkedClaimsPanel.jsx";
import PartySummary from "../../components/claims/PartySummary.jsx";
import { partsApi, REQUEST_KINDS } from "../../api/parts.js";
import { RESP_LABEL, shortageClaimsApi } from "../../api/shortageClaims.js";
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
      const lists = [await shortageClaimsApi.list({ item_request_id: id })];
      if (detail.crm_serial_no) lists.push((await shortageClaimsApi.list({ serial_no: detail.crm_serial_no })).filter((c) => !c.item_request_id || c.item_request_id === id));
      if (detail.crm_service_request_id) lists.push((await shortageClaimsApi.list({ service_request_id: detail.crm_service_request_id })).filter((c) => !c.serial_no));
      const seen = new Set();
      setLinkedClaims(lists.flat().filter((c) => !seen.has(c.id) && seen.add(c.id)).sort((a, b) => a.id - b.id));
    } catch {
      /* the request itself still shows */
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id]);

  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose?.(); }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

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

  const stageChip = {
    done: "bg-emerald-200 text-emerald-900",
    rejected: "bg-rose-200 text-rose-900",
    returned: "bg-orange-200 text-orange-900",
  }[req.stage] || "bg-amber-200 text-amber-900";
  const claimLines = linkedClaims.slice(0, 2).map((c) => (c.responsible_type
    ? `Claim ${c.claim_no} is on ${RESP_LABEL[c.responsible_type]}${c.party_name ? ` — ${c.party_name}` : ""}${c.party_given_by ? `, given by ${c.party_given_by}` : ""}`
    : `Claim ${c.claim_no}: not decided yet who it is on`));
  if (linkedClaims.length > 2) claimLines.push(`and ${linkedClaims.length - 2} more claim(s)`);
  const hasPhotos = (req.engineer_photos?.length || 0) + (req.photos?.length || 0) > 0;
  const detailCards = [
    ["Raised by", req.crm_raised_by_name],
    req.crm_serial_no && ["Serial", req.crm_serial_no, true],
    req.crm_item_code && ["Item code", req.crm_item_code, true],
    req.crm_service_request_id && ["Service request", req.crm_service_request_no || req.crm_service_request_id],
    req.crm_installation_request_id && ["Installation", req.crm_installation_request_no || req.crm_installation_request_id],
  ].filter(Boolean);
  const showFooter = req.can_act || req.stage === "rejected" || req.stage === "returned" || req.stage === "done";

  return (
    <div
      className="crm-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-3 sm:p-4"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <div className="crm-modal-card flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        {/* summary banner */}
        <div className="shrink-0 bg-[#26215C] px-5 pb-4 pt-3 text-white">
          <div className="flex items-start justify-between gap-3">
            <span className="text-xs text-white/80">{req.request_no} · {KIND_LABEL[req.kind]}</span>
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${stageChip}`}>{req.stage_label}</span>
              <button type="button" aria-label="Close" onClick={onClose} className="rounded p-1 text-white/70 hover:bg-white/10 hover:text-white">✕</button>
            </div>
          </div>
          <div className="mt-1 text-3xl font-semibold tracking-tight">
            {req.amount != null ? `₹${Number(req.amount).toLocaleString("en-IN")}` : KIND_LABEL[req.kind]}
          </div>
          <p className="mt-0.5 line-clamp-2 text-sm text-white/85">{req.description} · raised by {req.crm_raised_by_name}</p>
          {claimLines.length > 0 && (
            <div className="mt-3 space-y-1 rounded-xl bg-white/15 px-3 py-2 text-sm">
              {claimLines.map((line) => <div key={line}>🛡️ {line}</div>)}
            </div>
          )}
        </div>

        {/* scrolling body */}
        <div className="crm-modal-body min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {(linkedClaims.length > 0 || hasPhotos) && (
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Claim and photos</h3>
              <LinkedClaimsPanel claims={linkedClaims} onChanged={load} isServiceManager={roleKey(user?.role) === "service_manager"} />
              {req.engineer_photos?.length > 0 && (
                <div className="mt-3">
                  <span className="text-xs text-slate-500">Engineer's photos ({req.engineer_photos.length}), taken at the unit</span>
                  <div className="mt-1 grid grid-cols-4 gap-2">
                    {req.engineer_photos.map((p) => (
                      <a key={`fp-${p.id}`} href={p.file_path} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-slate-200" title={p.uploaded_by_name ? `By ${p.uploaded_by_name}` : ""}>
                        <img src={p.file_path} alt="Engineer's photo" className="h-20 w-full object-cover" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {req.photos?.length > 0 && (
                <div className="mt-3">
                  <span className="text-xs text-slate-500">Photos on this request ({req.photos.length}/{req.required_photos || req.photos.length})</span>
                  <div className="mt-1 grid grid-cols-4 gap-2">
                    {req.photos.map((p) => (
                      <a key={p.id} href={p.file_path} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-slate-200">
                        <img src={p.file_path} alt={p.label || "photo"} className="h-20 w-full object-cover" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Details</h3>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {detailCards.map(([label, value, mono]) => (
                <div key={label} className="rounded-xl bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">{label}</div>
                  <div className={`mt-0.5 break-words font-medium text-slate-800 ${mono ? "font-mono text-xs" : "text-sm"}`}>{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-2 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-800">
              <div className="text-xs text-slate-500">What is needed</div>
              {req.description}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Timeline</h3>
            <ul className="ml-1.5 space-y-2 border-l-2 border-slate-200 pl-4">
              {(req.timeline || []).map((e) => (
                <li key={e.id} className="relative text-sm text-slate-800">
                  <span className="absolute -left-[22px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
                  {e.text}
                  <div className="text-xs text-slate-400">{fmtDate(e.at)}</div>
                </li>
              ))}
            </ul>
          </section>

          {req.crm_query_id ? (
            <Link to={`/queries/${req.crm_query_id}`} className="inline-block rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
              💬 Open the discussion in Queries
            </Link>
          ) : (
            <div className="flex items-center gap-2">
              <input value={discussMsg} onChange={(e) => setDiscussMsg(e.target.value)} placeholder="Ask a question before deciding…" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <button
                disabled={discussing || !discussMsg.trim()}
                onClick={() => { setDiscussing(true); act(() => partsApi.discuss(req.id, discussMsg.trim())).finally(() => setDiscussing(false)); setDiscussMsg(""); }}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                💬 Discuss
              </button>
            </div>
          )}

          {err && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{err}</p>}
        </div>

        {/* decision bar, always in view */}
        {showFooter && (
          <div className="shrink-0 space-y-2 border-t border-slate-200 bg-slate-50 px-5 py-3">
            {req.can_act && (
              <>
                <input
                  value={rejectReason}
                  onChange={(e) => { setRejectReason(e.target.value); setReasonErr(""); }}
                  placeholder="Reason (needed for Not approved or Return)"
                  aria-invalid={!!reasonErr}
                  className={`w-full rounded-lg border px-3 py-2 text-sm ${reasonErr ? "border-rose-400 bg-rose-50" : "border-slate-300 bg-white"}`}
                />
                {reasonErr && <p className="text-xs font-medium text-rose-700">{reasonErr}</p>}
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <button type="button" disabled={busy} onClick={() => decide("reject")} className="rounded-lg border border-rose-400 bg-white px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50">
                    {deciding === "reject" ? "…" : "Not approved"}
                  </button>
                  {req.can_return_team && (
                    <button type="button" disabled={busy} onClick={() => decide("team")} className="rounded-lg border border-orange-400 bg-white px-4 py-2 text-sm font-medium text-orange-800 hover:bg-orange-50 disabled:opacity-50">
                      {deciding === "team" ? "…" : "Return to Service Team"}
                    </button>
                  )}
                  {req.can_return && (
                    <button type="button" disabled={busy} onClick={() => decide("return")} className="rounded-lg border border-amber-400 bg-white px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-50">
                      {deciding === "return" ? "…" : "Return to Service Manager"}
                    </button>
                  )}
                  <button type="button" disabled={busy} onClick={() => act(() => partsApi.approve(req.id))} className="rounded-lg bg-emerald-700 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50">
                    {req.stage === "svm" && req.stage_label?.includes("then Admin") ? "Recommend" : "Approve"}
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  Not approved closes the request, and the engineer can fix it and send it again. Return to Service Team keeps it open for the engineer to fix or add something, then it comes back to you.
                  {req.can_return ? " Return to Service Manager keeps it open and sends it back to be checked again." : ""}
                </p>
              </>
            )}

            {(req.stage === "rejected" || req.stage === "returned") && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                <p className="mb-2 text-xs text-rose-800">
                  {req.stage === "returned" ? "Returned to the Service Team" : "Not approved"} — see the reason in the timeline above. Fixing it below sends this same request (<span className="font-mono">{req.request_no}</span>) back through approval instead of starting over.
                </p>
                <div className="flex items-center gap-2">
                  <input
                    value={resubmitDesc}
                    onChange={(e) => setResubmitDesc(e.target.value)}
                    placeholder="Update the description (optional — leave blank to resubmit as-is)"
                    className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                  <button
                    disabled={resubmitting}
                    onClick={() => {
                      setResubmitting(true);
                      act(() => partsApi.resubmit(req.id, resubmitDesc.trim() ? { description: resubmitDesc.trim() } : {})).finally(() => setResubmitting(false));
                      setResubmitDesc("");
                    }}
                    className="rounded-lg bg-amber-600 px-4 py-2 text-sm text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    {resubmitting ? "…" : "Resubmit"}
                  </button>
                </div>
              </div>
            )}

            {req.stage === "done" && (
              <div className="flex items-center gap-2">
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (who handed it over, courier AWB, etc.)" className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
                <button disabled={busy} onClick={() => act(() => partsApi.supplied(req.id, note.trim() || null))} className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50">
                  Mark supplied
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
