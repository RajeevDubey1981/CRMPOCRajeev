import { hasPermission } from "../../utils/permissions.js";
import { useEffect, useState } from "react";
import PriorityBadge from "../../components/complaints/PriorityBadge.jsx";
import { BOUNCED_BUTTON, BounceBanner } from "../../components/EmailBounceNotice.jsx";
import { Link, useNavigate, useParams } from "react-router-dom";

import StatusBadge from "../../components/StatusBadge.jsx";
import Modal from "../../components/Modal.jsx";
import { complaintsApi } from "../../api/complaints.js";
import { installationsApi } from "../../api/installations.js";
import { servicesApi } from "../../api/services.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";
import { formatApiError } from "../../utils/apiError.js";
import { getInstallationWorkflowPath, getServiceRequestPath } from "../../utils/complaintLinks.js";
import { canAssignCallcenterEngineer } from "../../utils/installationWorkflowSteps.js";
import { callsApi } from "../../api/calls.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole, isServiceTeamRole } from "../../utils/roles.js";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";
import EngineerSelect from "../../components/EngineerSelect.jsx";
import ComplaintEdit from "./ComplaintEdit.jsx";
import InstallationEngineerSerialWorkflow from "../../components/installations/InstallationEngineerSerialWorkflow.jsx";
import InstallationPostVerifyWorkflow from "../../components/installations/InstallationPostVerifyWorkflow.jsx";

