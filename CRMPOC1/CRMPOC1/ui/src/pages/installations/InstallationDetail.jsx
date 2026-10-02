import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { installationsApi } from "../../api/installations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole, isServiceTeamRole, isSystemAdminRole } from "../../utils/roles.js";
import { usesStructuredInstallationWorkflow, getInstallationWorkflowStepOptions, getCurrentInstallationWorkflowStep } from "../../utils/installationWorkflowSteps.js";
import InstallationStatusEdit from "./InstallationStatusEdit.jsx";
import InstallationCallCenterWorkflow from "./InstallationCallCenterWorkflow.jsx";
import { toDownloadUrl } from "../../utils/downloadUrl.js";

function fmt(value) {
  return value ? new Date(value).toLocaleString() : "-";
}

function fmtDate(value) {
  return value ? new Date(value).toLocaleDateString() : "-";
}

function Field({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>
        {value ?? <span className="text-slate-400">-</span>}
      </div>
    </div>
  );
}

function FileLinkField({ label, path, full = false }) {
  if (!path) return null;
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <a
        href={toDownloadUrl(path)}
        download
        target="_blank"
        rel="noreferrer"
        className="mt-0.5 inline-block text-sm font-medium text-sky-700 underline"
      >
        View / download
      </a>
    </div>
  );
}

