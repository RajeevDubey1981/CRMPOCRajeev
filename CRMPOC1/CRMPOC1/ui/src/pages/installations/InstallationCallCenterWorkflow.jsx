import { useEffect, useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { formatApiError } from "../../utils/apiError.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";
import { canAssignCallcenterEngineer, getInstallationWorkflowStepState, installationSerialReady, isAssignedToUser, isVendorAssignedInstallation, isVendorInitiatedInstallation } from "../../utils/installationWorkflowSteps.js";
import InstallationEngineerSerialWorkflow from "../../components/installations/InstallationEngineerSerialWorkflow.jsx";
import InstallationPostVerifyWorkflow from "../../components/installations/InstallationPostVerifyWorkflow.jsx";
import WorkflowStepSection from "../../components/installations/WorkflowStepSection.jsx";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";
import EngineerSelect from "../../components/EngineerSelect.jsx";
import { isMissingItemCode } from "../../utils/installationItemCode.js";

function Field({ label, value, mono = false }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>{value || "—"}</div>
    </div>
  );
}

function CustomerDocumentList({ documents }) {
  if (!documents.length) return null;
  return (
    <div>
      <div className="text-sm font-medium text-slate-800">Customer uploaded documents</div>
      <ul className="mt-2 space-y-2 text-xs text-slate-700">
        {documents.map((doc) => (
          <li key={doc.id} className="rounded border border-slate-200 bg-white px-3 py-2">
            <div className="font-medium text-slate-800">{doc.document_type}</div>
            <div className="text-slate-500">
              {doc.uploaded_by_type}
              {doc.uploaded_at ? ` • ${new Date(doc.uploaded_at).toLocaleString()}` : ""}
            </div>
            <a
              href={toDownloadUrl(doc.file_path)}
              download
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-sky-700 underline"
            >
              View / download document
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function InstallationCallCenterWorkflow({
  installation,
  isAdminLike,
  isPaymentAdmin = false,
  isServiceTeam = false,
  isEngineer,
  userId,
  onUpdated,
  onError,
  onBusy,
  onResetWorkflow,
}) {
  const source = (installation.source || "vendor").toLowerCase();
  const isCallcenter = source === "callcenter";
  const isVendorInitiated = isVendorInitiatedInstallation(installation);
  const isVendorAssigned = isVendorAssignedInstallation(installation);
  const canViewCustomerDocuments = isAdminLike || isServiceTeam;
  const [orderSearch, setOrderSearch] = useState("");
  const [orderOptions, setOrderOptions] = useState([]);
  const [orderSearchLoading, setOrderSearchLoading] = useState(false);
  const [orderSearchAttempted, setOrderSearchAttempted] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [history, setHistory] = useState([]);
  const [engineerOptions, setEngineerOptions] = useState([]);
  const [selectedEngineerId, setSelectedEngineerId] = useState("");

  useEffect(() => {
    if (!isCallcenter) return;
    installationsApi.documents(installation.id).then(setDocuments).catch(() => setDocuments([]));
    installationsApi.history(installation.id).then(setHistory).catch(() => setHistory([]));
  }, [installation.id, installation.status, isCallcenter]);

  useEffect(() => {
    if (!isCallcenter || !isAdminLike) return undefined;
    const query = orderSearch.trim();
    if (query.length < 2) {
      setOrderOptions([]);
      setOrderSearchLoading(false);
      setOrderSearchAttempted(false);
      return undefined;
    }
    setOrderSearchLoading(true);
    const timer = window.setTimeout(() => {
      installationsApi.searchOrders({ mobile: query, name: query, order_no: query })
        .then((rows) => {
          setOrderOptions(rows);
          setOrderSearchAttempted(true);
        })
        .catch(() => {
          setOrderOptions([]);
          setOrderSearchAttempted(true);
        })
        .finally(() => setOrderSearchLoading(false));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [orderSearch, isCallcenter, isAdminLike]);

  useEffect(() => {
    if (!isCallcenter || !isAdminLike || !installation.order_verified_at) return;
    installationsApi.engineerAssignmentOptions(installation.address, installation)
      .then(setEngineerOptions)
      .catch(() => setEngineerOptions([]));
  }, [isCallcenter, isAdminLike, installation.order_verified_at, installation.id, installation.address, installation.pincode, installation.state, installation.district]);

  useEffect(() => {
    if (installation.assigned_engineer) {
      setSelectedEngineerId(String(installation.assigned_engineer));
    }
  }, [installation.assigned_engineer]);

  const workflowSteps = getInstallationWorkflowStepState(installation);
  const canAssignEngineer = canAssignCallcenterEngineer(installation);
  const isReassign = Boolean(installation.assigned_engineer);
  const showSerialWorkflow = isCallcenter
    && installation.order_verified_at
    && installation.assigned_engineer
    && !installation.serial_verified_at;

  if (isEngineer && !isAdminLike) {
    if (!isCallcenter && !isVendorAssigned) return null;

    const isAssignedEngineer = isAssignedToUser(installation, userId);
    const serialReady = installationSerialReady(installation);

    async function run(action) {
      onBusy?.(true);
      onError?.("");
      try {
        await action();
        onUpdated?.();
      } catch (error) {
        onError?.(formatApiError(error, "Action failed"));
      } finally {
        onBusy?.(false);
      }
    }

    async function startEngineerVisit() {
      const body = new FormData();
      body.append("new_status", "In Progress");
      await installationsApi.updateStatus(installation.id, body);
    }

    return (
      <section className="space-y-4 rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <div>
          <h2 className="text-sm font-medium text-amber-900">Your installation tasks</h2>
          <p className="mt-1 text-xs text-amber-800">
            {isVendorAssigned
              ? "Vendor order installation — complete site visit through admin payment approval."
              : "Complete the steps assigned to you for this installation request."}
          </p>
        </div>

        {isVendorAssigned && (
          <div className="rounded-md border border-sky-200 bg-white px-3 py-2 text-sm text-sky-900">
            Order <strong>{installation.order_no || "—"}</strong> · Serial{" "}
            <strong className="font-mono">{installation.serial_no || "—"}</strong>
            {installation.serial_no_2 ? ` / ${installation.serial_no_2}` : ""}
          </div>
        )}

        {!installation.assigned_engineer && (
          <p className="text-sm text-slate-700">Waiting for admin to assign an engineer.</p>
        )}
        {installation.assigned_engineer && installation.assigned_engineer !== userId && (
          <p className="text-sm text-slate-700">
            This request is assigned to {installation.assigned_engineer_name || "another engineer"}.
          </p>
        )}
        {isCallcenter && documents.length > 0 && installation.assigned_engineer === userId && (
          <CustomerDocumentList documents={documents} />
        )}
        {isCallcenter && installation.assigned_engineer === userId && !installation.order_verified_at && (
          <p className="text-sm text-slate-700">Waiting for admin to verify the linked order.</p>
        )}
        {isCallcenter && installation.assigned_engineer === userId && installation.order_verified_at && !isMissingItemCode(installation.item_code) && !installation.serial_verified_at && (
          <p className="text-sm text-slate-700">
            Use the update form below to record installation progress and completion details.
          </p>
        )}
        {isVendorAssigned && isAssignedEngineer && installation.status === "Assigned" && serialReady && (
          <button
            type="button"
            onClick={() => run(startEngineerVisit)}
            className="rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            Start engineer visit
          </button>
        )}
        {!serialReady && isAssignedEngineer && isVendorAssigned && (
          <p className="text-sm text-amber-800">Waiting for serial details on this unit. Refresh the page or contact admin.</p>
        )}
        {showSerialWorkflow && installation.assigned_engineer === userId && (
          <InstallationEngineerSerialWorkflow
            installationId={installation.id}
            installationStatus={installation.status}
            assignedEngineerId={installation.assigned_engineer}
            serialVerifiedAt={installation.serial_verified_at}
            engineerSiteRemarks={installation.engineer_site_remarks}
            isEngineer={isEngineer}
            isAdminLike={false}
            isPaymentAdmin={false}
            userId={userId}
            showAdminVerify={false}
            workflowSteps={workflowSteps}
            onUpdated={onUpdated}
            onError={onError}
            onBusy={onBusy}
          />
        )}
        {serialReady && isAssignedEngineer && (
          <InstallationPostVerifyWorkflow
            installation={installation}
            isEngineer={isEngineer}
            isAdminLike={false}
            isPaymentAdmin={false}
            userId={userId}
            workflowSteps={workflowSteps}
            onUpdated={onUpdated}
            onError={onError}
            onBusy={onBusy}
          />
        )}
        {!isEngineer && history.length > 0 && (
          <div>
            <div className="text-sm font-medium text-slate-700">Workflow history</div>
            <ol className="mt-2 max-h-56 space-y-2 overflow-auto text-xs text-slate-700">
              {history.map((entry) => (
                <li key={entry.id} className="rounded border border-slate-200 bg-white p-2">
                  <div className="font-medium">{entry.action}</div>
                  <div>{entry.old_status} → {entry.new_status}</div>
                  <div className="text-slate-500">{entry.performed_by_name || entry.performed_role} · {new Date(entry.created_at).toLocaleString()}</div>
                  {entry.remarks && <div className="mt-1">{entry.remarks}</div>}
                </li>
              ))}
            </ol>
          </div>
        )}
      </section>
    );
  }

  if (!isCallcenter && isVendorInitiated && (isAdminLike || isServiceTeam) && !isVendorAssigned) {
    return (
      <section className="space-y-4 rounded-lg border border-violet-200 bg-violet-50 p-6 shadow-sm">
        <div>
          <h2 className="text-sm font-medium text-violet-900">Vendor order installation</h2>
          <p className="mt-1 text-xs text-violet-800">
            Submitted from order {installation.order_no || `#${installation.order_id || "—"}`}
            {installation.serial_no ? ` · Serial ${installation.serial_no}` : ""}.
            Assign an engineer from the order line item or installation list to continue.
          </p>
        </div>
      </section>
    );
  }

  if (!isCallcenter && isVendorAssigned && (isAdminLike || isServiceTeam)) {
    const serialReady = installationSerialReady(installation);
    if (!serialReady) return null;

    return (
      <section className="space-y-4 rounded-lg border border-violet-200 bg-violet-50 p-6 shadow-sm">
        <div>
          <h2 className="text-sm font-medium text-violet-900">Admin installation review</h2>
          <p className="mt-1 text-xs text-violet-800">
            Vendor order installation — approve engineer completion, then payment.
          </p>
        </div>
        <InstallationPostVerifyWorkflow
          installation={installation}
          isEngineer={false}
          isAdminLike={isAdminLike}
          isPaymentAdmin={isPaymentAdmin}
          userId={userId}
          workflowSteps={workflowSteps}
          onUpdated={onUpdated}
          onError={onError}
          onBusy={onBusy}
        />
      </section>
    );
  }

  if (!isCallcenter) return null;

  async function run(action) {
    onBusy?.(true);
    onError?.("");
    try {
      await action();
      onUpdated?.();
    } catch (error) {
      onError?.(formatApiError(error, "Action failed"));
    } finally {
      onBusy?.(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

  return (
    <section className="space-y-4 rounded-lg border border-sky-200 bg-sky-50 p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-sky-900">Call Center Installation Workflow</h2>
          <p className="mt-1 text-xs text-sky-800">
            Source: Call Center · Order can be linked without serial number initially.
          </p>
        </div>
        {isAdminLike && onResetWorkflow && (
          <button
            type="button"
            onClick={() => {
              if (window.confirm("Reset the entire installation workflow to step 1?")) {
                onResetWorkflow();
              }
            }}
            className="rounded-md border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50"
          >
            Reset to step 1
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Field label="Linked order" value={installation.order_no || (installation.order_id ? `#${installation.order_id}` : "Not linked")} mono />
        <Field label="Billing decision" value={installation.admin_billing_type} />
        <Field label="Engineer-entered serial" value={installation.engineer_entered_serial_no} mono />
        <Field label="Verified serial" value={installation.serial_no} mono />
      </div>

      {canViewCustomerDocuments && documents.length > 0 && (
        <div className="rounded-md border border-emerald-200 bg-white p-4">
          <CustomerDocumentList documents={documents} />
        </div>
      )}

      {canViewCustomerDocuments && (
        <WorkflowStepSection
          title="Step 2 — Link / verify order"
          done={workflowSteps.steps[2].done}
          locked={workflowSteps.steps[2].locked}
          borderClass="border-violet-200"
          summary={`Order verified${installation.order_no ? `: ${installation.order_no}` : ""}.`}
        >
          <p className="text-xs text-violet-800">
            Search by customer mobile, name, or order number. Matching orders appear below —
            click <strong>Link &amp; verify</strong> on the correct order.
          </p>
          <input
            type="text"
            value={orderSearch}
            onChange={(e) => setOrderSearch(e.target.value)}
            placeholder="Customer mobile, name, or order no (min. 2 characters)"
            className={`${fieldClass} mt-2`}
          />
          {orderSearchLoading && (
            <p className="mt-2 text-xs text-slate-500">Searching orders…</p>
          )}
          {!orderSearchLoading && orderSearchAttempted && orderOptions.length === 0 && orderSearch.trim().length >= 2 && (
            <p className="mt-2 text-xs text-amber-700">
              No matching orders found for &ldquo;{orderSearch.trim()}&rdquo;. Try mobile number or full order number.
            </p>
          )}
          {orderOptions.length > 0 && (
            <div className="mt-2 max-h-48 space-y-2 overflow-auto">
              {orderOptions.map((option) => (
                <div
                  key={option.order_id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-white px-3 py-2"
                >
                  <div className="min-w-0 text-sm">
                    <div className="font-medium">Order {option.order_no || `#${option.order_id}`}</div>
                    <div className="text-xs text-slate-500">
                      {[option.customer_name, option.customer_mobile].filter(Boolean).join(" • ")}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => run(() => installationsApi.verifyOrder(installation.id, { order_id: option.order_id }))}
                    className="shrink-0 rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700"
                  >
                    Link &amp; verify
                  </button>
                </div>
              ))}
            </div>
          )}
        </WorkflowStepSection>
      )}

      {canViewCustomerDocuments && (
        <WorkflowStepSection
          title="Step 3 — Customer documents"
          done={workflowSteps.steps[3].done}
          locked={workflowSteps.steps[3].locked}
          borderClass="border-emerald-200"
          summary={installation.document_request_sent_at
            ? `Customer upload link sent on ${new Date(installation.document_request_sent_at).toLocaleString()}.`
            : "Customer document request recorded."}
          footer={<CustomerDocumentList documents={documents} />}
        >
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => run(() => installationsApi.requestDocumentLink(installation.id))}
              className="rounded-md bg-sky-700 px-3 py-2 text-sm text-white"
              disabled={!installation.customer_email}
            >
              Send customer upload link
            </button>
          </div>
          {!installation.customer_email && (
            <p className="mt-2 text-xs text-amber-700">Add customer email on the request before sending the upload link.</p>
          )}
          {installation.document_upload_url && (
            <a href={installation.document_upload_url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-xs text-sky-700 underline">
              {installation.document_upload_url}
            </a>
          )}
        </WorkflowStepSection>
      )}

      {(isAdminLike || isServiceTeam) && installation.order_verified_at && (
        <WorkflowStepSection
          title="Step 4 — Assign engineer"
          done={workflowSteps.steps[4].done && workflowSteps.steps[4].locked}
          locked={workflowSteps.steps[4].locked}
          borderClass="border-emerald-200"
          summary={installation.assigned_engineer_name
            ? `Assigned to ${installation.assigned_engineer_name}.`
            : "Engineer assignment completed."}
        >
          <p className="text-xs text-emerald-800">
            One engineer can be assigned to multiple installation requests on the same order.
          </p>
          {installation.assigned_engineer_name && canAssignEngineer && (
            <p className="mt-2 text-xs text-amber-800">
              Currently assigned to {installation.assigned_engineer_name}. Pick another engineer below to re-assign.
            </p>
          )}
          {!canAssignEngineer && (
            <p className="mt-2 text-xs text-amber-700">
              Engineer cannot be changed after serial numbers are verified.
            </p>
          )}
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
            <EngineerSelect engineers={engineerOptions} value={selectedEngineerId} onChange={(e) => setSelectedEngineerId(e.target.value)} disabled={!canAssignEngineer} emptyLabel="Select engineer" selectClassName={fieldClass} />
            <button
              type="button"
              disabled={!selectedEngineerId || !canAssignEngineer}
              onClick={() => run(async () => {
                const result = await installationsApi.bulkAssign([
                  { installation_id: installation.id, engineer_id: Number(selectedEngineerId) },
                ]);
                if (!result.assigned?.length) {
                  const skipped = result.skipped_wrong_status?.[0];
                  throw new Error(
                    skipped
                      ? `Cannot assign while status is ${skipped.status}.`
                      : "Engineer assignment failed",
                  );
                }
              })}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {isReassign ? "Re-assign engineer" : "Assign engineer"}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
        </WorkflowStepSection>
      )}

      {showSerialWorkflow && (
        <InstallationEngineerSerialWorkflow
          installationId={installation.id}
          installationStatus={installation.status}
          assignedEngineerId={installation.assigned_engineer}
          serialVerifiedAt={installation.serial_verified_at}
          engineerSiteRemarks={installation.engineer_site_remarks}
          isEngineer={isEngineer}
          isAdminLike={isAdminLike}
          isPaymentAdmin={isPaymentAdmin}
          userId={userId}
          showAdminVerify={isAdminLike}
          workflowSteps={workflowSteps}
          onUpdated={onUpdated}
          onError={onError}
          onBusy={onBusy}
        />
      )}

      {installation.serial_verified_at && (
        <InstallationPostVerifyWorkflow
          installation={installation}
          isEngineer={isEngineer}
          isAdminLike={isAdminLike}
          isPaymentAdmin={isPaymentAdmin}
          userId={userId}
          workflowSteps={workflowSteps}
          onUpdated={onUpdated}
          onError={onError}
          onBusy={onBusy}
        />
      )}

    </section>
  );
}
