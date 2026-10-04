import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import StatusBadge from "../../components/StatusBadge.jsx";
import { installationsApi } from "../../api/installations.js";
import {
  adminBulkReviewActionLabel,
  isBulkWorkflowEligibleRow,
} from "../../utils/installationWorkflowSteps.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";

const PAYMENT_TYPES = ["Cash", "UPI"];

function todayInputValue() {
  return new Date().toISOString().slice(0, 10);
}

function completionProofSummary(row) {
  const proofs = row?.completion_proofs;
  if (Array.isArray(proofs) && proofs.length > 0) {
    const uploaded = proofs.filter((proof) => proof.file_path).length;
    return `${uploaded}/${proofs.length} proof(s)`;
  }
  if (row?.work_report_file_path) return "1 proof";
  return "-";
}

function completionApprovalStatus(row) {
  if (row.status === "Completion Pending Approval") return "Pending admin approval";
  if (["Installation Completed", "Payment Pending", "Completed"].includes(row.status)) return "Approved";
  if (["Returned", "Rejected"].includes(row.status) && (row.admin_approval_remark || "").trim()) {
    return "Returned for correction";
  }
  if (row.status === "Service Team Review") return "Service Role review";
  return "Not submitted";
}

function canCompleteRow(row) {
  return ["Assigned", "In Progress", "Returned", "Rejected"].includes(row.status);
}

function canRequestPaymentRow(row) {
  return row.status === "Installation Completed";
}

function shouldShowAdminRemark(row) {
  return Boolean((row.admin_approval_remark || "").trim())
    && ["Returned", "Rejected", "Service Team Review", "Assigned", "In Progress"].includes(row.status);
}

function rowNeedsSecondProof(row) {
  return Boolean((row.serial_no_2 || row.engineer_entered_serial_no_2 || "").trim());
}

function defaultRowForm(row, existing = {}) {
  return {
    selectedForCompletion: existing.selectedForCompletion ?? canCompleteRow(row),
    selectedForPayment: existing.selectedForPayment ?? canRequestPaymentRow(row),
    installation_date: existing.installation_date || todayInputValue(),
    work_report: existing.work_report || "",
    proof_document: existing.proof_document || null,
    proof_document_serial_2: existing.proof_document_serial_2 || null,
    observation: existing.observation || row.engineer_site_remarks || "",
    payment_amount: existing.payment_amount ?? (
      row.payment_amount_requested != null ? String(row.payment_amount_requested) : ""
    ),
  };
}

