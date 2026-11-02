import { useEffect, useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { servicesApi } from "../../api/services.js";
import { formatApiError } from "../../utils/apiError.js";

function fmtWhen(d) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "numeric", minute: "2-digit" });
  } catch {
    return d;
  }
}

function StepDot({ decision }) {
  if (decision === "Rejected") {
    return (
      <span className="absolute -left-[21px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-rose-500 bg-white">
        <svg viewBox="0 0 20 20" className="h-2.5 w-2.5"><path d="M6 6l8 8M14 6l-8 8" stroke="#e11d48" strokeWidth="2.4" strokeLinecap="round" /></svg>
      </span>
    );
  }
  return (
    <span className="absolute -left-[21px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-emerald-600 bg-white">
      <svg viewBox="0 0 20 20" className="h-2.5 w-2.5"><path d="M5 10l3 3 7-7" stroke="#059669" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </span>
  );
}

/** The approval flow for one installation or service payment -- every stage it has passed through,
 * who acted and when, and any returns with the reason given -- fetched on demand from the record's
 * own detail payload (which already carries payment_approval_history), so this works from any list
 * (Payment Queue, Ready to Pay) without a dedicated endpoint. */
export default function PaymentFlowModal({ module, entityId, label, onClose }) {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    setErr("");
    const fetcher = module === "installation" ? installationsApi.get(entityId) : servicesApi.get(entityId);
    fetcher
      .then(setRecord)
      .catch((e) => setErr(formatApiError(e, "Failed to load approval flow")))
      .finally(() => setLoading(false));
  }, [module, entityId]);

  const history = [...(record?.payment_approval_history || [])].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at),
  );
  const currentStageLabel = record?.payment_approval_stage_label;
  const isWaiting = record?.status === "Payment Pending" || record?.status === "Payment Requested";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Approval flow — {label}</h2>
            <p className="text-xs text-slate-500">{module === "installation" ? "Installation" : "Service"} request</p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>

        {loading && <div className="py-6 text-center text-sm text-slate-500">Loading…</div>}
        {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

        {!loading && !err && (
          <>
            {history.length === 0 ? (
              <p className="text-sm text-slate-500">No approval activity recorded yet.</p>
            ) : (
              <div className="relative ml-2 space-y-4 border-l-2 border-slate-200 pl-6">
                {history.map((h) => (
                  <div key={h.id} className="relative">
                    <StepDot decision={h.decision} />
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-sm font-semibold text-slate-800">{h.stage_label}</span>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                        h.decision === "Rejected" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"
                      }`}>
                        {h.decision === "Rejected" ? "Returned" : "Approved"}
                      </span>
                      <span className="text-xs text-slate-400">{fmtWhen(h.created_at)}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {h.approved_by_name || "—"} {h.approver_role ? `(${h.approver_role})` : ""}
                    </div>
                    {h.remarks && (
                      <div className={`mt-1 rounded-md px-2.5 py-1.5 text-xs ${
                        h.decision === "Rejected" ? "bg-rose-50 text-rose-700" : "bg-slate-50 text-slate-600"
                      }`}>
                        "{h.remarks}"
                      </div>
                    )}
                  </div>
                ))}
                {isWaiting && (
                  <div className="relative">
                    <span className="absolute -left-[21px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-slate-300 bg-white">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                    </span>
                    <div className="text-sm font-semibold text-slate-500">{currentStageLabel || "Next stage"}</div>
                    <div className="text-xs text-slate-400">Waiting to act</div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