function fmt(value) {
  return value ? new Date(value).toLocaleString() : "-";
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

export default function ComplaintDetail() {
  const { user: permUser } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const isCallcenter = role === "callcenter";
  const isAdminLike = isServiceTeamRole(role);
  const isEngineer = role === "engineer";
  const canLinkCustomerOrder = isOperationsAdminRole(role);
  const canEditComplaint = isCallcenter || isAdminLike;
  const [complaint, setComplaint] = useState(null);
  const [history, setHistory] = useState([]);
  const [calls, setCalls] = useState([]);
  const [linkedService, setLinkedService] = useState(null);
  const [linkedInstallation, setLinkedInstallation] = useState(null);
  const [installationDocuments, setInstallationDocuments] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerOptions, setCustomerOptions] = useState([]);
  const [showOrderLink, setShowOrderLink] = useState(false);
  const [engineerOptions, setEngineerOptions] = useState([]);
  const [selectedEngineerId, setSelectedEngineerId] = useState("");

  async function load() {
    try {
      const [complaintResult, historyResult] = await Promise.all([
        complaintsApi.get(id),
        complaintsApi.history(id),
      ]);
      let callsData = { items: [] };
      let serviceData = null;
      let installationData = null;
      try {
        callsData = await callsApi.list({ complaint_id: parseInt(id, 10) });
      } catch {
        callsData = { items: [] };
      }
      const queryType = (complaintResult.query_type || "").toLowerCase();
      if (queryType === "service") {
        try {
          serviceData = await complaintsApi.linkedServiceRequest(id);
        } catch {
          serviceData = null;
        }
      }
      if (queryType === "installation") {
        try {
          if (complaintResult.order_id) {
            try {
              await complaintsApi.ensureInstallationRequest(id);
            } catch {
              // Best-effort sync of linked order into installation workflow.
            }
          }
          installationData = await complaintsApi.linkedInstallationRequest(id);
          if (installationData?.installation_request_id) {
            try {
              const docs = await installationsApi.documents(installationData.installation_request_id);
              setInstallationDocuments(Array.isArray(docs) ? docs : []);
            } catch {
              setInstallationDocuments([]);
            }
          } else {
            setInstallationDocuments([]);
          }
        } catch {
          installationData = null;
          setInstallationDocuments([]);
        }
      }
      setComplaint(complaintResult);
      setHistory(Array.isArray(historyResult) ? historyResult : []);
      setCalls(Array.isArray(callsData?.items) ? callsData.items : []);
      setLinkedService(serviceData);
      setLinkedInstallation(installationData);
    } catch (error) {
      setErr(formatApiError(error, "Failed to load"));
    }
  }

  async function refreshComplaintAndInstallation() {
    const [complaintResult, installationData] = await Promise.all([
      complaintsApi.get(id),
      complaintsApi.linkedInstallationRequest(id),
    ]);
    setComplaint(complaintResult);
    setLinkedInstallation(installationData);
    if (installationData?.assigned_engineer) {
      setSelectedEngineerId(String(installationData.assigned_engineer));
    }
  }

  async function assignInstallationEngineer() {
    const installationRequestId = linkedInstallation?.installation_request_id;
    if (!installationRequestId || !selectedEngineerId) return;
    setBusy(true);
    setErr("");
    try {
      const result = await installationsApi.bulkAssign([{
        installation_id: installationRequestId,
        engineer_id: Number(selectedEngineerId),
      }]);
      if (!result.assigned?.length) {
        const skipped = result.skipped_wrong_status?.[0];
        throw new Error(
          skipped
            ? `Cannot assign while status is ${skipped.status}. Click Order verified first.`
            : "Engineer assignment failed",
        );
      }
      await refreshComplaintAndInstallation();
    } catch (error) {
      setErr(formatApiError(error, "Engineer assignment failed"));
    } finally {
      setBusy(false);
    }
  }

  async function rejectComplaint() {
    if (!window.confirm(`Reject complaint ${complaint.comp_no}?`)) return;
    setBusy(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("new_status", "Rejected");
      fd.append("remark", "Rejected by admin");
      await complaintsApi.updateStatus(id, fd);
      await load();
    } catch (error) {
      setErr(formatApiError(error, "Failed to reject complaint"));
    } finally {
      setBusy(false);
    }
  }

  async function deleteComplaint() {
    setBusy(true);
    setErr("");
    try {
      await complaintsApi.remove(id);
      navigate("/complaints");
    } catch (error) {
      setErr(formatApiError(error, "Failed to delete complaint"));
      setConfirmDelete(false);
    } finally {
      setBusy(false);
    }
  }

  async function linkCustomerOption(option) {
    setBusy(true);
    setErr("");
    const queryType = (complaint?.query_type || "").toLowerCase();
    const isInstallation = queryType === "installation";
    try {
      const updated = await complaintsApi.linkCustomer(id, {
        order_id: option.order_id || null,
        order_item_id: option.order_item_id || null,
        customer_name: option.customer_name || null,
        customer_mobile: option.customer_mobile || null,
        customer_email: option.customer_email || null,
        customer_address: option.customer_address || null,
        serial_no: option.serial_no || null,
      });
      setCustomerSearch("");
      setCustomerOptions([]);
      setShowOrderLink(false);
      if (!isInstallation && updated.order_id) {
        navigate(`/orders/${updated.order_id}`);
        return;
      }
      if (isInstallation) {
        await complaintsApi.ensureInstallationRequest(id);
      }
      await load();
    } catch (error) {
      setErr(formatApiError(error, "Failed to link order"));
    } finally {
      setBusy(false);
    }
  }

  async function run(action) {
    setBusy(true);
    setErr("");
    try {
      await action();
      await load();
    } catch (error) {
      setErr(formatApiError(error, "Action failed"));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  useEffect(() => {
    const installationId = linkedInstallation?.installation_request_id;
    if (!complaint || !installationId || isCallcenter) return;
    const queryType = (complaint.query_type || "").toLowerCase();
    if (queryType !== "installation") return;
    navigate(getInstallationWorkflowPath(installationId), { replace: true });
  }, [complaint, linkedInstallation?.installation_request_id, navigate, isCallcenter]);

  useEffect(() => {
    const serviceRequestId = linkedService?.service_request_id;
    if (!complaint || !serviceRequestId) return;
    const queryType = (complaint.query_type || "").toLowerCase();
    if (queryType !== "service") return;
    navigate(getServiceRequestPath(serviceRequestId), { replace: true });
  }, [complaint, linkedService?.service_request_id, navigate]);

  useEffect(() => {
    if (!canLinkCustomerOrder) return undefined;
    const query = customerSearch.trim();
    if (query.length < 2) {
      setCustomerOptions([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      complaintsApi.searchCustomers({ mobile: query, name: query, order_no: query })
        .then(setCustomerOptions)
        .catch(() => setCustomerOptions([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [customerSearch, canLinkCustomerOrder]);

  const isInstallationQuery = (complaint?.query_type || "").toLowerCase() === "installation";
  const complaintHasOrder = Boolean(complaint?.order_id || complaint?.order_item_id);
  const orderVerifiedOnInstallation = Boolean(linkedInstallation?.order_verified_at);
  const showAssignEngineerSection = isInstallationQuery
    && !isCallcenter
    && canLinkCustomerOrder
    && complaintHasOrder
    && Boolean(linkedInstallation?.installation_request_id)
    && orderVerifiedOnInstallation;

  useEffect(() => {
    if (!showAssignEngineerSection) return;
    installationsApi.engineerAssignmentOptions(complaint?.customer_address, complaint)
      .then(setEngineerOptions)
      .catch(() => setEngineerOptions([]));
  }, [showAssignEngineerSection, linkedInstallation?.installation_request_id, complaint?.customer_address, complaint?.pincode, complaint?.state, complaint?.district]);

  useEffect(() => {
    if (linkedInstallation?.assigned_engineer) {
      setSelectedEngineerId(String(linkedInstallation.assigned_engineer));
    }
  }, [linkedInstallation?.assigned_engineer]);

  if (err && !complaint) {
    return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  }
  if (!complaint) {
    return <div className="text-center text-slate-500">Loading...</div>;
  }

  const isServiceComplaint = (complaint.query_type || "").toLowerCase() === "service";
  const isInstallationComplaint = (complaint.query_type || "").toLowerCase() === "installation";
  const installationDocumentsSent = Boolean(linkedInstallation?.document_request_sent_at);
  const callcenterLocked = isCallcenter && (
    Boolean(linkedService?.document_request_sent_at)
    || (isInstallationComplaint && installationDocumentsSent)
  );
  const hasOrderLink = Boolean(complaint.order_id || complaint.order_item_id);
  const canManageInstallationDocuments = isAdminLike || isCallcenter;
  const showLinkOrderSection = canLinkCustomerOrder && !isCallcenter && (!isInstallationComplaint || installationDocumentsSent) && (!hasOrderLink || showOrderLink);
  const installationAssignmentLocked = Boolean(linkedInstallation?.assigned_engineer_name);
  const canAssignInstallationEngineer = canAssignCallcenterEngineer(linkedInstallation);
  const showVerifyOrderSection = isInstallationComplaint
    && !isCallcenter
    && canLinkCustomerOrder
    && hasOrderLink
    && Boolean(linkedInstallation?.installation_request_id);
  const orderVerified = Boolean(linkedInstallation?.order_verified_at);
  const showEngineerSerialWorkflow = isInstallationComplaint
    && !isCallcenter
    && linkedInstallation?.installation_request_id
    && (linkedInstallation?.assigned_engineer || complaint.assigned_engineer)
    && orderVerified;
  const isAssignedInstallationEngineer = isEngineer
    && (
      Number(linkedInstallation?.assigned_engineer) === Number(user?.id)
      || Number(complaint?.assigned_engineer) === Number(user?.id)
    );
  const showPostVerifyWorkflow = isInstallationComplaint
    && !isCallcenter
    && linkedInstallation?.installation_request_id
    && linkedInstallation?.serial_verified_at
    && (canLinkCustomerOrder || isAssignedInstallationEngineer);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/complaints" className="text-sm text-brand-600 hover:underline">Back to complaints</Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-2xl font-bold text-slate-900 sm:text-3xl">
            Complaint <span className="font-mono text-lg text-slate-500">{complaint.comp_no}</span>
            <StatusBadge value={complaint.status} />
            {complaint.priority === "High" && <PriorityBadge at={complaint.priority_at} by={complaint.priority_by_name} />}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {canEditComplaint && (
            <>
              <button
                type="button"
                onClick={() => setEditOpen(true)}
                disabled={busy}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => run(() => complaintsApi.setPriority(id, complaint.priority === "High" ? "Normal" : "High"))}
                disabled={busy}
                title={complaint.priority === "High" ? "Remove the high priority mark" : "Mark as HIGH priority: it will blink and be shown first in the list"}
                className={`rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-50 ${complaint.priority === "High" ? "border-orange-600 bg-orange-100 text-orange-800 hover:bg-orange-200" : "border-orange-300 text-orange-700 hover:bg-orange-50"}`}
              >
                {complaint.priority === "High" ? "Clear priority" : "Mark high priority"}
              </button>
              {complaint.status !== "Rejected" && (
                <button
                  type="button"
                  onClick={rejectComplaint}
                  disabled={busy}
                  className="rounded-md border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                >
                  Reject
                </button>
              )}
{hasPermission(permUser, "complaints", "can_delete", complaint?.query_type) && (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                disabled={busy}
                className="rounded-md border border-rose-400 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              >
                Delete
              </button>
)}
            </>
          )}
          {!callcenterLocked && (
            <>
              <button
                onClick={() => navigate(`/calls/calendar?complaint_id=${id}`)}
                className="inline-flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Calendar
              </button>
              <button
                onClick={() => navigate(`/calls/pending-follow-ups?complaint_id=${id}`)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
              >
                Follow-ups
              </button>
              <button
                onClick={() => navigate(`/calls/new?complaint_id=${id}`)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Log Call
              </button>
            </>
          )}
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{formatApiError(err)}</div>}

      {complaint.email_bounced && (
        <BounceBanner email={complaint.customer_email} reason={complaint.email_bounce_reason} />
      )}

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Customer and complaint details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Customer name" value={complaint.customer_name} />
          <Field label="Mobile" value={complaint.customer_mobile} mono />
          <Field label="Email" value={complaint.customer_email} />
          <Field label="Query type" value={complaint.query_type} />
          <Field label="Complaint date" value={complaint.comp_date} />
          <Field label="Model" value={complaint.model_details} />
          <Field label="Address" value={complaint.customer_address} full />
          <Field label="Problem description" value={complaint.problem_description} full />
          <Field label="Remark" value={complaint.remark} full />
          <Field label="Assigned engineer" value={complaint.assigned_engineer_name} />
          <Field label="Created by" value={complaint.created_by_name} />
          <Field label="Created at" value={fmt(complaint.created_at)} />
          <Field label="Last status change" value={fmt(complaint.status_date)} />
          {hasOrderLink && !isCallcenter && (
            <>
              <Field label="Linked order" value={complaint.order_no || (complaint.order_id ? `#${complaint.order_id}` : "—")} mono />
              <Field label="Linked serial" value={complaint.serial_no} mono />
            </>
          )}
        </div>
        {isInstallationComplaint && canManageInstallationDocuments && (
          <div className="mt-4 rounded-md border border-sky-200 bg-sky-50 p-4 text-sm text-slate-800">
            <div className="font-medium text-sky-900">Step 1 — Ask for customer documents</div>
            {callcenterLocked ? (
              <div className="mt-2 space-y-2 text-xs text-slate-600">
                <p>
                  Customer upload link sent. Further workflow is handled by admin.
                  {complaint.status === "Resolved"
                    ? " This complaint is resolved."
                    : " You can track the complaint status below."}
                </p>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Complaint status" value={complaint.status} />
                  <Field
                    label="Link sent at"
                    value={linkedInstallation?.document_request_sent_at ? fmt(linkedInstallation.document_request_sent_at) : "Not sent"}
                  />
                  {linkedInstallation?.status && (
                    <Field label="Installation progress" value={linkedInstallation.status} />
                  )}
                </div>
              </div>
            ) : (
              <>
                <p className="mt-1 text-xs text-slate-600">
                  Request purchase order / invoice from the customer before linking an order.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => run(() => complaintsApi.ensureInstallationRequest(id))}
                    disabled={busy}
                    className="rounded-md border border-sky-300 px-3 py-2 text-sm text-sky-800 disabled:opacity-50"
                  >
                    {linkedInstallation?.installation_request_id ? "Refresh installation workflow" : "Create installation workflow"}
                  </button>
                  <button
                    type="button"
                    onClick={() => run(() => complaintsApi.requestInstallationUploadLink(id))}
                    disabled={busy || !complaint.customer_email}
                    className="rounded-md bg-sky-700 px-3 py-2 text-sm text-white disabled:opacity-50"
                  >
                    Send customer upload link
                  </button>
                </div>
                {!complaint.customer_email && (
                  <p className="mt-2 text-xs text-amber-700">Add customer email (Edit complaint) before sending the upload link.</p>
                )}
                <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field
                    label="Linked installation request"
                    value={linkedInstallation?.installation_request_id ? `#${linkedInstallation.installation_request_id}` : "Not created"}
                  />
                  <Field
                    label="Link sent at"
                    value={linkedInstallation?.document_request_sent_at ? fmt(linkedInstallation.document_request_sent_at) : "Not sent"}
                  />
                </div>
                {linkedInstallation?.upload_url && (
                  <div className="mt-3">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Upload URL</div>
                    <a href={linkedInstallation.upload_url} target="_blank" rel="noreferrer" className="mt-1 block break-all text-sm text-sky-700 underline">
                      {linkedInstallation.upload_url}
                    </a>
                  </div>
                )}
                {installationDocuments.length > 0 && (
                  <ul className="mt-3 space-y-2 text-xs text-slate-700">
                    {installationDocuments.map((doc) => (
                      <li key={doc.id} className="rounded border border-slate-200 bg-white px-3 py-2">
                        <div className="font-medium text-slate-800">{doc.document_type}</div>
                        <div className="text-slate-500">{doc.status}</div>
                        <a
                          href={toDownloadUrl(doc.file_path)}
                          download
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-block text-sky-700 underline"
                        >
                          Download document
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
            {linkedInstallation?.installation_request_id && !isCallcenter && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={() => navigate(getInstallationWorkflowPath(linkedInstallation.installation_request_id))}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700"
                >
                  Open installation request
                </button>
              </div>
            )}
          </div>
        )}
        {showLinkOrderSection && (
          <div className="mt-4 rounded-md border border-violet-200 bg-violet-50 p-4 text-sm text-slate-800">
            <div className="font-medium text-violet-900">
              {isInstallationComplaint ? "Step 2 — Link customer or order" : hasOrderLink ? "Change linked order" : "Link customer or order"}
            </div>
            <p className="mt-1 text-xs text-violet-800">
              Search by customer name, mobile number, or order number. Pick an order — no serial number required.
            </p>
            <input
              type="text"
              value={customerSearch}
              onChange={(e) => setCustomerSearch(e.target.value)}
              placeholder="Customer name, mobile, or order no"
              className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {customerOptions.length > 0 && (
              <div className="mt-2 max-h-56 space-y-2 overflow-auto rounded-md border border-violet-200 bg-white p-2">
                {customerOptions.map((option) => (
                  <button
                    key={`${option.source_type || "result"}-${option.order_id || option.order_item_id || option.customer_mobile || option.customer_name}`}
                    type="button"
                    disabled={busy}
                    onClick={() => linkCustomerOption(option)}
                    className="block w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm hover:bg-violet-50 disabled:opacity-50"
                  >
                    <div className="font-medium text-slate-800">
                      {option.source_type === "order" && option.order_no
                        ? `Order ${option.order_no}`
                        : option.source_type === "complaint"
                          ? `Past complaint — ${option.customer_name || "—"}`
                          : option.customer_name || "—"}
                    </div>
                    <div className="text-xs text-slate-500">
                      {[
                        option.customer_name && option.source_type === "order" ? option.customer_name : null,
                        option.customer_mobile,
                        option.customer_email,
                      ].filter(Boolean).join(" • ")}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {isInstallationComplaint && canLinkCustomerOrder && !installationDocumentsSent && (
          <p className="mt-3 text-xs text-violet-800">
            Send the customer document upload link first. Order linking unlocks after the link is sent.
          </p>
        )}
        {canLinkCustomerOrder && hasOrderLink && complaint.order_id && (
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to={`/orders/${complaint.order_id}`}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Open linked order {complaint.order_no || `#${complaint.order_id}`}
            </Link>
            {!showOrderLink && (
              <button
                type="button"
                onClick={() => setShowOrderLink(true)}
                className="rounded-md border border-violet-300 px-3 py-2 text-sm text-violet-800 hover:bg-violet-50"
              >
                Change linked order
              </button>
            )}
          </div>
        )}
        {showVerifyOrderSection && (
          <div className="mt-4 rounded-md border border-indigo-200 bg-indigo-50 p-4 text-sm text-slate-800">
            <div className="font-medium text-indigo-900">Step 3 — Order verification</div>
            <p className="mt-1 text-xs text-indigo-800">
              Confirm the linked order before assigning an engineer.
            </p>
            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field
                label="Linked order"
                value={linkedInstallation?.order_no || complaint.order_no || (complaint.order_id ? `#${complaint.order_id}` : "—")}
                mono
              />
              <Field
                label="Verification status"
                value={orderVerified ? `Verified · ${fmt(linkedInstallation.order_verified_at)}` : "Pending verification"}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {!orderVerified ? (
                <button
                  type="button"
                  onClick={() => run(() => complaintsApi.verifyInstallationOrder(id))}
                  disabled={busy}
                  className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800 disabled:opacity-50"
                >
                  Order verified
                </button>
              ) : (
                <span className="inline-flex items-center rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
                  Order verified
                </span>
              )}
            </div>
          </div>
        )}
        {showAssignEngineerSection && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-slate-800">
            <div className="font-medium text-emerald-900">Step 4 — Assign engineer</div>
            <p className="mt-1 text-xs text-emerald-800">
              Assign an installation engineer after the order is verified.
            </p>
            {installationAssignmentLocked && (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Currently assigned to {linkedInstallation.assigned_engineer_name || complaint.assigned_engineer_name || "engineer"}.
                Select a different engineer below to re-assign.
              </div>
            )}
            {!canAssignInstallationEngineer && (
              <p className="mt-3 text-xs text-amber-700">
                Installation workflow status is {linkedInstallation?.status || "unknown"}.
                {" "}Click <strong>Order verified</strong> above if you have not verified the linked order yet.
              </p>
            )}
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
              <div>
                <label className="text-xs uppercase tracking-wide text-slate-500">Engineer</label>
                <EngineerSelect engineers={engineerOptions} value={selectedEngineerId} onChange={(e) => setSelectedEngineerId(e.target.value)} disabled={busy} emptyLabel="Select engineer" selectClassName="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100" />
                <p className="mt-1 text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
                {engineerOptions.length === 0 && (
                  <p className="mt-1 text-xs text-slate-500">No engineers available for assignment.</p>
                )}
              </div>
              <button
                type="button"
                disabled={busy || !selectedEngineerId || !canAssignInstallationEngineer}
                onClick={assignInstallationEngineer}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Assign engineer
              </button>
            </div>
            {linkedInstallation?.installation_request_id && !isCallcenter && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-slate-500">
                  This request appears in the Installation Requests list only after an engineer is assigned.
                </p>
                <button
                  type="button"
                  onClick={() => navigate(getInstallationWorkflowPath(linkedInstallation.installation_request_id))}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700"
                >
                  Open installation workflow
                </button>
              </div>
            )}
          </div>
        )}
        {showEngineerSerialWorkflow && (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4">
            <InstallationEngineerSerialWorkflow
              installationId={linkedInstallation.installation_request_id}
              installationStatus={linkedInstallation.status}
              assignedEngineerId={linkedInstallation.assigned_engineer || complaint.assigned_engineer}
              serialVerifiedAt={linkedInstallation.serial_verified_at}
              engineerSiteRemarks={linkedInstallation.engineer_site_remarks}
              isEngineer={isEngineer}
              isAdminLike={canLinkCustomerOrder}
              userId={user?.id}
              showAdminVerify={canLinkCustomerOrder}
              onUpdated={refreshComplaintAndInstallation}
              onError={setErr}
              onBusy={setBusy}
            />
          </div>
        )}
        {showPostVerifyWorkflow && (
          <div className="mt-4 rounded-md border border-sky-200 bg-sky-50 p-4">
            <InstallationPostVerifyWorkflow
              installation={{
                ...linkedInstallation,
                id: linkedInstallation.installation_request_id,
                assigned_engineer: linkedInstallation.assigned_engineer || complaint.assigned_engineer,
              }}
              isEngineer={isEngineer}
              isAdminLike={isAdminLike}
              userId={user?.id}
              onUpdated={refreshComplaintAndInstallation}
              onError={setErr}
              onBusy={setBusy}
            />
          </div>
        )}
        {!isCallcenter && (
        <div className="mt-4 rounded-md border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
          <strong>Access code (prototype-only):</strong>{" "}
          <span className="font-mono">{complaint.access_code || "-"}</span>
          <div className="mt-1">
            In production this is delivered to the customer by SMS; the engineer asks the customer for it
            when marking the complaint resolved. Shown here only for testing.
          </div>
        </div>
        )}
        {isServiceComplaint && (
          <div className="mt-4 rounded-md border border-sky-200 bg-sky-50 p-4 text-sm text-slate-800">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-medium text-sky-900">Customer document upload</div>
                <div className="mt-1 text-xs text-slate-600">
                  {callcenterLocked
                    ? "Customer upload link sent. This complaint is read-only for call center."
                    : linkedService?.upload_url
                    ? "Upload link ready"
                    : linkedService?.service_request_id
                      ? "Service workflow created"
                      : "No service workflow created yet"}
                </div>
              </div>
              {!callcenterLocked && (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => run(() => complaintsApi.ensureServiceRequest(id))}
                    disabled={busy}
                    className="rounded-md border border-sky-300 px-3 py-2 text-sm text-sky-800 disabled:opacity-50"
                  >
                    {linkedService?.service_request_id ? "Refresh Service Workflow" : "Create Service Workflow"}
                  </button>
                  <button
                    onClick={() => {
                      const alreadySent = Boolean(linkedService?.document_request_sent_at);
                      if (complaint.email_bounced && !window.confirm(`The last email to ${complaint.customer_email} BOUNCED. Please correct the email address first.\n\nSend the link anyway?`)) return;
                      if (alreadySent && !window.confirm("The customer upload link was already sent. Do you want to send it again?")) return;
                      run(() => complaintsApi.requestCustomerUploadLink(id, alreadySent));
                    }}
                    disabled={busy}
                    className={`rounded-md px-3 py-2 text-sm text-white disabled:opacity-50 ${complaint.email_bounced ? "border " + BOUNCED_BUTTON : "bg-sky-700"}`}
                  >
                    {complaint.email_bounced ? "Email bounced - fix & resend" : "Send Customer Upload Link"}
                  </button>
                </div>
              )}
            </div>
            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Linked service request" value={linkedService?.request_no || "Not created"} />
              <Field label="Service status" value={linkedService?.status || "Not created"} />
              <Field label="Link sent at" value={linkedService?.document_request_sent_at ? fmt(linkedService.document_request_sent_at) : "Not sent"} />
              <Field
                label="Documents approved"
                value={linkedService?.customer_documents_approved ? "Yes" : linkedService?.documents?.length ? "Pending review" : "Not uploaded"}
              />
            </div>
            {linkedService?.status === "Admin Review Document" && isAdminLike && (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Customer documents are uploaded. Review and approve each document below to continue the service workflow.
              </div>
            )}
            {(linkedService?.documents || []).length > 0 && (
              <ul className="mt-3 space-y-2 text-xs text-slate-700">
                {(linkedService.documents || []).map((doc) => (
                  <li key={doc.id} className="rounded border border-slate-200 bg-white px-3 py-2">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-slate-800">{doc.document_type}</div>
                        <div className="text-slate-500">
                          {doc.status}
                          {doc.uploaded_at ? ` • ${fmt(doc.uploaded_at)}` : ""}
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
                      </div>
                      {isAdminLike && !["Reviewed", "Approved", "Rejected"].includes(doc.status) && linkedService?.service_request_id && (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => run(() => servicesApi.reviewDocument(
                              linkedService.service_request_id,
                              doc.id,
                              { status: "Reviewed", remarks: "Approved" },
                            ))}
                            className="rounded-md border border-emerald-300 px-2 py-1 text-xs text-emerald-700"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => run(() => servicesApi.reviewDocument(
                              linkedService.service_request_id,
                              doc.id,
                              { status: "Rejected", remarks: "Rejected" },
                            ))}
                            className="rounded-md border border-rose-300 px-2 py-1 text-xs text-rose-700"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {linkedService?.service_request_id && (
              <div className="mt-3">
                <button
                  onClick={() => navigate(`/services/${linkedService.service_request_id}`)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700"
                >
                  Open Service Workflow
                </button>
              </div>
            )}
            {linkedService?.upload_url && (
              <div className="mt-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">Upload URL</div>
                <a href={linkedService.upload_url} target="_blank" rel="noreferrer" className="mt-1 block break-all text-sm text-sky-700 underline">
                  {linkedService.upload_url}
                </a>
              </div>
            )}
          </div>
        )}
      </section>

      {editOpen && (
        <ComplaintEdit
          complaint={complaint}
          onClose={() => setEditOpen(false)}
          onSaved={() => { setEditOpen(false); load(); }}
        />
      )}

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete complaint?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete complaint <span className="font-mono">{complaint.comp_no}</span>.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setConfirmDelete(false)} className="rounded border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button onClick={deleteComplaint} disabled={busy} className="rounded bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50">Delete</button>
          </div>
        </div>
      </Modal>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Status history</h2>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">No history entries yet.</p>
        ) : (
          <ol className="space-y-3">
            {history.map((entry) => (
              <li key={entry.id} className="rounded-md border border-slate-200 p-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  {entry.action_taken ? (
                    <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
                      Action: {entry.action_taken}
                    </span>
                  ) : (
                    <>
                      <StatusBadge value={entry.old_status} />
                      <span className="text-slate-400">to</span>
                      <StatusBadge value={entry.new_status} />
                    </>
                  )}
                  <span className="text-xs text-slate-500">{fmt(entry.changed_at)}</span>
                  <span className="text-xs text-slate-500">by {entry.changed_by_name || "-"}</span>
                </div>
                {entry.remark && <div className="mt-2 text-sm text-slate-700">{entry.remark}</div>}
                {entry.document_path && (
                  <div className="mt-1 text-xs text-slate-500">
                    Document: <span className="font-mono">{entry.document_path}</span>
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      {!isCallcenter && (
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-700">Call log ({calls.length})</h2>
          {!callcenterLocked && (
            <button
              onClick={() => navigate(`/calls/new?complaint_id=${id}`)}
              className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
            >
              + Log Call
            </button>
          )}
        </div>
        {calls.length === 0 ? (
          <p className="text-sm text-slate-500">No calls logged yet.</p>
        ) : (
          <div className="space-y-3">
            {calls.map((call) => {
              const hasPendingFollowup = call.follow_up_status === "Pending" && call.followup_date;
              return (
                <div
                  key={call.id}
                  onClick={() => navigate(`/calls/${call.id}`)}
                  className={`cursor-pointer rounded-md border p-4 hover:bg-blue-50 ${
                    hasPendingFollowup
                      ? "border-red-300 bg-red-50 hover:border-red-400"
                      : "border-slate-200 hover:border-blue-300"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-medium text-slate-900">{call.ref_no}</span>
                        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          call.status === "Completed" ? "bg-green-100 text-green-800" :
                          call.status === "Busy" ? "bg-red-100 text-red-800" :
                          call.status === "No Answer" ? "bg-gray-100 text-gray-800" :
                          call.status === "Call Back" ? "bg-yellow-100 text-yellow-800" :
                          "bg-purple-100 text-purple-800"
                        }`}>
                          {call.status}
                        </span>
                        {hasPendingFollowup && (
                          <span className="inline-flex items-center rounded-full bg-red-600 px-2.5 py-0.5 text-xs font-semibold text-white">
                            Follow-up pending
                          </span>
                        )}
                        {call.follow_up_status === "Completed" && call.followup_date && (
                          <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                            Follow-up done
                          </span>
                        )}
                      </div>
                      {hasPendingFollowup && (
                        <p className="mt-1 text-xs font-medium text-red-700">
                          Due: {new Date(call.followup_date).toLocaleString()}
                        </p>
                      )}
                      {call.notes && <p className="mt-2 text-sm text-slate-700">{call.notes}</p>}
                    </div>
                    <div className="text-right text-xs text-slate-500">
                      <div>{new Date(call.call_datetime).toLocaleString()}</div>
                      {call.assigned_to_name && <div className="mt-1">{call.assigned_to_name}</div>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
      )}
    </div>
  );
}
