import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import DateRangeFilter from "../../components/DateRangeFilter.jsx";
import Modal from "../../components/Modal.jsx";
import PartySummary from "../../components/claims/PartySummary.jsx";
import { partsApi, REQUEST_KINDS } from "../../api/parts.js";

const KIND_LABEL = Object.fromEntries(REQUEST_KINDS.map((k) => [k.value, k.label]));
const KIND_PILL = { part: "bg-blue-100 text-blue-800", expense: "bg-amber-100 text-amber-800", ondemand: "bg-violet-100 text-violet-800", unit: "bg-rose-100 text-rose-800" };

function stagePill(stage) {
  if (stage === "done") return <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Approved</span>;
  if (stage === "rejected") return <span className="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">Rejected</span>;
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

function RequestDetail({ id, onClose, onChanged }) {
  const [req, setReq] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [discussMsg, setDiscussMsg] = useState("");
  const [discussing, setDiscussing] = useState(false);
  const [note, setNote] = useState("");

  async function load() {
    try {
      setReq(await partsApi.requestDetail(id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not load this request");
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

        {req.can_act && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 pt-3">
            <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Reason to reject" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button
              disabled={busy || !rejectReason.trim()}
              onClick={() => { setRejecting(true); act(() => partsApi.reject(req.id, rejectReason.trim())).finally(() => setRejecting(false)); }}
              className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            >
              {rejecting ? "…" : "Reject"}
            </button>
            <button
              disabled={busy}
              onClick={() => act(() => partsApi.approve(req.id))}
              className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              Approve
            </button>
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
