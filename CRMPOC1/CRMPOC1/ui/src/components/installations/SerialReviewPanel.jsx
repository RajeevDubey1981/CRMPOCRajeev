import { useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { formatApiError } from "../../utils/apiError.js";

function normalize(value) {
  return (value || "").trim();
}

function Row({ label, reference, entered }) {
  const ref = normalize(reference);
  const got = normalize(entered);
  if (!ref && !got) return null;
  const matches = ref && got && ref.toLowerCase() === got.toLowerCase();
  const cellClass = matches
    ? "bg-emerald-50 text-emerald-700 font-medium"
    : got
      ? "bg-amber-50 text-amber-700 font-medium"
      : "";
  return (
    <tr className="border-b border-slate-200">
      <td className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-500">{label}</td>
      <td className="px-3 py-2 font-mono text-sm">{ref || <span className="text-slate-400">-</span>}</td>
      <td className={`px-3 py-2 font-mono text-sm ${cellClass}`}>{got || <span className="text-slate-400">-</span>}</td>
    </tr>
  );
}

// Jayveer's (the Service Team member this request is routed to) review gate before a serial the
// engineer scanned on site counts for anything downstream -- Approve unlocks the rest of the
// workflow (installationSerialReady), Return clears it and sends the engineer back to re-scan.
export default function SerialReviewPanel({ installation, canReview, onUpdated, onError, onBusy }) {
  const [busy, setBusy] = useState(false);
  const [showReturn, setShowReturn] = useState(false);
  const [remarks, setRemarks] = useState("");

  if (!installation || installation.serial_verified_at) return null;
  const hasEntry = Boolean((installation.engineer_entered_serial_no || installation.serial_no || "").trim());
  if (!hasEntry) return null;

  const reviewNote = (installation.serial_review_note || "").trim();
  const entered1 = installation.engineer_entered_serial_no || installation.serial_no;
  const entered2 = installation.engineer_entered_serial_no_2 || installation.serial_no_2;

  async function approve() {
    setBusy(true); onBusy?.(true); onError?.("");
    try {
      await installationsApi.approveEngineerOrderSerials(installation.id);
      await onUpdated?.();
    } catch (e) { onError?.(formatApiError(e, "Unable to approve the serial reading")); }
    finally { setBusy(false); onBusy?.(false); }
  }

  async function returnToEngineer() {
    setBusy(true); onBusy?.(true); onError?.("");
    try {
      await installationsApi.returnEngineerOrderSerials(installation.id, { remarks: remarks.trim() || undefined });
      setRemarks(""); setShowReturn(false);
      await onUpdated?.();
    } catch (e) { onError?.(formatApiError(e, "Unable to return the serial reading to the engineer")); }
    finally { setBusy(false); onBusy?.(false); }
  }

  return (
    <section className="mt-4 rounded-lg border border-violet-200 bg-violet-50/40 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">Serial verification pending</h3>
      <p className="mt-1 text-xs text-slate-600">
        The engineer entered these on site. Compare against what the order's own record shows, then approve or send back for re-verification.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[420px] text-left">
          <thead>
            <tr className="border-b border-slate-300">
              <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Slot</th>
              <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Order record</th>
              <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Engineer entered</th>
            </tr>
          </thead>
          <tbody>
            <Row label="Serial 1" reference={installation.order_item_serial_no} entered={entered1} />
            <Row label="Serial 2" reference={installation.order_item_serial_no_2} entered={entered2} />
          </tbody>
        </table>
      </div>
      {reviewNote && (
        <p className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {reviewNote} — approval is blocked until this is corrected or returned to the engineer.
        </p>
      )}
      {canReview ? (
        <div className="mt-4 flex flex-wrap items-start gap-3">
          <button
            type="button"
            onClick={approve}
            disabled={busy || Boolean(reviewNote)}
            title={reviewNote ? "Nothing on this order to approve it against" : undefined}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Working…" : "Approve — on-site reading is correct"}
          </button>
          {!showReturn ? (
            <button
              type="button"
              onClick={() => setShowReturn(true)}
              disabled={busy}
              className="rounded-md border border-rose-400 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 disabled:opacity-50"
            >
              Return to engineer for re-verification
            </button>
          ) : (
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-start">
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={2}
                placeholder="Optional note for the engineer"
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
                disabled={busy}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={returnToEngineer}
                  disabled={busy}
                  className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Confirm return
                </button>
                <button
                  type="button"
                  onClick={() => { setShowReturn(false); setRemarks(""); }}
                  disabled={busy}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">Waiting on the assigned Service Team member, Service Manager, or Admin to review this.</p>
      )}
    </section>
  );
}
