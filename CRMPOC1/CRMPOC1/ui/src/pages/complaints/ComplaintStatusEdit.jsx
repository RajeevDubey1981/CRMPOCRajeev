import { useEffect, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import { complaintsApi, serialsApi } from "../../api/complaints.js";
import { installationsApi } from "../../api/installations.js";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";
import EngineerSelect from "../../components/EngineerSelect.jsx";

const STATUSES = ["Pending", "Under Process", "In Process", "Resolved", "Rejected"];

export default function ComplaintStatusEdit({ complaint, onClose, onSaved }) {
  const { user } = useAuth();
  const isEngineer = (user?.role || "").toLowerCase() === "engineer";
  const [engineers, setEngineers] = useState([]);
  const [form, setForm] = useState({
    new_status: complaint.status || "Pending",
    access_code: "",
    serial_no: "",
    assigned_engineer: complaint.assigned_engineer || "",
    remark: "",
  });
  const [file, setFile] = useState(null);
  const [serialInfo, setSerialInfo] = useState(null);
  const [lookupErr, setLookupErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitErr, setSubmitErr] = useState("");

  useEffect(() => {
    if (isEngineer) return;
    installationsApi.engineerAssignmentOptions()
      .then(setEngineers)
      .catch(() => setEngineers([]));
  }, [isEngineer]);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  async function lookupSerial() {
    setLookupErr("");
    setSerialInfo(null);
    if (!form.serial_no.trim()) {
      setLookupErr("Enter a serial number first");
      return;
    }
    try {
      setSerialInfo(await serialsApi.lookup(form.serial_no.trim()));
    } catch (e) {
      setLookupErr(e.response?.data?.detail || "Serial not found");
    }
  }

  async function submit() {
    setSubmitErr("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("new_status", form.new_status);
      if (form.access_code) fd.append("access_code", form.access_code);
      if (form.serial_no) fd.append("serial_no", form.serial_no);
      if (!isEngineer && form.assigned_engineer) fd.append("assigned_engineer", String(form.assigned_engineer));
      if (form.remark) fd.append("remark", form.remark);
      if (file) fd.append("document", file);
      await complaintsApi.updateStatus(complaint.id, fd);
      onSaved?.();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setSubmitErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to update");
    } finally {
      setBusy(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";
  const needsAccessCode = form.new_status === "Resolved";

  return (
    <Modal open={true} onClose={onClose} title={`Edit status — ${complaint.comp_no}`} maxWidth="max-w-2xl">
      <div className="space-y-4">
        {submitErr && (
          <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>New Status</label>
            <select value={form.new_status} onChange={(e) => set("new_status", e.target.value)} className={fieldClass}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className={labelClass}>
              Access Code {needsAccessCode && <span className="text-rose-600">*</span>}
            </label>
            <input
              value={form.access_code}
              onChange={(e) => set("access_code", e.target.value)}
              className={fieldClass}
              placeholder={needsAccessCode ? "Required to mark Resolved" : "(optional)"}
            />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass}>Serial Number</label>
            <div className="flex gap-2">
              <input
                value={form.serial_no}
                onChange={(e) => set("serial_no", e.target.value)}
                className={`${fieldClass} flex-1`}
                placeholder="e.g. SN12345"
              />
              <button
                type="button"
                onClick={lookupSerial}
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
              >
                Get Serial No Detail
              </button>
            </div>
            {lookupErr && <p className="mt-1 text-xs text-rose-600">{lookupErr}</p>}
            {serialInfo && (
              <div className="mt-2 rounded-md bg-slate-50 p-3 text-xs">
                <div><strong>Item:</strong> {serialInfo.item_name || "—"} ({serialInfo.item_code || "—"})</div>
                <div><strong>Order:</strong> {serialInfo.order_no || "—"}</div>
                <div><strong>Customer:</strong> {serialInfo.customer_name || "—"} ({serialInfo.customer_contact || "—"})</div>
                <div><strong>Warranties:</strong> PCB {serialInfo.pcb_warranty_date || "—"} | Component {serialInfo.component_warranty_date || "—"} | Machine {serialInfo.machine_warranty_date || "—"}</div>
                <div><strong>Installation:</strong> {serialInfo.installation_status}</div>
                <div><strong>Free service:</strong> {serialInfo.service_consume_count}/{serialInfo.free_service_count}</div>
              </div>
            )}
          </div>

          {!isEngineer && (
            <div>
              <label className={labelClass}>Assign Engineer</label>
              <EngineerSelect engineers={engineers} value={form.assigned_engineer} onChange={(e) => set("assigned_engineer", e.target.value ? Number(e.target.value) : "")} emptyLabel="— Unassigned —" selectClassName={fieldClass} />
              <p className="mt-1 text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
            </div>
          )}

          <div>
            <label className={labelClass}>Upload Document</label>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm"
            />
            <p className="mt-1 text-xs text-slate-500">PDF, DOC, DOCX, JPG, PNG · max 2MB</p>
          </div>
        </div>

        <div>
          <label className={labelClass}>Remark</label>
          <textarea
            rows={3}
            value={form.remark}
            onChange={(e) => set("remark", e.target.value)}
            className={fieldClass}
          />
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save status"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
