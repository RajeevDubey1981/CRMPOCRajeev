import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import { formatApiError } from "../../utils/apiError.js";

// The serial the engineer entered doesn't match what the vendor's order actually assigned to this
// unit (order_item_serial_no/_2) -- the same basis Service Requests already use to tell a genuine
// mismatch from an ordinary first-time entry. No expected serial on file (non-vendor installs, or
// none set) means there's nothing to compare against, so it never counts as a mismatch.
export const hasSerialMismatch = row => {
  const expected1 = (row.order_item_serial_no || "").trim();
  const expected2 = (row.order_item_serial_no_2 || "").trim();
  if (!expected1 && !expected2) return false;
  const actual1 = (row.serial_no || "").trim();
  const actual2 = (row.serial_no_2 || "").trim();
  return (expected1 && actual1 && expected1 !== actual1) || (expected2 && actual2 && expected2 !== actual2);
};

// Once admin has verified the serial it's authoritative -- an engineer can no longer flag it for
// return even if it still reads as a mismatch, same as Service Requests (serial_verified_at gates it there too).
export const canReturnSerialRow = row => ["Assigned", "In Progress", "Serial Pending Verification", "Returned", "Rejected"].includes(row.status) && Boolean(row.serial_no) && !row.serial_verified_at && hasSerialMismatch(row);

export default function ReturnSelectedSerialsButton({ rows, onUpdated, disabled = false }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reasonField = useRef(null);
  const hasSelection = rows.length > 0;
  useEffect(() => {
    if (!hasSelection) { setReason(""); setError(""); }
  }, [hasSelection]);

  async function submit() {
    if (disabled || busy || !rows.length) return;
    if (reason.trim().length < 2) {
      setError("Enter a return reason of at least 2 characters before submitting.");
      reasonField.current?.focus();
      return;
    }
    setBusy(true); setError("");
    try {
      await api.post("/api/installation-returns", { installation_ids: rows.map(row => row.id), reason: reason.trim() });
      setReason(""); await onUpdated?.();
    } catch (e) { setError(formatApiError(e, "Unable to return selected serial rows")); }
    finally { setBusy(false); }
  }

  return <div className="contents">
    {hasSelection && <label className="order-first block w-full basis-full text-sm font-medium text-slate-700">
      Return reason <span className="text-rose-600">*</span>
      <textarea ref={reasonField} required minLength={2} rows={3} value={reason} onChange={e => { setReason(e.target.value); setError(""); }} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 font-normal" placeholder="Explain why the selected products are not available at the installation location" disabled={disabled || busy} />
      <span className="mt-1 block text-xs font-normal text-slate-500">Required before sending the selected serial rows for return approval. Other rows will continue unchanged.</span>
    </label>}
    <button type="button" disabled={disabled || busy || !hasSelection} onClick={submit} className="rounded-md border border-amber-500 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 disabled:opacity-50">{busy ? "Submitting..." : `Return selected (${rows.length})`}</button>
    {error && <p role="alert" className="w-full basis-full text-sm text-rose-700">{error}</p>}
  </div>;
}
