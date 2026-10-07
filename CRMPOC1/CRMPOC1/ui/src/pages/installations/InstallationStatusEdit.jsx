import { useEffect, useMemo, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { api } from "../../api/client.js";
import { installationsApi } from "../../api/installations.js";
import { usersApi } from "../../api/complaints.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";
import EngineerSelect from "../../components/EngineerSelect.jsx";

const BASE_STATUSES = ["Pending", "Assigned", "In Progress", "Installation Completed", "Payment Pending", "Completed", "Settlement Pending", "Settlement Approved", "Returned", "Rejected"];
const SEND_BACK_VALUE = "Send Back to Admin";
const PAYMENT_TYPES = ["Cash", "UPI"];

export default function InstallationStatusEdit({ installation, onClose, onSaved, inline = false }) {
  const { user } = useAuth();
  const isEngineer = user?.role === "engineer";
  const isAdminLike = isOperationsAdminRole(user?.role);
  const isEngineerPaymentPendingMode = isEngineer && ["Payment Pending", "Returned", "Rejected"].includes(installation.status);
  const [engineers, setEngineers] = useState([]);
  const [approvers, setApprovers] = useState([]);
  const [form, setForm] = useState({
    new_status: isEngineerPaymentPendingMode ? "Completed" : (installation.status || "Pending"),
    assigned_engineer: installation.assigned_engineer || "",
    installation_date: installation.installation_date ? new Date(installation.installation_date).toISOString().slice(0, 10) : "",
    work_report: installation.work_report || "",
    settlement_approved_by: installation.settlement_approved_by || "",
    payment_amount: installation.payment_amount_paid || installation.payment_amount_requested || "",
    payment_type: installation.payment_type_paid || installation.payment_type_requested || "Cash",
  });
  const [file, setFile] = useState(null);
  const [qrFile, setQrFile] = useState(null);
  const [qrObjectUrl, setQrObjectUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitErr, setSubmitErr] = useState("");
  const [submitOk, setSubmitOk] = useState("");

  function buildFormState(currentInstallation) {
    return {
      new_status: isEngineerPaymentPendingMode ? "Completed" : (currentInstallation.status || "Pending"),
      assigned_engineer: currentInstallation.assigned_engineer || "",
      installation_date: currentInstallation.installation_date
        ? new Date(currentInstallation.installation_date).toISOString().slice(0, 10)
        : "",
      work_report: currentInstallation.work_report || "",
      settlement_approved_by: currentInstallation.settlement_approved_by || "",
      payment_amount: currentInstallation.payment_amount_paid || currentInstallation.payment_amount_requested || "",
      payment_type: currentInstallation.payment_type_paid || currentInstallation.payment_type_requested || "Cash",
    };
  }

  useEffect(() => {
    setForm(buildFormState(installation));
    setFile(null);
    setQrFile(null);
    setSubmitErr("");
  }, [
    installation.id,
    installation.status,
    installation.updated_at,
    installation.work_report,
    installation.assigned_engineer,
    installation.installation_date,
    installation.settlement_approved_by,
    installation.payment_amount_paid,
    installation.payment_amount_requested,
    installation.payment_type_paid,
    installation.payment_type_requested,
    isEngineerPaymentPendingMode,
  ]);

  const paymentApprovalMode = isAdminLike && installation.status === "Payment Pending";
  const adminCanEditPayment = isAdminLike;
  const isCompleted = form.new_status === "Completed";
  const editingCompletedRecord = installation.status === "Completed" && !paymentApprovalMode && !isEngineerPaymentPendingMode && !adminCanEditPayment;
  const shouldCollectPayment = (isCompleted && !editingCompletedRecord) || (adminCanEditPayment && installation.status === "Completed");
  const availableStatuses = useMemo(() => {
    if (isEngineerPaymentPendingMode) {
      return ["Completed"];
    }
    const list = [...BASE_STATUSES];
    if (paymentApprovalMode) return ["Completed", "Returned", "Rejected"];
    return list;
  }, [isEngineerPaymentPendingMode, paymentApprovalMode]);
  const isUpiPaymentApproval = paymentApprovalMode && isCompleted && form.payment_type === "UPI";

  useEffect(() => {
    installationsApi.engineerAssignmentOptions(installation.address, installation)
      .then(setEngineers)
      .catch(() => setEngineers([]));

    Promise.all([
      usersApi.list({ role: "admin" }).catch(() => []),
      usersApi.list({ role: "incool" }).catch(() => []),
    ]).then(([adminUsers, incoolUsers]) => {
      const seen = new Set();
      const merged = [...adminUsers, ...incoolUsers].filter((entry) => {
        if (seen.has(entry.id)) return false;
        seen.add(entry.id);
        return true;
      });
      setApprovers(merged);
    }).catch(() => setApprovers([]));
  }, []);

  useEffect(() => {
    let active = true;
    let nextObjectUrl = "";

    async function loadProtectedQr() {
      if (!installation.payment_qr_code_path || !isAdminLike) {
        setQrObjectUrl("");
        return;
      }
      try {
        const response = await api.get(installation.payment_qr_code_path, { responseType: "blob" });
        nextObjectUrl = URL.createObjectURL(response.data);
        if (active) setQrObjectUrl(nextObjectUrl);
      } catch {
        if (active) setQrObjectUrl("");
      }
    }

    loadProtectedQr();

    return () => {
      active = false;
      if (nextObjectUrl) URL.revokeObjectURL(nextObjectUrl);
    };
  }, [installation.payment_qr_code_path, isAdminLike]);

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function submit() {
    setSubmitErr("");
    setSubmitOk("");
    setBusy(true);
    try {
      if (isCompleted && !form.installation_date) {
        setSubmitErr("Installation date is required when status is Completed");
        setBusy(false);
        return;
      }
      if (shouldCollectPayment && form.payment_amount === "" && !adminCanEditPayment) {
        setSubmitErr("Payment Amount is required when status is Completed");
        setBusy(false);
        return;
      }
      if (shouldCollectPayment && form.payment_type === "UPI" && !qrFile) {
        setSubmitErr("QR Code is required when payment type is UPI");
        setBusy(false);
        return;
      }
      if (isEngineer && isCompleted && !file && !installation.work_report_file_path) {
        setSubmitErr("Upload Document is required when status is Completed");
        setBusy(false);
        return;
      }
      if (isUpiPaymentApproval && !file && !installation.payment_proof_file_path) {
        setSubmitErr("Upload Payment Proof / Document is required when payment type is UPI");
        setBusy(false);
        return;
      }

      if (adminCanEditPayment && installation.status === "Completed" && !paymentApprovalMode && form.payment_amount !== "") {
        await installationsApi.updatePaymentAmount(installation.id, {
          payment_amount_requested: Number(form.payment_amount),
          payment_amount_paid: Number(form.payment_amount),
          payment_type_requested: form.payment_type,
          payment_type_paid: form.payment_type,
        });
        setSubmitOk("Payment amount updated.");
        onSaved?.();
        return;
      }

      const fd = new FormData();
      fd.append("new_status", form.new_status);
      if (form.new_status !== SEND_BACK_VALUE) {
        if (form.assigned_engineer) fd.append("assigned_engineer", String(form.assigned_engineer));
        if (form.installation_date) fd.append("installation_date", form.installation_date);
        if (form.work_report) fd.append("work_report", form.work_report);
        if (form.settlement_approved_by) fd.append("settlement_approved_by", String(form.settlement_approved_by));
        if (shouldCollectPayment) {
          fd.append("payment_amount", String(form.payment_amount));
          fd.append("payment_type", form.payment_type);
          if (qrFile) fd.append("qr_code", qrFile);
        }
        if (file) fd.append("document", file);
      }
      await installationsApi.updateStatus(installation.id, fd);
      setSubmitOk(paymentApprovalMode ? "Payment approved." : "Changes saved.");
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

  const formContent = (
    <div className="space-y-4">
      {submitErr && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>
      )}
      {submitOk && (
        <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{submitOk}</div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className={labelClass}>Status</label>
          {isEngineerPaymentPendingMode ? (
            <input value="Completed" readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
          ) : (
            <select value={form.new_status} onChange={(e) => set("new_status", e.target.value)} className={fieldClass}>
              {availableStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
              {isEngineer && installation.status === "Assigned" && (
                <option value={SEND_BACK_VALUE}>Cancel (send back to admin)</option>
              )}
            </select>
          )}
        </div>

        <div>
          <label className={labelClass}>Installation Date</label>
          <input
            type="date"
            value={form.installation_date}
            onChange={(e) => set("installation_date", e.target.value)}
            className={fieldClass}
          />
        </div>

        {!isEngineer && (
          <div>
            <label className={labelClass}>Assign Engineer</label>
            <EngineerSelect engineers={engineers} value={form.assigned_engineer} onChange={(e) => set("assigned_engineer", e.target.value ? Number(e.target.value) : "")} emptyLabel="-- Unassigned --" selectClassName={fieldClass} />
            <p className="mt-1 text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
            {installation.assigned_engineer_name && (
              <p className="mt-1 text-xs text-slate-500">Current engineer: {installation.assigned_engineer_name}</p>
            )}
          </div>
        )}

        {!isEngineer && (
          <div>
            <label className={labelClass}>Settlement Raised By</label>
            <select
              value={form.settlement_approved_by}
              onChange={(e) => set("settlement_approved_by", e.target.value ? Number(e.target.value) : "")}
              className={fieldClass}
            >
              <option value="">-- None --</option>
              {approvers.map((approver) => (
                <option key={approver.id} value={approver.id}>{approver.name} ({approver.email})</option>
              ))}
            </select>
            {installation.settlement_approved_by_name && (
              <p className="mt-1 text-xs text-slate-500">Current raised by: {installation.settlement_approved_by_name}</p>
            )}
          </div>
        )}
      </div>

      <div>
        <label className={labelClass}>Work Report</label>
        <textarea
          rows={3}
          value={form.work_report}
          onChange={(e) => set("work_report", e.target.value)}
          className={fieldClass}
          placeholder="Summary of work completed"
        />
      </div>

      {shouldCollectPayment && (
        <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          {isEngineerPaymentPendingMode && (
            <div className="rounded-md bg-white/70 px-3 py-2 text-sm text-slate-700">
              Payment request is open again. You can update the payment amount, payment type, QR code, and installation date before sending it back for admin approval.
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className={labelClass}>Payment Amount</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.payment_amount}
                onChange={(e) => set("payment_amount", e.target.value)}
                className={fieldClass}
              />
              {paymentApprovalMode && installation.payment_amount_requested != null && (
                <p className="mt-1 text-xs text-slate-500">
                  Engineer submitted: {installation.payment_amount_requested}. Admin decides the final approved amount.
                </p>
              )}
              {adminCanEditPayment && installation.status === "Completed" && !paymentApprovalMode && (
                <p className="mt-1 text-xs text-slate-500">Admin can update the final payment amount at any time.</p>
              )}
            </div>

            <div>
              <label className={labelClass}>Payment Type</label>
              <select value={form.payment_type} onChange={(e) => set("payment_type", e.target.value)} className={fieldClass}>
                {PAYMENT_TYPES.map((paymentType) => <option key={paymentType} value={paymentType}>{paymentType}</option>)}
              </select>
            </div>
          </div>

          {form.payment_type === "UPI" && (
            <div className="space-y-2">
              {installation.payment_qr_code_path && (
                <div className="rounded-md bg-white/70 px-3 py-2 text-sm text-slate-700">
                  <div className="font-medium">Saved QR Code</div>
                  {qrObjectUrl && (
                    <img
                      src={qrObjectUrl}
                      alt="Payment QR Code"
                      className="mt-2 max-h-64 rounded border border-slate-200 bg-white object-contain"
                    />
                  )}
                  {!qrObjectUrl && (
                    <div className="mt-2 text-xs text-rose-600">
                      Unable to preview QR code in the browser. Please re-upload the QR code if needed.
                    </div>
                  )}
                </div>
              )}
              <div>
                <label className={labelClass}>QR Code *</label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  required
                  onChange={(e) => setQrFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm"
                />
              </div>
            </div>
          )}
        </div>
      )}

      <div>
        <label className={labelClass}>
          {isUpiPaymentApproval
            ? "Upload Payment Proof / Document *"
            : editingCompletedRecord
              ? "Upload work document"
              : `Upload Document${isEngineer && isCompleted ? " *" : ""}`}
        </label>
        <input
          type="file"
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm"
        />
        <p className="mt-1 text-xs text-slate-500">PDF, DOC, DOCX, JPG, PNG - max 2MB</p>
      </div>

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
          {inline ? "Close" : "Cancel"}
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? (paymentApprovalMode ? "Approving..." : "Saving...") : (paymentApprovalMode ? "Approve Payment" : isEngineerPaymentPendingMode ? "Update Payment Request" : "Save changes")}
        </button>
      </div>
    </div>
  );

  if (inline) return formContent;

  return (
    <Modal open={true} onClose={onClose} title={`Edit installation - ID ${installation.id}`} maxWidth="max-w-2xl">
      {formContent}
    </Modal>
  );
}
