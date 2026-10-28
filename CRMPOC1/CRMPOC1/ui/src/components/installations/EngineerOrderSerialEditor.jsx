import ReturnSelectedSerialsButton, { canReturnSerialRow } from "./ReturnSelectedSerialsButton.jsx";
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
  const [popupError, setPopupError] = useState("");
  const [savedAt, setSavedAt] = useState(0);

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

  if (Number(installation.assigned_engineer) !== Number(userId)) return null;

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

  const inputClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
  return (
    <>
    <section className="mt-4 rounded-lg border border-sky-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">Update order serial numbers</h3>
      <p className="mt-1 text-xs text-slate-600">
        Scan or enter both serial numbers. Every entered serial must belong to order {installation.order_no || `#${installation.order_id}`}.
      </p>
      <div className="mt-3 flex items-start gap-3">
        <input type="checkbox" aria-label="Select serial row to return" checked={selectedForReturn} onChange={e => setSelectedForReturn(e.target.checked)} disabled={saving || !canReturnSerialRow(installation)} className="mt-8 h-4 w-4 shrink-0" />
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
      <ReturnSelectedSerialsButton rows={selectedForReturn && canReturnSerialRow(installation) ? [installation] : []} disabled={saving} onUpdated={async () => { setSelectedForReturn(false); await onUpdated?.(); }} />
      {savedAt > 0 && <span className="text-sm font-medium text-emerald-700">✓ Saved</span>}
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
