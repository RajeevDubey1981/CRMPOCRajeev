import { useEffect, useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { formatApiError } from "../../utils/apiError.js";
import Modal from "../Modal.jsx";
import ScanInput from "../scan/ScanInput.jsx";

export default function EngineerOrderSerialEditor({ installation, userId, onUpdated, onError, onBusy }) {
  const [serialNo, setSerialNo] = useState(installation.serial_no || "");
  const [serialNo2, setSerialNo2] = useState(installation.serial_no_2 || "");
  const [popupError, setPopupError] = useState("");

  useEffect(() => {
    setSerialNo(installation.serial_no || "");
    setSerialNo2(installation.serial_no_2 || "");
  }, [installation.id, installation.serial_no, installation.serial_no_2]);

  if (Number(installation.assigned_engineer) !== Number(userId)) return null;

  async function save() {
    onError?.("");
    setPopupError("");
    onBusy?.(true);
    try {
      await installationsApi.updateEngineerOrderSerials(installation.id, {
        serial_no: serialNo.trim(),
        serial_no_2: serialNo2.trim() || null,
      });
      onUpdated?.();
    } catch (error) {
      setPopupError(formatApiError(error, "Unable to update serial numbers"));
    } finally {
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
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 1 *</label>
          <ScanInput value={serialNo} onValue={setSerialNo} placeholder="Scan serial number 1" className={inputClass} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Serial number 2</label>
          <ScanInput value={serialNo2} onValue={setSerialNo2} placeholder="Scan serial number 2" className={inputClass} />
        </div>
      </div>
      <button
        type="button"
        onClick={save}
        disabled={!serialNo.trim()}
        className="mt-3 rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        Update serial numbers
      </button>
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