export default function InstallationDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const wantsEdit = searchParams.get("edit") === "1";
  const bulkIds = (searchParams.get("bulkIds") || "").trim();
  const bulkWorkflowHref = bulkIds ? `/installations/bulk-workflow?ids=${bulkIds}` : null;
  const workflowRef = useRef(null);
  const { user } = useAuth();
  const role = (user?.role || "").toLowerCase();
  const isAdminLike = isOperationsAdminRole(role);
  const isPaymentAdmin = isSystemAdminRole(role);
  const isServiceTeam = isServiceTeamRole(role);
  const isEngineer = role === "engineer";
  const [installation, setInstallation] = useState(null);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(wantsEdit);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [workflowStep, setWorkflowStep] = useState("");
  const [workflowRemarks, setWorkflowRemarks] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  async function load() {
    try {
      setInstallation(await installationsApi.get(id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load");
    }
  }

  useEffect(() => {
    load();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!installation || !wantsEdit) return;
    workflowRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [installation, wantsEdit]);

  async function rejectInstallation() {
    const returnToEngineer = usesStructuredWorkflow && installation.assigned_engineer;
    const message = returnToEngineer
      ? `Return installation request #${installation.id} to the engineer for correction?`
      : `Reject installation request #${installation.id}?`;
    if (!window.confirm(message)) return;
    setBusy(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("new_status", returnToEngineer ? "Returned" : "Rejected");
      await installationsApi.updateStatus(id, fd);
      await load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to update installation request");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!installation) return;
    setWorkflowStep(String(getCurrentInstallationWorkflowStep(installation)));
  }, [installation]);

  async function updateWorkflowStep() {
    const targetStep = Number(workflowStep);
    if (!targetStep) return;
    setBusy(true);
    setErr("");
    setSuccessMsg("");
    try {
      await installationsApi.resetWorkflow(id, {
        target_step: targetStep,
        remarks: workflowRemarks.trim() || undefined,
      });
      setSuccessMsg("Workflow step updated.");
      setWorkflowRemarks("");
      await load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to update installation workflow step");
    } finally {
      setBusy(false);
    }
  }

  async function resetWorkflow() {
    if (!window.confirm("Reset the entire installation workflow? This clears order link, engineer assignment, serials, and payment progress.")) return;
    setBusy(true);
    setErr("");
    setSuccessMsg("");
    try {
      await installationsApi.resetWorkflow(id, { target_step: 1 });
      setSuccessMsg("Workflow reset to step 1.");
      await load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to reset installation workflow");
    } finally {
      setBusy(false);
    }
  }

  async function deleteInstallation() {
    setBusy(true);
    setErr("");
    try {
      await installationsApi.remove(id);
      navigate("/installations");
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to delete installation request");
      setConfirmDelete(false);
    } finally {
      setBusy(false);
    }
  }

  if (err && !installation) return <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>;
  if (!installation) return <div className="text-slate-500">Loading...</div>;

  const isCallcenter = (installation.source || "").toLowerCase() === "callcenter";
  const usesStructuredWorkflow = usesStructuredInstallationWorkflow(installation);
  const canEditWorkflow = (isAdminLike || isServiceTeam) && usesStructuredWorkflow;
  const workflowStepOptions = canEditWorkflow ? getInstallationWorkflowStepOptions(installation) : [];
  const showInlineStatusEdit = (editing || wantsEdit)
    && !usesStructuredWorkflow
    && (!isCallcenter || isAdminLike);
  const canEdit = !(isEngineer && installation.status === "Completed");

  function handleEditClick() {
    if (usesStructuredWorkflow && !isAdminLike) {
      workflowRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      setEditing(true);
      return;
    }
    if (isCallcenter && !isAdminLike) {
      workflowRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    setEditing(true);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <Link to="/installations" className="text-brand-600 hover:underline">Back to installations</Link>
            {bulkWorkflowHref && (
              <>
                <span className="text-slate-300">|</span>
                <Link to={bulkWorkflowHref} className="font-medium text-brand-600 hover:underline">
                  Back to bulk workflow
                </Link>
              </>
            )}
          </div>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold text-slate-800">
            Installation Request #{installation.id}
            <StatusBadge value={installation.status} />
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {canEdit && (
            <button
              onClick={handleEditClick}
              disabled={busy}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {usesStructuredWorkflow && !isAdminLike ? "Go to workflow" : isCallcenter ? "Go to workflow" : "Edit"}
            </button>
          )}
          {isAdminLike && installation.status !== "Rejected" && installation.status !== "Returned" && (
            <button
              onClick={rejectInstallation}
              disabled={busy}
              className="rounded-md border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            >
              {usesStructuredWorkflow && installation.assigned_engineer ? "Return to engineer" : "Reject"}
            </button>
          )}
          {isAdminLike && (
            <button
              onClick={() => setConfirmDelete(true)}
              disabled={busy}
              className="rounded-md border border-rose-400 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {successMsg && <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMsg}</div>}

      {canEditWorkflow && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <div className="text-sm font-semibold text-amber-900">Admin workflow control</div>
          <p className="mt-1 text-xs text-amber-800">
            Roll this installation back to an earlier workflow step. Later-step data is cleared.
            Vendor order installs keep the linked order and serial numbers when rolling back to step 1 or 4.
          </p>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_2fr_auto]">
            <select
              value={workflowStep}
              onChange={(e) => setWorkflowStep(e.target.value)}
              className="rounded-md border border-amber-300 bg-white px-3 py-2 text-sm"
            >
              {workflowStepOptions.map((option) => (
                <option key={option.step} value={option.step}>
                  {option.label}
                </option>
              ))}
            </select>
            <input
              value={workflowRemarks}
              onChange={(e) => setWorkflowRemarks(e.target.value)}
              placeholder="Reason for changing workflow step"
              className="rounded-md border border-amber-300 bg-white px-3 py-2 text-sm"
            />
            <button
              type="button"
              disabled={busy || Number(workflowStep) === getCurrentInstallationWorkflowStep(installation)}
              onClick={updateWorkflowStep}
              className="rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Update step
            </button>
          </div>
        </section>
      )}

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Request & Customer Details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Source" value={installation.source || "vendor"} />
          <Field label="Order No" value={installation.order_no} mono />
          <Field label="Vendor" value={installation.vendor_name} />
          {installation.complaint_id && (
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Linked complaint</div>
              <div className="mt-0.5 text-sm">
                <Link
                  to={`/complaints/${installation.complaint_id}`}
                  className="font-mono text-brand-600 underline hover:text-brand-700"
                >
                  {installation.complaint_no || `#${installation.complaint_id}`}
                </Link>
              </div>
            </div>
          )}
          <Field label="Customer Name" value={installation.customer_name} />
          <Field label="Contact Number" value={installation.contact_number} mono />
          <Field label="Product" value={installation.product_name} />
          <Field label="Serial 1" value={installation.serial_no} mono />
          <Field label="Serial 2" value={installation.serial_no_2} mono />
          <Field label="Request Date" value={fmtDate(installation.request_date)} />
          <Field label="Installation Date" value={fmtDate(installation.installation_date)} />
          <Field label="Status" value={installation.status} />
          <Field label="Assigned Engineer" value={installation.assigned_engineer_name} />
          <Field label="Address" value={installation.address} full />
          {installation.work_report && (
            <Field label="Work Report" value={installation.work_report} full />
          )}
          <FileLinkField label="Installation Proof" path={installation.work_report_file_path} full />
          <Field label="Payment Amount Requested" value={installation.payment_amount_requested} />
          <Field label="Payment Type Requested" value={installation.payment_type_requested} />
          <Field label="Payment QR Code" value={installation.payment_qr_code_path} mono full />
          <FileLinkField label="Payment Proof" path={installation.payment_proof_file_path} full />
          <Field label="Payment Requested At" value={fmt(installation.payment_requested_at)} />
          <Field label="Payment Amount Paid" value={installation.payment_amount_paid} />
          <Field label="Payment Type Paid" value={installation.payment_type_paid} />
          <Field label="Payment Recorded By" value={installation.payment_recorded_by_name} />
          <Field label="Payment Recorded At" value={fmt(installation.payment_recorded_at)} />
          <Field label="Settlement Approved By" value={installation.settlement_approved_by_name} />
          <Field label="Created At" value={fmt(installation.created_at)} />
          <Field label="Updated At" value={fmt(installation.updated_at)} />
        </div>
        {installation.complaint_id && (
          <div className="mt-4">
            <Link
              to={`/complaints/${installation.complaint_id}`}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Open complaint {installation.complaint_no || `#${installation.complaint_id}`}
            </Link>
          </div>
        )}
      </section>

      <div ref={workflowRef}>
        <InstallationCallCenterWorkflow
          installation={installation}
          isAdminLike={isAdminLike}
          isPaymentAdmin={isPaymentAdmin}
          isServiceTeam={isServiceTeam}
          isEngineer={isEngineer}
          userId={user?.id}
          onUpdated={load}
          onError={setErr}
          onBusy={setBusy}
          onResetWorkflow={resetWorkflow}
        />

        {showInlineStatusEdit && (
          <section className="mt-4 rounded-lg border border-brand-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-medium text-slate-700">
              {isEngineer ? "Update installation progress" : "Edit installation"}
            </h2>
            <InstallationStatusEdit
              inline
              installation={installation}
              onClose={() => setEditing(false)}
              onSaved={() => {
                load();
              }}
            />
          </section>
        )}
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete installation request?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will delete installation request <span className="font-medium">#{installation.id}</span> for {installation.customer_name}.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setConfirmDelete(false)} className="rounded border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button onClick={deleteInstallation} disabled={busy} className="rounded bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50">Delete</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
