import ReturnSelectedSerialsButton, { canReturnSerialRow, hasSerialMismatch } from "./ReturnSelectedSerialsButton.jsx";
import { useEffect, useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { formatApiError } from "../../utils/apiError.js";
import Modal from "../Modal.jsx";
import ScanInput from "../scan/ScanInput.jsx";

export default function EngineerOrderSerialEditor({ installation, userId, onUpdated, onError, onBusy }) {
  const [serialNo, setSerialNo] = useState(installation.serial_no || "");
  const [serialNo2, setSerialNo2] = useState(installation.serial_no_2 || "");
  const [selectedForReturn, setSelectedForReturn] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reVerifying, setReVerifying] = useState(false);
  const [popupError, setPopupError] = useState("");
  const [savedAt, setSavedAt] = useState(0);
  const [reVerifiedAt, setReVerifiedAt] = useState(0);

  useEffect(() => {
    setSelectedForReturn(false);
    setSerialNo(installation.serial_no || "");
    setSerialNo2(installation.serial_no_2 || "");
  }, [installation.id, installation.serial_no, installation.serial_no_2]);

  // The save can legitimately be a no-op (the engineer re-enters the same serials that already matched),
  // so the data on screen doesn't change -- without this, a successful click looked identical to a
  // silently failed one and engineers kept re-clicking, thinking it wasn't working.
  useEffect(() => {
    if (!savedAt) return undefined;
    const timer = setTimeout(() => setSavedAt(0), 4000);
    return () => clearTimeout(timer);
  }, [savedAt]);

  useEffect(() => {
    if (!reVerifiedAt) return undefined;
    const timer = setTimeout(() => setReVerifiedAt(0), 4000);
    return () => clearTimeout(timer);
  }, [reVerifiedAt]);

  if (Number(installation.assigned_engineer) !== Number(userId)) return null;

  // A vendor-order serial is auto-trusted the moment the engineer is assigned -- it's never cleared
  // just because they later type something different here. This is the separate, deliberate "I've
  // corrected it, please check this one" action, open whenever there's a serial and the request is
  // still open (not whatever triggers Return's own, narrower mismatch gate).
  const canReVerify = Boolean((installation.serial_no || "").trim())
    && !["Completed", "Settlement Approved", "Rejected", "Returned"].includes(installation.status);

  async function save() {
    onError?.("");
    setPopupError("");
    setSaving(true);
    onBusy?.(true);
    try {
      await installationsApi.updateEngineerOrderSerials(installation.id, {
        serial_no: serialNo.trim(),
        serial_no_2: serialNo2.trim() || null,
      });
      setSavedAt(Date.now());
      onUpdated?.();
    } catch (error) {
      setPopupError(formatApiError(error, "Unable to update serial numbers"));
    } finally {
      setSaving(false);
      onBusy?.(false);
    }
  }

  async function reVerify() {
    onError?.("");
    setPopupError("");
    setReVerifying(true);
    onBusy?.(true);
    try {
      await installationsApi.reVerifyEngineerOrderSerial(installation.id);
      setReVerifiedAt(Date.now());
      onUpdated?.();
    } catch (error) {
      setPopupError(formatApiError(error, "Unable to request re-verification"));
    } finally {
      setReVerifying(false);
      onBusy?.(false);
    }
  }

  const inputClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
  return (
    <>
    <section className={`mt-4 rounded-lg border p-4 shadow-sm transition-colors duration-700 ${savedAt > 0 ? "border-emerald-200 bg-emerald-50" : reVerifiedAt > 0 ? "border-violet-200 bg-violet-50" : "border-sky-200 bg-white"}`}>
      <h3 className="text-sm font-semibold text-slate-800">Update order serial numbers</h3>
      <p className="mt-1 text-xs text-slate-600">
        Scan or enter both serial numbers. Every entered serial must belong to order {installation.order_no || `#${installation.order_id}`}.
      </p>
      <div className="mt-3 flex items-start gap-3">
        <input
          type="checkbox"
          aria-label="Select serial row to return"
          checked={selectedForReturn}
          onChange={e => setSelectedForReturn(e.target.checked)}
          disabled={saving || !canReturnSerialRow(installation)}
          title={hasSerialMismatch(installation) ? "Select to return — scanned serial doesn't match the order" : "Available only when the scanned serial doesn't match what the order assigned to this unit"}
          className="mt-8 h-4 w-4 shrink-0"
        />
        <div className="grid min-w-0 flex-1 grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 1 *</label>
          <ScanInput value={serialNo} onValue={setSerialNo} placeholder="Scan serial number 1" className={inputClass} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 2</label>
          <ScanInput value={serialNo2} onValue={setSerialNo2} placeholder="Scan serial number 2" className={inputClass} />
        </div>
      </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={save}
        disabled={saving || !serialNo.trim()}
        className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Updating…" : "Update serial numbers"}
      </button>
      <button
        type="button"
        onClick={reVerify}
        disabled={reVerifying || saving || !canReVerify}
        title="Clears the earlier auto-verification and puts this back in front of admin to check the current serial"
        className="rounded-md border border-violet-300 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {reVerifying ? "Requesting…" : "Re-verify"}
      </button>
      <ReturnSelectedSerialsButton rows={selectedForReturn && canReturnSerialRow(installation) ? [installation] : []} disabled={saving} onUpdated={async () => { setSelectedForReturn(false); await onUpdated?.(); }} />
      {savedAt > 0 && <span className="text-sm font-medium text-emerald-700">✓ Saved</span>}
      {reVerifiedAt > 0 && <span className="text-sm font-medium text-violet-700">✓ Sent for re-verification</span>}
      </div>
    </section>
    <Modal open={Boolean(popupError)} onClose={() => setPopupError("")} title="Serial numbers not updated">
      <div className="space-y-4">
        <p className="text-sm text-rose-700">{popupError}</p>
        <div className="flex justify-end">
          <button type="button" onClick={() => setPopupError("")} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white">
            Close
          </button>
        </div>
      </div>
    </Modal>
    </>
  );
}