export default function BulkInstallationWorkflowPanel({ rows, onSaved, showClose, onClose }) {
  const { user } = useAuth();
  const isAdminLike = isOperationsAdminRole(user?.role);
  const [workflowRows, setWorkflowRows] = useState(rows);
  const [rowForms, setRowForms] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [paymentForm, setPaymentForm] = useState({
    payment_type: "Cash",
    work_report: "",
    qr_code: null,
  });

  useEffect(() => {
    setWorkflowRows(rows);
    setRowForms((current) => {
      const next = {};
      rows.forEach((row) => {
        next[row.id] = defaultRowForm(row, current[row.id]);
      });
      return next;
    });
  }, [rows]);

  const eligibleRows = useMemo(
    () => workflowRows.filter((row) => isBulkWorkflowEligibleRow(row, {
      isAdminLike,
      userId: user?.id,
      userName: user?.name,
    })),
    [workflowRows, isAdminLike, user?.id, user?.name],
  );
  const assignedRows = useMemo(
    () => eligibleRows.filter((row) => row.status === "Assigned"),
    [eligibleRows],
  );
  const rejectedRows = useMemo(
    () => eligibleRows.filter((row) => row.status === "Rejected"),
    [eligibleRows],
  );
  const completionRows = useMemo(
    () => eligibleRows.filter(canCompleteRow),
    [eligibleRows],
  );
  const selectedCompletionRows = useMemo(
    () => completionRows.filter((row) => rowForms[row.id]?.selectedForCompletion),
    [completionRows, rowForms],
  );
  const showCompletionSelection = !isAdminLike && completionRows.length > 0;
  const paymentRows = useMemo(
    () => eligibleRows.filter(canRequestPaymentRow),
    [eligibleRows],
  );
  const selectedPaymentRows = useMemo(
    () => paymentRows.filter((row) => rowForms[row.id]?.selectedForPayment),
    [paymentRows, rowForms],
  );
  const adminReviewRows = useMemo(
    () => eligibleRows.filter((row) => [
      "Serial Pending Verification",
      "Completion Pending Approval",
      "Installation Completed",
      "Payment Pending",
      "Service Team Review",
    ].includes(row.status)),
    [eligibleRows],
  );
  const bulkIdsQuery = useMemo(
    () => eligibleRows.map((row) => row.id).join(","),
    [eligibleRows],
  );
  const paymentTotal = selectedPaymentRows.reduce((total, row) => {
    const value = Number(rowForms[row.id]?.payment_amount || 0);
    return total + (Number.isFinite(value) ? value : 0);
  }, 0);

  function updateRowForm(rowId, patch) {
    setRowForms((current) => ({
      ...current,
      [rowId]: {
        ...current[rowId],
        ...patch,
      },
    }));
  }

  async function startAllVisits() {
    if (!assignedRows.length) return;
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const results = await Promise.allSettled(
        assignedRows.map(async (row) => {
          const body = new FormData();
          body.append("new_status", "In Progress");
          await installationsApi.updateStatus(row.id, body);
        }),
      );
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed > 0) setErr(`${failed} of ${assignedRows.length} visit(s) could not be started.`);
      setMsg(`Engineer visit started for ${assignedRows.length - failed} unit(s).`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to start visits");
    } finally {
      setBusy(false);
    }
  }

  async function resumeAllRejected() {
    if (!rejectedRows.length) return;
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const results = await Promise.allSettled(
        rejectedRows.map((row) => installationsApi.resumeWorkflow(row.id)),
      );
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed > 0) setErr(`${failed} of ${rejectedRows.length} unit(s) could not be resumed.`);
      setMsg(`Resumed ${rejectedRows.length - failed} unit(s). Upload proof and resubmit completion.`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to resume installations");
    } finally {
      setBusy(false);
    }
  }

  async function completeSelectedRows() {
    if (!selectedCompletionRows.length) return;
    const missingProofRows = selectedCompletionRows.filter((row) => {
      const form = rowForms[row.id] || {};
      return !form.proof_document || (rowNeedsSecondProof(row) && !form.proof_document_serial_2);
    });
    if (missingProofRows.length) {
      setErr("Upload required proof documents for each selected installation before completing.");
      return;
    }
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const results = await Promise.allSettled(
        selectedCompletionRows.map(async (row) => {
          const form = rowForms[row.id] || {};
          if (row.status === "Rejected") {
            await installationsApi.resumeWorkflow(row.id);
          }
          const body = new FormData();
          body.append("installation_date", form.installation_date || todayInputValue());
          body.append("work_report", form.work_report || "");
          body.append("proof_document", form.proof_document);
          if (form.proof_document_serial_2) {
            body.append("proof_document_serial_2", form.proof_document_serial_2);
          }
          await installationsApi.completeInstallation(row.id, body);
        }),
      );
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed > 0) setErr(`${failed} of ${selectedCompletionRows.length} unit(s) could not be completed.`);
      setMsg(`Installation completion submitted for ${selectedCompletionRows.length - failed} unit(s).`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to complete installations");
    } finally {
      setBusy(false);
    }
  }

  async function sendRowToServiceReview(row) {
    const observation = (rowForms[row.id]?.observation || "").trim();
    if (!observation) {
      setErr(`Observation is required for request #${row.id}.`);
      return;
    }
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const body = new FormData();
      body.append("observation", observation);
      await installationsApi.sendToServiceReview(row.id, body);
      setMsg(`Request #${row.id} sent to Service Role for review.`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to send request to Service Role");
    } finally {
      setBusy(false);
    }
  }

  async function requestBulkPayment() {
    if (!selectedPaymentRows.length) return;
    const invalidRows = selectedPaymentRows.filter((row) => {
      const amount = Number(rowForms[row.id]?.payment_amount);
      return rowForms[row.id]?.payment_amount === "" || !Number.isFinite(amount) || amount < 0;
    });
    if (invalidRows.length) {
      setErr("Enter a valid payment amount for each selected installation.");
      return;
    }
    if (paymentForm.payment_type === "UPI" && !paymentForm.qr_code) {
      setErr("Upload a UPI QR code before raising this bulk payment request.");
      return;
    }
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const amounts = {};
      selectedPaymentRows.forEach((row) => {
        amounts[row.id] = Number(rowForms[row.id]?.payment_amount || 0);
      });
      const body = new FormData();
      body.append("installation_ids", selectedPaymentRows.map((row) => row.id).join(","));
      body.append("payment_amounts_json", JSON.stringify(amounts));
      body.append("payment_type", paymentForm.payment_type);
      if (paymentForm.work_report) body.append("work_report", paymentForm.work_report);
      if (paymentForm.qr_code) body.append("qr_code", paymentForm.qr_code);
      await installationsApi.requestBulkPayment(body);
      setMsg(`Bulk payment request raised for ${selectedPaymentRows.length} installation(s). Total: ${paymentTotal.toFixed(2)}.`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to raise bulk payment request");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        {isAdminLike
          ? "Review each request by serial number and status. Open a unit workflow for approval details when needed."
          : "Complete selected installation requests together while keeping proof, payment, observation, and history per serial."}
      </p>

      <div className="overflow-x-auto rounded-md border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              {showCompletionSelection && <th className="w-12 px-2 py-2">Complete</th>}
              <th className="px-3 py-2">Request</th>
              <th className="px-3 py-2">Serial 1</th>
              <th className="px-3 py-2">Serial 2</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Proof of installation</th>
              <th className="px-3 py-2">Admin approval</th>
              {!isAdminLike && <th className="px-3 py-2">Observation / Remark</th>}
              <th className="w-16 px-2 py-2">Payment</th>
              <th className="px-3 py-2 text-right">Workflow</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {eligibleRows.map((row) => {
              const form = rowForms[row.id] || defaultRowForm(row);
              const completeReady = canCompleteRow(row);
              return (
                <tr key={row.id} className="align-top hover:bg-slate-50">
                  {showCompletionSelection && (
                    <td className="px-2 py-2">
                      <input
                        type="checkbox"
                        checked={Boolean(form.selectedForCompletion)}
                        onChange={(e) => updateRowForm(row.id, { selectedForCompletion: e.target.checked })}
                        disabled={!completeReady}
                        className="h-4 w-4 disabled:opacity-40"
                      />
                    </td>
                  )}
                  <td className="px-3 py-2 font-medium">#{row.id}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.serial_no || "-"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.serial_no_2 || row.engineer_entered_serial_no_2 || "-"}</td>
                  <td className="px-3 py-2">
                    <StatusBadge value={row.status} />
                    <div className="mt-1 text-xs text-slate-500">{adminBulkReviewActionLabel(row.status)}</div>
                    {shouldShowAdminRemark(row) && (
                      <div className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800">
                        <span className="font-semibold">Admin remark:</span>{" "}
                        <span className="whitespace-pre-wrap">{row.admin_approval_remark}</span>
                      </div>
                    )}
                  </td>
                  <td className="min-w-[220px] px-3 py-2">
                    {isAdminLike || !completeReady ? (
                      <span className="text-xs text-slate-700">{completionProofSummary(row)}</span>
                    ) : (
                      <div className="space-y-2">
                        <input
                          type="date"
                          value={form.installation_date}
                          onChange={(e) => updateRowForm(row.id, { installation_date: e.target.value })}
                          className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs"
                        />
                        <label className="block text-xs text-slate-700">
                          <span className="mb-1 block font-medium">Serial 1 proof required</span>
                          <input
                            type="file"
                            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                            required
                            onChange={(e) => updateRowForm(row.id, { proof_document: e.target.files?.[0] || null })}
                            className="block w-full text-xs"
                          />
                        </label>
                        {rowNeedsSecondProof(row) && (
                          <label className="block text-xs text-slate-700">
                            <span className="mb-1 block font-medium">Serial 2 proof required</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                              required
                              title="Proof for Serial 2"
                              onChange={(e) => updateRowForm(row.id, { proof_document_serial_2: e.target.files?.[0] || null })}
                              className="block w-full text-xs"
                            />
                          </label>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="min-w-[220px] px-3 py-2 text-xs text-slate-700">
                    <div className="font-medium text-slate-800">{completionApprovalStatus(row)}</div>
                    {row.admin_approved_at && (
                      <div className="mt-1 text-slate-500">
                        Approved {new Date(row.admin_approved_at).toLocaleDateString()}
                      </div>
                    )}
                    {(row.admin_approval_remark || "").trim() ? (
                      <div className="mt-2 rounded-md border border-slate-200 bg-white px-2 py-1">
                        <span className="font-semibold">Admin remark:</span>{" "}
                        <span className="whitespace-pre-wrap">{row.admin_approval_remark}</span>
                      </div>
                    ) : (
                      <div className="mt-1 text-slate-400">No admin remark</div>
                    )}
                  </td>
                  {!isAdminLike && (
                    <td className="min-w-[260px] px-3 py-2">
                      {shouldShowAdminRemark(row) && (
                        <div className="mb-2 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800">
                          <span className="font-semibold">Admin remark:</span>{" "}
                          <span className="whitespace-pre-wrap">{row.admin_approval_remark}</span>
                        </div>
                      )}
                      <textarea
                        rows={3}
                        value={form.observation}
                        onChange={(e) => updateRowForm(row.id, { observation: e.target.value, work_report: e.target.value })}
                        className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs"
                        placeholder="Observation, issue, or completion remark"
                      />
                      <button
                        type="button"
                        onClick={() => sendRowToServiceReview(row)}
                        disabled={busy || !form.observation.trim()}
                        className="mt-2 rounded-md bg-violet-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-violet-800 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:bg-violet-200 disabled:text-violet-500 disabled:shadow-none"
                      >
                        Send to Service Role
                      </button>
                    </td>
                  )}
                  <td className="w-16 px-2 py-2">
                    {canRequestPaymentRow(row) && !isAdminLike ? (
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs text-slate-700">
                          <input
                            type="checkbox"
                            checked={Boolean(form.selectedForPayment)}
                            onChange={(e) => updateRowForm(row.id, { selectedForPayment: e.target.checked })}
                            className="h-4 w-4"
                          />
                          Include
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={form.payment_amount}
                          onChange={(e) => updateRowForm(row.id, { payment_amount: e.target.value })}
                          className="w-14 rounded-md border border-slate-300 px-1 py-1 text-xs"
                          placeholder="Amount"
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-slate-600">
                        {row.payment_amount_requested != null ? row.payment_amount_requested : "-"}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      to={`/installations/${row.id}?edit=1${bulkIdsQuery ? `&bulkIds=${bulkIdsQuery}` : ""}`}
                      className="font-medium text-brand-600 hover:text-brand-700"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {isAdminLike && adminReviewRows.length > 0 && (
        <div className="rounded-md border border-sky-200 bg-sky-50 p-4">
          <div className="text-sm font-medium text-sky-900">Admin review summary</div>
          <p className="mt-1 text-xs text-sky-800">
            {adminReviewRows.length} unit(s) need admin or service action. Use Open on each row for detailed approval.
          </p>
        </div>
      )}

      {!isAdminLike && rejectedRows.length > 0 && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4">
          <div className="text-sm font-medium text-rose-900">Admin returned for correction</div>
          <p className="mt-1 text-xs text-rose-800">
            {rejectedRows.length} unit(s) were rejected or returned. Resume them, fix the issue, then resubmit proof.
          </p>
          <button
            type="button"
            onClick={resumeAllRejected}
            disabled={busy}
            className="mt-3 rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            Resume {rejectedRows.length} unit(s)
          </button>
        </div>
      )}

      {!isAdminLike && assignedRows.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
          <div className="text-sm font-medium text-amber-900">Step 1 - Start engineer visit</div>
          <p className="mt-1 text-xs text-amber-800">
            {assignedRows.length} unit(s) are still Assigned and can be moved to In Progress together.
          </p>
          <button
            type="button"
            onClick={startAllVisits}
            disabled={busy}
            className="mt-3 rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            Start visit for {assignedRows.length} unit(s)
          </button>
        </div>
      )}

      {!isAdminLike && completionRows.length > 0 && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-sm font-medium text-emerald-900">Step 2 - Submit selected completions</div>
          <p className="mt-1 text-xs text-emerald-800">
            Submit proof and remarks only for the checked rows. Rows sent to Service Role remain separate and do not block the rest.
          </p>
          <button
            type="button"
            onClick={completeSelectedRows}
            disabled={busy || selectedCompletionRows.length === 0}
            className="mt-3 rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Submit completion for {selectedCompletionRows.length} selected unit(s)
          </button>
        </div>
      )}

      {!isAdminLike && paymentRows.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
          <div className="text-sm font-medium text-amber-900">Step 3 - Raise bulk payment request</div>
          <p className="mt-1 text-xs text-amber-800">
            Select installations above, enter the amount per serial, then submit one bulk payment request.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Payment type</label>
              <select
                value={paymentForm.payment_type}
                onChange={(e) => setPaymentForm((current) => ({ ...current, payment_type: e.target.value }))}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {PAYMENT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Final total</label>
              <div className="mt-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900">
                {paymentTotal.toFixed(2)}
              </div>
            </div>
            {paymentForm.payment_type === "UPI" && (
              <div>
                <label className="text-xs uppercase tracking-wide text-slate-500">
                  UPI QR code <span className="text-rose-600">*</span>
                </label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  required
                  onChange={(e) => setPaymentForm((current) => ({ ...current, qr_code: e.target.files?.[0] || null }))}
                  className="mt-1 block w-full text-sm"
                />
              </div>
            )}
            <div className="md:col-span-3">
              <label className="text-xs uppercase tracking-wide text-slate-500">Payment note</label>
              <textarea
                rows={2}
                value={paymentForm.work_report}
                onChange={(e) => setPaymentForm((current) => ({ ...current, work_report: e.target.value }))}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Optional payment request note"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={requestBulkPayment}
            disabled={busy || selectedPaymentRows.length === 0}
            className="mt-3 rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Raise payment for {selectedPaymentRows.length} selected installation(s)
          </button>
        </div>
      )}

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{msg}</div>}

      {showClose && (
        <div className="flex justify-end">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Close
          </button>
        </div>
      )}
    </div>
  );
}
