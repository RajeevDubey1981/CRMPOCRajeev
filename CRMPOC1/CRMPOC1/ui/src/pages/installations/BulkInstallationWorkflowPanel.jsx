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
  return "—";
}

export default function BulkInstallationWorkflowPanel({ rows, onSaved, showClose, onClose }) {
  const { user } = useAuth();
  const isAdminLike = isOperationsAdminRole(user?.role);
  const [workflowRows, setWorkflowRows] = useState(rows);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [completeForm, setCompleteForm] = useState({
    installation_date: todayInputValue(),
    work_report: "",
    proof_document: null,
  });

  useEffect(() => {
    setWorkflowRows(rows);
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
    () => eligibleRows.filter((row) => ["In Progress", "Returned", "Rejected"].includes(row.status)),
    [eligibleRows],
  );
  const adminReviewRows = useMemo(
    () => eligibleRows.filter((row) => [
      "Serial Pending Verification",
      "Completion Pending Approval",
      "Installation Completed",
      "Payment Pending",
    ].includes(row.status)),
    [eligibleRows],
  );
  const bulkIdsQuery = useMemo(
    () => eligibleRows.map((row) => row.id).join(","),
    [eligibleRows],
  );

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
      if (failed > 0) {
        setErr(`${failed} of ${assignedRows.length} visit(s) could not be started.`);
      }
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
      if (failed > 0) {
        setErr(`${failed} of ${rejectedRows.length} unit(s) could not be resumed.`);
      }
      setMsg(`Resumed ${rejectedRows.length - failed} unit(s). Upload new proof and resubmit completion.`);
      setWorkflowRows((current) => current.map((row) => (
        row.status === "Rejected" ? { ...row, status: "Returned" } : row
      )));
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to resume installations");
    } finally {
      setBusy(false);
    }
  }

  async function completeAll() {
    if (!completionRows.length) return;
    if (!completeForm.proof_document) {
      setErr("Installation proof is required for bulk completion.");
      return;
    }
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const results = await Promise.allSettled(
        completionRows.map(async (row) => {
          if (row.status === "Rejected") {
            await installationsApi.resumeWorkflow(row.id);
          }
          const body = new FormData();
          body.append("installation_date", completeForm.installation_date);
          body.append("work_report", completeForm.work_report || "");
          body.append("proof_document", completeForm.proof_document);
          await installationsApi.completeInstallation(row.id, body);
        }),
      );
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed > 0) {
        setErr(`${failed} of ${completionRows.length} unit(s) could not be completed.`);
      }
      setMsg(`Installation resubmitted for ${completionRows.length - failed} unit(s). Waiting for admin approval.`);
      onSaved?.();
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Failed to complete installations");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        {isAdminLike
          ? "Review each request by serial number and status. Open the unit workflow to approve completion, payment, or serial verification."
          : "Process multiple vendor units from the same item code group — start visits, complete installations, or open each unit workflow."}
      </p>

      <div className="overflow-x-auto rounded-md border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Request</th>
              <th className="px-3 py-2">Serial 1</th>
              {isAdminLike && <th className="px-3 py-2">Serial 2</th>}
              <th className="px-3 py-2">Status</th>
              {isAdminLike && <th className="px-3 py-2">Billing</th>}
              {isAdminLike && <th className="px-3 py-2">Completion proof</th>}
              {isAdminLike && <th className="px-3 py-2">Engineer</th>}
              <th className="px-3 py-2">Next action</th>
              <th className="px-3 py-2 text-right">Workflow</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {eligibleRows.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium">#{row.id}</td>
                <td className="px-3 py-2 font-mono text-xs">{row.serial_no || "—"}</td>
                {isAdminLike && (
                  <td className="px-3 py-2 font-mono text-xs">
                    {row.serial_no_2 || row.engineer_entered_serial_no_2 || "—"}
                  </td>
                )}
                <td className="px-3 py-2">
                  <StatusBadge value={row.status} />
                </td>
                {isAdminLike && (
                  <td className="px-3 py-2">{row.admin_billing_type || "—"}</td>
                )}
                {isAdminLike && (
                  <td className="px-3 py-2 text-xs text-slate-700">{completionProofSummary(row)}</td>
                )}
                {isAdminLike && (
                  <td className="px-3 py-2 text-xs text-slate-700">{row.assigned_engineer_name || "—"}</td>
                )}
                <td className="px-3 py-2 text-xs text-slate-600">
                  {adminBulkReviewActionLabel(row.status)}
                </td>
                <td className="px-3 py-2 text-right">
                  <Link
                    to={`/installations/${row.id}?edit=1${bulkIdsQuery ? `&bulkIds=${bulkIdsQuery}` : ""}`}
                    className="font-medium text-brand-600 hover:text-brand-700"
                  >
                    Open workflow
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isAdminLike && adminReviewRows.length > 0 && (
        <div className="rounded-md border border-sky-200 bg-sky-50 p-4">
          <div className="text-sm font-medium text-sky-900">Admin review summary</div>
          <p className="mt-1 text-xs text-sky-800">
            {adminReviewRows.length} unit(s) need admin action (serial verify, completion approval, or payment approval).
            Check the serial numbers above, then use <strong>Open workflow</strong> on each row.
          </p>
          <ul className="mt-2 space-y-1 text-xs text-sky-900">
            {eligibleRows.map((row) => (
              <li key={row.id}>
                <span className="font-mono">#{row.id}</span>
                {" — "}
                <span className="font-mono">{row.serial_no || "no serial"}</span>
                {" — "}
                <span className="font-medium">{row.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isAdminLike && adminReviewRows.length > 0 && (
        <div className="rounded-md border border-sky-200 bg-sky-50 p-4">
          <div className="text-sm font-medium text-sky-900">In progress — open unit workflow</div>
          <p className="mt-1 text-xs text-sky-800">
            {adminReviewRows.length} unit(s) are waiting on verification, admin approval, or payment steps.
            Use <strong>Open workflow</strong> on each request above to review details.
          </p>
        </div>
      )}

      {!isAdminLike && rejectedRows.length > 0 && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4">
          <div className="text-sm font-medium text-rose-900">Admin returned for correction</div>
          <p className="mt-1 text-xs text-rose-800">
            {rejectedRows.length} unit(s) were rejected or returned by admin. Resume them, fix the issue, then resubmit installation proof below.
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
          <div className="text-sm font-medium text-amber-900">Step 1 — Start engineer visit</div>
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
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 space-y-3">
          <div>
            <div className="text-sm font-medium text-emerald-900">
              {rejectedRows.length > 0 ? "Resubmit installation" : "Step 2 — Complete installation"}
            </div>
            <p className="mt-1 text-xs text-emerald-800">
              {rejectedRows.length > 0
                ? `Fix and resubmit installation proof for ${completionRows.length} unit(s). Rejected units are resumed automatically before submission.`
                : `Apply the same installation date, work report, and proof to ${completionRows.length} unit(s).`}
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Installation date</label>
              <input
                type="date"
                value={completeForm.installation_date}
                onChange={(e) => setCompleteForm((current) => ({ ...current, installation_date: e.target.value }))}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">
                Installation proof <span className="text-rose-600">*</span>
              </label>
              <input
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                required
                onChange={(e) => {
                  setErr("");
                  setCompleteForm((current) => ({ ...current, proof_document: e.target.files?.[0] || null }));
                }}
                className="mt-1 block w-full text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs uppercase tracking-wide text-slate-500">Work report</label>
              <textarea
                rows={3}
                value={completeForm.work_report}
                onChange={(e) => setCompleteForm((current) => ({ ...current, work_report: e.target.value }))}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Summary applied to all selected units"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={completeAll}
            disabled={busy || !completeForm.proof_document}
            className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {rejectedRows.length > 0
              ? `Resubmit ${completionRows.length} unit(s)`
              : `Complete ${completionRows.length} unit(s)`}
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
