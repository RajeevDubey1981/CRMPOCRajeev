import ReturnSelectedSerialsButton, { ORDER_MEMBERSHIP_ERROR, canReturnAfterOrderMembershipRejection, canReturnSerialRow, hasSerialMismatch } from "./ReturnSelectedSerialsButton.jsx";
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
  const [orderRejected, setOrderRejected] = useState(false);

  useEffect(() => {
    setSelectedForReturn(false);
    setSerialNo(installation.serial_no || "");
    setSerialNo2(installation.serial_no_2 || "");
    setOrderRejected(false);
  }, [installation.id, installation.serial_no, installation.serial_no_2]);

  // A scanned serial that doesn't belong to this order at all is rejected outright by the save --
  // the row itself never changes, so the normal "saved serial differs from the order" check can never
  // see it. This is the only way Return still unlocks for that case.
  const canReturn = canReturnSerialRow(installation) || (orderRejected && canReturnAfterOrderMembershipRejection(installation));

  if (Number(installation.assigned_engineer) !== Number(userId)) return null;

  // Stays on (doesn't time out) until a field is edited again, so it stays an honest reflection of
  // "what's on screen matches what's saved" rather than quietly reverting while nothing has changed.
  function editSerialNo(value) {
    setSerialNo(value);
    setSavedAt(0);
    setOrderRejected(false);
  }
  function editSerialNo2(value) {
    setSerialNo2(value);
    setSavedAt(0);
    setOrderRejected(false);
  }

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
      setOrderRejected(false);
      onUpdated?.();
    } catch (error) {
      const message = formatApiError(error, "Unable to update serial numbers");
      setOrderRejected(message === ORDER_MEMBERSHIP_ERROR);
      setPopupError(message);
    } finally {
      setSaving(false);
      onBusy?.(false);
    }
  }

  const inputClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
  return (
    <>
    <section className={`mt-4 rounded-lg border p-4 shadow-sm transition-colors duration-700 ${savedAt > 0 ? "border-emerald-200 bg-emerald-50" : "border-sky-200 bg-white"}`}>
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
          disabled={saving || !canReturn}
          title={hasSerialMismatch(installation) || orderRejected ? "Select to return — scanned serial doesn't match the order" : "Available only when the scanned serial doesn't match what the order assigned to this unit"}
          className="mt-8 h-4 w-4 shrink-0"
        />
        <div className="grid min-w-0 flex-1 grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 1 *</label>
          <ScanInput value={serialNo} onValue={editSerialNo} placeholder="Scan serial number 1" className={inputClass} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 2</label>
          <ScanInput value={serialNo2} onValue={editSerialNo2} placeholder="Scan serial number 2" className={inputClass} />
        </div>
      </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={save}
        disabled={saving || !serialNo.trim()}
        className={`rounded-md px-4 py-2 text-sm font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${savedAt > 0 ? "bg-emerald-600" : "bg-sky-700"}`}
      >
        {saving ? "Updating…" : savedAt > 0 ? "Updated ✓" : "Update serial numbers"}
      </button>
      <ReturnSelectedSerialsButton rows={selectedForReturn && canReturn ? [installation] : []} disabled={saving} onUpdated={async () => { setSelectedForReturn(false); setOrderRejected(false); await onUpdated?.(); }} />
      </div>
    </section>
    <Modal open={Boolean(popupError)} onClose={() => setPopupError("")} title="Serial numbers not updated">
      <div className="space-y-4">
        <p className="text-sm text-rose-700">{popupError}</p>
        {orderRejected && (
          <p className="text-sm text-slate-600">
            If this unit genuinely isn't on this order, tick the box next to Serial number 1 and use <strong>Return selected</strong> instead of trying to save it.
          </p>
        )}
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
