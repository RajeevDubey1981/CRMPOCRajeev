import { useEffect, useMemo, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { installationsApi } from "../../api/installations.js";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";

const ENGINEER_STATUSES = ["Assigned", "In Progress", "Completed", "Returned", "Rejected"];
const ADMIN_STATUSES = ["Assigned", "In Progress", "Completed", "Settlement Pending", "Settlement Approved", "Returned", "Rejected"];
const PAYMENT_TYPES = ["Cash", "UPI"];

function uniqueNonEmptyValues(rows, key) {
  return Array.from(new Set(rows.map((row) => row[key]).filter(Boolean)));
}

function displaySingleOrMixed(values, fallback = "-") {
  if (values.length === 0) return fallback;
  if (values.length === 1) return values[0];
  return "Mixed";
}

export default function BulkInstallationEditModal({ rows, onClose, onSaved }) {
  const { user } = useAuth();
  const isEngineer = user?.role === "engineer";
  const isAdminLike = isOperationsAdminRole(user?.role);
  const sharedStatuses = useMemo(() => uniqueNonEmptyValues(rows, "status"), [rows]);
  const sharedEngineerNames = useMemo(() => uniqueNonEmptyValues(rows, "assigned_engineer_name"), [rows]);
  const sharedServiceUserNames = useMemo(() => uniqueNonEmptyValues(rows, "assigned_service_user_name"), [rows]);
  const sharedPaymentTypes = useMemo(() => uniqueNonEmptyValues(rows, "payment_type_requested"), [rows]);
  const sharedPaymentAmounts = useMemo(() => uniqueNonEmptyValues(rows, "payment_amount_requested"), [rows]);
  const sharedQrPaths = useMemo(() => uniqueNonEmptyValues(rows, "payment_qr_code_path"), [rows]);
  const sharedInstallationDates = useMemo(
    () => uniqueNonEmptyValues(rows, "installation_date").map((value) => new Date(value).toISOString().slice(0, 10)),
    [rows],
  );
  const currentStatusText = displaySingleOrMixed(sharedStatuses);
  const currentEngineerText = displaySingleOrMixed(sharedEngineerNames);
  const currentServiceUserText = displaySingleOrMixed(sharedServiceUserNames);
  const currentQrPath = sharedQrPaths[0] || "";
  const hasMultipleQrSources = sharedQrPaths.length > 1;
  const isEngineerPaymentPendingMode = isEngineer && sharedStatuses.length === 1 && ["Payment Pending", "Returned", "Rejected"].includes(sharedStatuses[0]);
  const [form, setForm] = useState({
    new_status: isEngineer
      ? (isEngineerPaymentPendingMode ? "Completed" : "In Progress")
      : (sharedStatuses.length === 1 && sharedStatuses[0] === "Payment Pending" ? "Completed" : sharedStatuses[0] || "Assigned"),
    installation_date: sharedInstallationDates.length === 1 ? sharedInstallationDates[0] : "",
    work_report: "",
    payment_amount: sharedPaymentAmounts.length === 1 ? String(sharedPaymentAmounts[0]) : "",
    payment_type: sharedPaymentTypes.length === 1 ? sharedPaymentTypes[0] : "Cash",
    assigned_engineer: "",
    update_service_user: false,
    service_user_id: "",
  });
  const [serviceUsers, setServiceUsers] = useState([]);
  const [file, setFile] = useState(null);
  const [qrFile, setQrFile] = useState(null);
  const [qrObjectUrl, setQrObjectUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitErr, setSubmitErr] = useState("");

  const statuses = isEngineer
    ? (isEngineerPaymentPendingMode ? ["Completed"] : ENGINEER_STATUSES)
    : (sharedStatuses.length === 1 && sharedStatuses[0] === "Payment Pending" ? ["Completed", "Returned", "Rejected"] : ADMIN_STATUSES);
  const isCompleted = form.new_status === "Completed";
  const hasPaymentPendingRows = useMemo(
    () => rows.some((row) => row.status === "Payment Pending"),
    [rows],
  );
  const showPaymentSection = isCompleted || hasPaymentPendingRows;
  const isPaymentApprovalMode = isAdminLike && sharedStatuses.length === 1 && sharedStatuses[0] === "Payment Pending";
  const isEngineerPaymentUpdateMode = isEngineerPaymentPendingMode;
  const isUpiPaymentApproval = isPaymentApprovalMode && isCompleted && form.payment_type === "UPI";

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  useEffect(() => {
    if (!isAdminLike) return;
    installationsApi.serviceUsers().then(setServiceUsers).catch(() => setServiceUsers([]));
  }, [isAdminLike]);

  useEffect(() => {
    let active = true;
    let nextObjectUrl = "";

    async function loadProtectedQr() {
      if (!currentQrPath || !isAdminLike) {
        setQrObjectUrl("");
        return;
      }
      try {
        const response = await api.get(currentQrPath, { responseType: "blob" });
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
  }, [currentQrPath, isAdminLike]);

  async function submit() {
    setSubmitErr("");

    if (rows.length === 0) {
      setSubmitErr("No requests selected");
      return;
    }
    if (isCompleted && !form.installation_date) {
      setSubmitErr("Installation date is required when status is Completed");
      return;
    }
    if (isCompleted && !form.payment_amount) {
      setSubmitErr("Payment Amount is required when status is Completed");
      return;
    }
    if (showPaymentSection && form.payment_type === "UPI" && !qrFile && !currentQrPath) {
      setSubmitErr("QR Code is required when payment type is UPI");
      return;
    }
    if (isEngineer && isCompleted && !file) {
      setSubmitErr("Upload Document is required when status is Completed");
      return;
    }
    if (isUpiPaymentApproval && !file && rows.some((row) => !row.payment_proof_file_path)) {
      setSubmitErr("Upload Payment Proof / Document is required when payment type is UPI");
      return;
    }
    if (isAdminLike && form.update_service_user && !form.service_user_id) {
      setSubmitErr("Choose a service user or turn off Update service user");
      return;
    }

    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("installation_ids", rows.map((row) => row.id).join(","));
      fd.append("new_status", form.new_status);
      if (form.installation_date) fd.append("installation_date", form.installation_date);
      if (form.work_report) fd.append("work_report", form.work_report);
      if (form.assigned_engineer) fd.append("assigned_engineer", form.assigned_engineer);
      if (isAdminLike && form.update_service_user && form.service_user_id) {
        fd.append("service_user_id", form.service_user_id);
      }
      if (showPaymentSection && form.payment_amount) {
        fd.append("payment_amount", form.payment_amount);
        fd.append("payment_type", form.payment_type);
      }
      if (qrFile) fd.append("qr_code", qrFile);
      if (file) fd.append("document", file);

      await installationsApi.bulkUpdateStatus(fd);
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

  return (
    <Modal open={true} onClose={onClose} title={`Bulk Edit (${rows.length} request${rows.length === 1 ? "" : "s"})`} maxWidth="max-w-2xl">
      <div className="space-y-4">
        {submitErr && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>}

        <div className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Applying changes to request IDs: {rows.map((row) => row.id).join(", ")}
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>Current Status</label>
            <input value={currentStatusText} readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
          </div>
          <div>
            <label className={labelClass}>{isPaymentApprovalMode ? "Approval Status" : isEngineerPaymentUpdateMode ? "Payment Update Status" : "New Status"}</label>
            {isEngineerPaymentUpdateMode ? (
              <input value="Completed" readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
            ) : (
              <select value={form.new_status} onChange={(e) => set("new_status", e.target.value)} className={fieldClass}>
                {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            )}
          </div>
          <div>
            <label className={labelClass}>Installation Date</label>
            <input type="date" value={form.installation_date} onChange={(e) => set("installation_date", e.target.value)} className={fieldClass} />
          </div>
        </div>

        {isAdminLike && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className={labelClass}>Assigned Engineer</label>
              <input value={currentEngineerText} readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
            </div>
            <div>
              <label className={labelClass}>Current Service User</label>
              <input value={currentServiceUserText} readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
            </div>
            <label className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 md:col-span-2">
              <input
                type="checkbox"
                checked={form.update_service_user}
                onChange={(e) => set("update_service_user", e.target.checked)}
                className="h-4 w-4"
              />
              Update service user for selected requests
            </label>
            <div className="md:col-span-2">
              <label className={labelClass}>Service User</label>
              <select
                value={form.service_user_id}
                onChange={(e) => set("service_user_id", e.target.value)}
                disabled={!form.update_service_user}
                className={`${fieldClass} disabled:bg-slate-100 disabled:text-slate-400`}
              >
                <option value="">Select service user</option>
                {serviceUsers.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} {option.email ? `(${option.email})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div>
          <label className={labelClass}>Work Report</label>
          <textarea rows={3} value={form.work_report} onChange={(e) => set("work_report", e.target.value)} className={fieldClass} />
        </div>

        {showPaymentSection && (
          <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
            {isPaymentApprovalMode && (
              <div className="rounded-md bg-white/70 px-3 py-2 text-sm text-slate-700">
                Admin payment approval: review the engineer-submitted amount, view the QR code below, and then choose Completed, Returned, or Rejected.
              </div>
            )}
            {isEngineerPaymentUpdateMode && (
              <div className="rounded-md bg-white/70 px-3 py-2 text-sm text-slate-700">
                Payment request already raised. You can still update the payment amount, payment type, QR code, and installation date before admin approval.
              </div>
            )}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <label className={labelClass}>Payment Amount</label>
                <input type="number" min="0" step="0.01" value={form.payment_amount} onChange={(e) => set("payment_amount", e.target.value)} className={fieldClass} />
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
                {currentQrPath && (
                  <div className="rounded-md bg-white/70 px-3 py-2 text-sm text-slate-700">
                    <div className="font-medium">Saved QR Code</div>
                    {hasMultipleQrSources && (
                      <div className="mt-1 text-xs text-slate-500">
                        Showing QR preview from one selected request in this group.
                      </div>
                    )}
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
                  <label className={labelClass}>QR Code</label>
                  <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => setQrFile(e.target.files?.[0] || null)} className="block w-full text-sm" />
                </div>
              </div>
            )}
          </div>
        )}

        <div>
          <label className={labelClass}>
            {isAdminLike ? `Upload Payment Proof / Document${isUpiPaymentApproval ? " *" : ""}` : `Upload Document${isEngineer && isCompleted ? " *" : ""}`}
          </label>
          <input type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={(e) => setFile(e.target.files?.[0] || null)} className="block w-full text-sm" />
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
          <button type="button" onClick={submit} disabled={busy} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
            {busy ? (isPaymentApprovalMode ? "Approving..." : "Saving...") : (isPaymentApprovalMode ? "Approve Payment" : isEngineerPaymentUpdateMode ? "Update Payment Request" : "Save Changes")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
