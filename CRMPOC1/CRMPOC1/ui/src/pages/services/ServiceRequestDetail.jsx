import { useEffect, useMemo, useState } from "react";
import { BOUNCED_BUTTON, BounceBanner } from "../../components/EmailBounceNotice.jsx";
import { Link, useParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import ScanInput from "../../components/scan/ScanInput.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import {
  canAssignServiceDeskUser,
  canViewAllServiceRequests,
  isOperationsAdminRole,
  isServiceDeskRole,
  isSystemAdminRole,
  isServiceTeamRole,
} from "../../utils/roles.js";
import { servicesApi } from "../../api/services.js";
import { installationsApi } from "../../api/installations.js";
import ServiceUnitAssignmentPanel from "./ServiceUnitAssignmentPanel.jsx";
import EngineerUnitWorkflowPanel from "./EngineerUnitWorkflowPanel.jsx";
import { engineerIdsMatch, formatEngineerOptionLabel, ENGINEER_ASSIGNMENT_HINT } from "../../utils/engineerAssignment.js";

const PAYMENT_TYPES = ["Cash", "UPI"];
const SERVICE_STATUSES = [
  "New", "Service Team Review", "Admin Review Document", "Assigned", "Engineer Visit", "Serial Verification Review",
  "Serial Verified", "Pending Service Approval", "Approved for Service", "Service In Progress",
  "Completion Pending Approval", "Service Completed", "Payment Requested", "Payment Completed", "Closed", "Rejected", "Cancelled",
];

function Field({ label, value }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-800">{value || "-"}</div>
    </div>
  );
}

function buildCustomerUploadUrl(tokenOrUrl) {
  if (!tokenOrUrl) {
    return "";
  }
  if (/^https?:\/\//i.test(tokenOrUrl)) {
    return tokenOrUrl;
  }
  const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
  return new URL(`/services/public-upload/${tokenOrUrl}`, base).toString();
}

function toDownloadUrl(path) {
  if (!path) {
    return "#";
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const apiBase = import.meta.env.VITE_API_BASE_URL || window.location.origin;
  return new URL(path, apiBase).toString();
}

function fileNameFromPath(path) {
  if (!path) {
    return "";
  }
  return String(path).split(/[\\/]/).pop() || String(path);
}

function PaymentQrPanel({ path, title = "Payment QR Code" }) {
  if (!path) {
    return null;
  }
  const url = toDownloadUrl(path);
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="text-sm font-medium text-slate-800">{title}</div>
      <img
        src={url}
        alt={title}
        className="mt-2 max-h-64 rounded border border-slate-200 bg-white object-contain"
        onError={(e) => { e.currentTarget.style.display = "none"; }}
      />
      <a href={url} download target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm text-sky-700 underline">
        Download QR code ({fileNameFromPath(path)})
      </a>
    </div>
  );
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleDateString();
}

function formatDateInput(value) {
  if (!value) {
    return "";
  }
  return String(value).slice(0, 10);
}

function formatMoneyInput(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

function UploadDocumentModal({ open, onClose, onSubmit }) {
  const [documentType, setDocumentType] = useState("Invoice Copy");
  const [file, setFile] = useState(null);

  return (
    <Modal open={open} onClose={onClose} title="Upload Document">
      <div className="space-y-3">
        <input value={documentType} onChange={(e) => setDocumentType(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="w-full text-sm" />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
          <button onClick={() => onSubmit(documentType, file)} disabled={!file} className="rounded-md bg-brand-600 px-3 py-2 text-sm text-white disabled:opacity-50">Upload</button>
        </div>
      </div>
    </Modal>
  );
}

export default function ServiceRequestDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const [service, setService] = useState(null);
  const [history, setHistory] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [err, setErr] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerOptions, setCustomerOptions] = useState([]);
  const [selectedCustomerKey, setSelectedCustomerKey] = useState("");
  const [assignForm, setAssignForm] = useState({ assignee_type: "engineer", assignee_id: "", remarks: "" });
  const [serviceUsers, setServiceUsers] = useState([]);
  const [serviceDeskAssignForm, setServiceDeskAssignForm] = useState({ service_user_id: "", remarks: "" });
  const [returnToManagerRemarks, setReturnToManagerRemarks] = useState("");
  const [serialNo, setSerialNo] = useState("");
  const [observation, setObservation] = useState({ problem_found: "", observation: "", recommended_action: "", parts_required: "", estimated_service_charge: "", estimated_parts_charge: "", remarks: "" });
  const [approval, setApproval] = useState({ decision: "Approve", remarks: "" });
  const [completion, setCompletion] = useState({ work_performed: "", parts_replaced: "", service_notes: "", service_date: "", final_amount: "", completion_remarks: "", completion_code: "" });
  const [completionProof, setCompletionProof] = useState(null);
  const [payment, setPayment] = useState({ customer_charge_amount: "", settlement_service_amount: "", settlement_parts_amount: "", total_requested_amount: "", payment_type: "Cash", remarks: "" });
  const [paymentQrCode, setPaymentQrCode] = useState(null);
  const [paymentApproval, setPaymentApproval] = useState({ approved_amount: "", remarks: "", proof_document: null });
  const [cancelAssignmentOpen, setCancelAssignmentOpen] = useState(false);
  const [cancelObservationOpen, setCancelObservationOpen] = useState(false);
  const [cancelApprovalOpen, setCancelApprovalOpen] = useState(false);
  const [cancelCompletionOpen, setCancelCompletionOpen] = useState(false);
  const [cancelPaymentOpen, setCancelPaymentOpen] = useState(false);
  const [closeServiceOpen, setCloseServiceOpen] = useState(false);
  const [reopenEngineerOpen, setReopenEngineerOpen] = useState(false);
  const [reopenRemarks, setReopenRemarks] = useState("");
  const [closeRemarks, setCloseRemarks] = useState("");
  const [serialInfo, setSerialInfo] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState("");
  const [workflowRemarks, setWorkflowRemarks] = useState("");
  const [pendingOrderVerifyNo, setPendingOrderVerifyNo] = useState("");

  async function load() {
    try {
      setErr("");
      const [serviceResult, historyResult] = await Promise.all([
        servicesApi.get(id),
        servicesApi.history(id),
      ]);
      setService(serviceResult);
      setHistory(historyResult);
      setSerialNo(serviceResult.serial_no || "");
    } catch (error) {
      setService(null);
      setErr(error.response?.data?.detail || "Failed to load service request");
    }
  }

  useEffect(() => {
    load();
    servicesApi.serviceUsers().then(setServiceUsers).catch(() => setServiceUsers([]));
    servicesApi.vendors().then(setVendors).catch(() => null);
  }, [id]);

  // engineers to assign: the ones nearest the customer first (the address is known once the request has loaded)
  useEffect(() => {
    installationsApi.engineerAssignmentOptions(service?.customer_address).then(setEngineers).catch(() => setEngineers([]));
  }, [service?.customer_address]);

  useEffect(() => {
    if (!customerSearch.trim()) {
      setCustomerOptions([]);
      return;
    }
    const timer = setTimeout(() => {
      servicesApi.searchCustomers({ mobile: customerSearch, name: customerSearch, order_no: customerSearch })
        .then(setCustomerOptions)
        .catch(() => setCustomerOptions([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [customerSearch]);

  useEffect(() => {
    if (!service?.serial_no) {
      setSerialInfo(null);
      return;
    }
    servicesApi.serialLookup(service.serial_no)
      .then(setSerialInfo)
      .catch(() => setSerialInfo(null));
  }, [service?.serial_no]);

  useEffect(() => {
    const active = service?.assignments?.find((assignment) => assignment.is_active);
    if (!active) {
      return;
    }
    setAssignForm({
      assignee_type: active.assignee_type || "engineer",
      assignee_id: String(active.assignee_user_id || active.assignee_vendor_id || ""),
      remarks: active.remarks || "",
    });
  }, [service?.assignments]);

  useEffect(() => {
    const latest = service?.observations?.[0];
    if (!latest) {
      return;
    }
    setObservation({
      problem_found: latest.problem_found || "",
      observation: latest.observation || "",
      recommended_action: latest.recommended_action || "",
      parts_required: Array.isArray(latest.parts_required) ? latest.parts_required.join(", ") : "",
      estimated_service_charge: formatMoneyInput(latest.estimated_service_charge),
      estimated_parts_charge: formatMoneyInput(latest.estimated_parts_charge),
      remarks: latest.remarks || "",
    });
  }, [service?.observations]);

  useEffect(() => {
    const latest = service?.approvals?.[0];
    if (!latest) {
      return;
    }
    setApproval({
      decision: latest.decision || "Approve",
      remarks: latest.remarks || "",
    });
  }, [service?.approvals]);

  useEffect(() => {
    const latest = service?.completions?.[0];
    if (!latest) {
      return;
    }
    setCompletion({
      work_performed: latest.work_performed || "",
      parts_replaced: Array.isArray(latest.parts_replaced) ? latest.parts_replaced.join(", ") : "",
      service_notes: latest.service_notes || "",
      service_date: formatDateInput(latest.service_date),
      final_amount: formatMoneyInput(latest.final_amount),
      completion_remarks: latest.completion_remarks || "",
    });
  }, [service?.completions]);

  useEffect(() => {
    const latest = service?.payment_requests?.[0];
    if (!latest) {
      return;
    }
    setPayment({
      customer_charge_amount: formatMoneyInput(latest.customer_charge_amount),
      settlement_service_amount: formatMoneyInput(latest.settlement_service_amount),
      settlement_parts_amount: formatMoneyInput(latest.settlement_parts_amount),
      total_requested_amount: formatMoneyInput(latest.total_requested_amount),
      payment_type: latest.payment_type || "Cash",
      remarks: latest.remarks || "",
    });
    setPaymentApproval((current) => ({
      approved_amount: formatMoneyInput(latest.approved_amount ?? latest.total_requested_amount ?? latest.settlement_service_amount ?? latest.customer_charge_amount),
      remarks: current.remarks,
      proof_document: null,
    }));
  }, [service?.payment_requests]);

  async function run(action, options = {}) {
    setBusy(true);
    setErr("");
    if (!options.keepSuccess) {
      setSuccessMsg("");
    }
    try {
      const result = await action();
      if (result && result.id != null && Array.isArray(result.units)) {
        setService(result);
      }
      await load();
      const message = (result && result.successMessage) || options.successMessage;
      if (message) {
        setSuccessMsg(message);
      }
      if (options.scrollToId) {
        requestAnimationFrame(() => {
          document.getElementById(options.scrollToId)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      }
    } catch (error) {
      setErr(error.response?.data?.detail || "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const activeAssigneeOptions = useMemo(() => (
    engineers
  ), [engineers]);
  const roleIsServiceTeam = isServiceTeamRole(role);
  const roleIsServiceDesk = isServiceDeskRole(role);
  const roleCanViewAllServices = canViewAllServiceRequests(role);
  const canAssignServiceDesk = canAssignServiceDeskUser(role);
  const roleIsAdminLike = isOperationsAdminRole(role);
  const roleIsPaymentAdmin = isSystemAdminRole(role);
  const roleIsEngineer = role === "engineer";
  const roleIsVendor = role === "vendor";
  const canEditWorkflow = roleIsAdminLike;
  const documentsWorkflowUnlocked = Boolean(service?.customer_documents_approved);
  const engineerWorkUnits = useMemo(() => {
    if (!service?.units?.length) return [];
    if (roleIsEngineer) {
      return service.units.filter((unit) => engineerIdsMatch(unit.assigned_engineer_id, user?.id));
    }
    if (roleIsVendor || roleIsServiceTeam) {
      return service.units.filter((unit) => unit.assigned_engineer_id);
    }
    return [];
  }, [service?.units, roleIsEngineer, roleIsVendor, roleIsServiceTeam, user?.id]);
  const engineerOnRequest = roleIsEngineer && (
    engineerIdsMatch(service?.assigned_engineer_id, user?.id)
    || (service?.units || []).some((unit) => engineerIdsMatch(unit.assigned_engineer_id, user?.id))
  );
  const useUnitWorkflow = engineerWorkUnits.length > 0
    || ((roleIsVendor || roleIsServiceTeam) && (service?.units || []).some((unit) => unit.assigned_engineer_id))
    || (engineerOnRequest && (
      Boolean(service?.order_id)
      || Boolean((service?.customer_mobile || "").trim())
      || Boolean((service?.customer_email || "").trim())
      || Boolean((service?.customer_name || "").trim())
    ));
  const usePerUnitAssignment = Boolean(
    (service?.units?.length > 0) || (service?.order_items?.length > 0),
  );
  const unitAssignmentSummary = useMemo(() => {
    const units = service?.units || [];
    if (!units.length) {
      return null;
    }
    const byEngineer = new Map();
    let unassigned = 0;
    for (const unit of units) {
      if (unit.assigned_engineer_id) {
        const key = unit.assigned_engineer_id;
        if (!byEngineer.has(key)) {
          byEngineer.set(key, {
            name: unit.assigned_engineer_name || "Unknown",
            count: 0,
          });
        }
        byEngineer.get(key).count += 1;
      } else {
        unassigned += 1;
      }
    }
    return {
      assigned: Array.from(byEngineer.values()),
      unassigned,
      total: units.length,
    };
  }, [service?.units]);
  const assignedEngineerDisplay = useMemo(() => {
    if (service?.assigned_engineer_name) {
      return service.assigned_engineer_name;
    }
    if (!unitAssignmentSummary?.assigned.length) {
      return unitAssignmentSummary?.total ? "Pending unit assignment" : null;
    }
    return unitAssignmentSummary.assigned
      .map((row) => `${row.name} (${row.count} unit${row.count === 1 ? "" : "s"})`)
      .join(", ");
  }, [service?.assigned_engineer_name, unitAssignmentSummary]);
  const canCloseServiceRequest = useMemo(() => {
    if (!roleIsServiceTeam || service?.status === "Closed") {
      return false;
    }
    const units = service?.units || [];
    if (units.length > 0) {
      return units.every((unit) => unit.unit_status === "Payment Completed");
    }
    return service?.status === "Payment Completed";
  }, [service?.status, service?.units, roleIsServiceTeam]);

  const latestDocuments = useMemo(() => {
    if (!service?.documents?.length) {
      return [];
    }
    const byType = new Map();
    for (const document of service.documents) {
      const key = `${document.uploaded_by_type}::${document.document_type}`;
      if (!byType.has(key)) {
        byType.set(key, document);
      }
    }
    return Array.from(byType.values());
  }, [service]);

  const customerUploadUrl = useMemo(() => {
    if (!service) {
      return "";
    }
    if (service.upload_url) {
      return service.upload_url;
    }
    return buildCustomerUploadUrl(service.document_access_token);
  }, [service]);

  async function openCustomerUploadPage() {
    setBusy(true);
    setErr("");
    try {
      let uploadUrl = customerUploadUrl;
      if (!uploadUrl) {
        const result = await servicesApi.ensureDocumentLink(service.id);
        uploadUrl = result.upload_url || buildCustomerUploadUrl(service.document_access_token);
        await load();
      }
      if (!uploadUrl) {
        throw new Error("Could not create customer upload link");
      }
      window.open(uploadUrl, "_blank", "noopener,noreferrer");
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || "Could not open upload page");
    } finally {
      setBusy(false);
    }
  }

  const activeAssignment = useMemo(
    () => service?.assignments?.find((assignment) => assignment.is_active) || null,
    [service],
  );
  const assignmentLocked = Boolean(activeAssignment);
  const canCancelAssignment = Boolean(
    activeAssignment && (
      roleIsServiceTeam
      || (roleIsEngineer && activeAssignment.assignee_user_id === user?.id)
      || (roleIsVendor && activeAssignment.assignee_vendor_id === service?.assigned_vendor_id)
    ),
  );
  const latestObservation = service?.observations?.[0] || null;
  const serialVerified = Boolean(
    service?.serial_no
    && !["Assigned", "Engineer Visit", "Serial Verification Review"].includes(service?.status),
  );
  const canVerifySerial = Boolean(!serialVerified && ["Assigned", "Engineer Visit"].includes(service?.status));
  const observationSubmitted = service?.status === "Pending Service Approval";
  const canSubmitObservation = Boolean(
    serialVerified
    && service?.status === "Serial Verified"
    && (roleIsEngineer || roleIsVendor),
  );
  const canCancelObservation = Boolean(observationSubmitted && latestObservation && (roleIsEngineer || roleIsVendor || roleIsServiceTeam));
  const approvalPending = service?.status === "Pending Service Approval";
  const approvalCompleted = ["Approved for Service", "Rejected"].includes(service?.status);
  const canCancelApproval = Boolean(roleIsServiceTeam && approvalCompleted);
  const latestCompletion = service?.completions?.[0] || null;
  const canCompleteService = Boolean((roleIsEngineer || roleIsVendor) && ["Approved for Service", "Service In Progress"].includes(service?.status));
  const completionPendingApproval = service?.status === "Completion Pending Approval";
  const completionSubmitted = ["Service Completed", "Payment Requested", "Payment Completed", "Closed"].includes(service?.status)
    || completionPendingApproval;
  const completionBlockedHint = useMemo(() => {
    if (canCompleteService) return null;
    if (completionPendingApproval && (roleIsEngineer || roleIsVendor)) {
      return null;
    }
    if (completionSubmitted && !completionPendingApproval) return null;
    if (service?.status === "Pending Service Approval") {
      return "Waiting for INDcool/Admin service approval (Approval section above).";
    }
    if (["Approved for Service", "Service In Progress"].includes(service?.status) && roleIsServiceTeam && !roleIsEngineer && !roleIsVendor) {
      return "Service is approved. The assigned engineer must mark completion here (happy code + proof). Admin cannot complete on behalf of engineer.";
    }
    if (completionPendingApproval && roleIsServiceTeam) {
      return "Engineer submitted completion. Use the completion approval section above.";
    }
    return "Completion unlocks after service approval and engineer visit work.";
  }, [canCompleteService, completionSubmitted, completionPendingApproval, service?.status, roleIsServiceTeam, roleIsEngineer, roleIsVendor]);
  const canCancelCompletion = Boolean(
    (roleIsEngineer || roleIsVendor || roleIsServiceTeam)
    && ["Service Completed", "Completion Pending Approval"].includes(service?.status),
  );
  const latestPaymentRequest = service?.payment_requests?.[0] || null;
  const paymentSubmitted = service?.status === "Payment Requested";
  const paymentCompleted = ["Payment Completed", "Closed"].includes(service?.status);
  const canApprovePayment = Boolean(roleIsServiceTeam && paymentSubmitted && latestPaymentRequest);
  const latestPaymentFinalStage = latestPaymentRequest?.approval_stage === "admin"
    || latestPaymentRequest?.approval_stage_label === "Admin";
  const latestPaymentProofRequired = canApprovePayment
    && roleIsPaymentAdmin
    && latestPaymentFinalStage
    && (latestPaymentRequest?.payment_type || payment.payment_type) === "UPI";
  const latestPaymentStageSummary = latestPaymentRequest?.approval_status === "Pending"
    ? `Current approval: ${latestPaymentRequest.approval_stage_label || "Service Role"} (${latestPaymentRequest.approval_step || 1}/${latestPaymentRequest.approval_total_steps || 3}). Next: ${latestPaymentRequest.next_approver_role || latestPaymentRequest.approval_stage_label || "Service Role"}.`
    : latestPaymentRequest?.approval_status === "Approved"
      ? "Payment approval completed."
      : latestPaymentRequest?.approval_status === "Rejected"
        ? "Payment request rejected."
        : "Payment approval is pending.";
  const canRaisePayment = Boolean((roleIsEngineer || roleIsVendor || roleIsServiceTeam) && service?.status === "Service Completed");
  const canCancelPayment = Boolean((roleIsEngineer || roleIsVendor || roleIsServiceTeam) && paymentSubmitted);
  const canReopenToEngineer = Boolean(roleIsServiceTeam && ["Payment Completed", "Payment Requested", "Service Completed"].includes(service?.status));
  const paymentQrRequired = payment.payment_type === "UPI";

  if (err && !service) {
    return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  }
  if (!service) {
    return <div className="text-center text-slate-500">Loading...</div>;
  }

  const isServiceTeam = roleIsServiceTeam;
  const isEngineer = roleIsEngineer;
  const isVendor = roleIsVendor;
  const linkedCustomerSummary = [service.customer_name, service.customer_mobile, service.order_no].filter(Boolean).join(" • ");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/services" className="text-sm text-brand-600 hover:underline">Back to service requests</Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-2xl font-bold text-slate-900 sm:text-3xl">
            Service Request <span className="whitespace-nowrap font-mono text-lg text-slate-500">{service.request_no}</span>
            <StatusBadge value={service.status} />
          </h1>
          {(service.customer_mobile || service.customer_address) && (
            <div className="mt-2 flex gap-2 md:hidden">
              {service.customer_mobile && (
                <a href={`tel:${service.customer_mobile}`} className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2.5 text-center text-sm font-semibold text-indcool-navy">Call customer</a>
              )}
              {service.customer_address && (
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(service.customer_address)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2.5 text-center text-sm font-semibold text-indcool-navy"
                >
                  Open in Maps
                </a>
              )}
            </div>
          )}
          {service.complaint_id && (
            <p className="mt-2 text-sm text-slate-600">
              Linked complaint:{" "}
              <Link to={`/complaints/${service.complaint_id}`} className="font-mono text-brand-600 underline hover:text-brand-700">
                {service.complaint_no || `#${service.complaint_id}`}
              </Link>
            </p>
          )}
        </div>
      </div>

      {(canAssignServiceDesk || roleIsServiceDesk) && (
        <section className="rounded-lg border border-violet-200 bg-violet-50 p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-violet-900">Assignment (service desk)</h2>
          <p className="mt-1 text-xs text-violet-800">
            Assign this request to a Service user. Service users only see requests assigned to them.
          </p>
          <div className="mt-3 text-sm text-slate-800">
            <span className="font-medium text-slate-600">Currently assigned:</span>{" "}
            {service.assigned_service_user_name || "Unassigned"}
          </div>
          {canAssignServiceDesk && (
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_2fr_auto]">
              <select
                value={serviceDeskAssignForm.service_user_id}
                onChange={(e) => setServiceDeskAssignForm((current) => ({ ...current, service_user_id: e.target.value }))}
                className="rounded-md border border-violet-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Select service user</option>
                {serviceUsers.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} ({option.email})
                  </option>
                ))}
              </select>
              <input
                value={serviceDeskAssignForm.remarks}
                onChange={(e) => setServiceDeskAssignForm((current) => ({ ...current, remarks: e.target.value }))}
                placeholder="Assignment remarks (optional)"
                className="rounded-md border border-violet-300 bg-white px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={busy || !serviceDeskAssignForm.service_user_id}
                onClick={() => run(
                  () => servicesApi.assignServiceUser(service.id, {
                    service_user_id: Number(serviceDeskAssignForm.service_user_id),
                    remarks: serviceDeskAssignForm.remarks || null,
                  }),
                  { successMessage: "Service user assigned." },
                )}
                className="rounded-md bg-violet-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Assign service user
              </button>
            </div>
          )}
          {roleIsServiceDesk && service.assigned_service_user_id === user?.id && (
            <div className="mt-3 flex flex-wrap items-end gap-2">
              <input
                value={returnToManagerRemarks}
                onChange={(e) => setReturnToManagerRemarks(e.target.value)}
                placeholder="Reason for returning to manager (optional)"
                className="min-w-[240px] flex-1 rounded-md border border-violet-300 bg-white px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => run(
                  () => servicesApi.returnToServiceManager(service.id, { remarks: returnToManagerRemarks || null }),
                  { successMessage: "Request returned to Service Manager." },
                )}
                className="rounded-md border border-violet-400 bg-white px-4 py-2 text-sm text-violet-900 disabled:opacity-50"
              >
                Return to service manager
              </button>
            </div>
          )}
        </section>
      )}

      {canEditWorkflow && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <div className="text-sm font-semibold text-amber-900">Admin workflow control</div>
          <p className="mt-1 text-xs text-amber-800">
            Update step clears later work from the selected step onward (order verify, assignment, engineer steps). Customer documents are kept. Use the current step to restart from here.
          </p>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_2fr_auto]">
            <select
              value={workflowStatus || service.status}
              onChange={(event) => setWorkflowStatus(event.target.value)}
              className="rounded-md border border-amber-300 bg-white px-3 py-2 text-sm"
            >
              {SERVICE_STATUSES.map((statusOption) => (
                <option key={statusOption} value={statusOption}>
                  {statusOption === "Serial Verification Review" ? "Waiting for Admin Approval" : statusOption}
                </option>
              ))}
            </select>
            <input
              value={workflowRemarks}
              onChange={(event) => setWorkflowRemarks(event.target.value)}
              placeholder="Reason for changing workflow step"
              className="rounded-md border border-amber-300 bg-white px-3 py-2 text-sm"
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                const step = workflowStatus || service.status;
                const sameStep = step === service.status;
                if (sameStep && !window.confirm(
                  `Clear later steps and restart from "${step}"? Customer documents will stay on file.`,
                )) {
                  return;
                }
                const body = new FormData();
                body.append("new_status", step);
                if (workflowRemarks.trim()) body.append("remarks", workflowRemarks.trim());
                run(
                  () => servicesApi.updateStatus(service.id, body),
                  {
                    successMessage: sameStep
                      ? `Workflow reset from ${step}. Continue step by step from here.`
                      : "Workflow step updated.",
                  },
                );
              }}
              className="rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Update step
            </button>
          </div>
        </section>
      )}

      {canCloseServiceRequest && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          All serials have completed payment. You can now close this service request.
        </div>
      )}

      {service.status === "Closed" && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          This service request is closed
          {service.closed_at ? ` on ${new Date(service.closed_at).toLocaleString()}` : ""}.
        </div>
      )}

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {successMsg && <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMsg}</div>}

      {service.email_bounced && (
        <BounceBanner email={service.customer_email} reason={service.email_bounce_reason} />
      )}

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Request details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field label="Customer" value={service.customer_name} />
          <Field label="Mobile" value={service.customer_mobile} />
          <Field label="Email" value={service.customer_email} />
          <Field label="Address" value={service.customer_address} />
          <Field label="Model" value={service.model_details} />
          <Field label="Order No" value={service.order_no} />
          <Field label="Serial" value={service.serial_no} />
          <Field label="Warranty" value={service.warranty_status} />
          <Field label="Service Type" value={service.service_type} />
          <Field label="Service user" value={service.assigned_service_user_name} />
          <Field label="Engineer" value={assignedEngineerDisplay} />
          <Field label="Vendor" value={service.assigned_vendor_name} />
          {isServiceTeam && service.completion_code ? (
            <Field label="Happy Code (sent to customer)" value={service.completion_code} />
          ) : null}
          {isServiceTeam && latestCompletion?.engineer_completion_code ? (
            <Field label="Happy Code (entered by engineer)" value={latestCompletion.engineer_completion_code} />
          ) : null}
          {isServiceTeam && (service.completions || []).filter((c) => c.engineer_completion_code).length > 1 && (
            <div className="md:col-span-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">Happy codes by completion</div>
              <ul className="mt-1 space-y-1 text-sm text-slate-800">
                {(service.completions || [])
                  .filter((c) => c.engineer_completion_code)
                  .map((c) => (
                    <li key={c.id}>
                      <span className="font-mono font-semibold">{c.engineer_completion_code}</span>
                      {c.completed_at ? ` — ${new Date(c.completed_at).toLocaleString()}` : ""}
                    </li>
                  ))}
              </ul>
            </div>
          )}
          <Field label="Document Request Sent" value={service.document_request_sent_at ? new Date(service.document_request_sent_at).toLocaleString() : "Not sent"} />
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="Problem Description" value={service.problem_description} />
          <Field label="Additional Remarks" value={service.additional_remarks} />
        </div>
      </section>

      {isServiceTeam && (
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-medium text-slate-700">
            {isServiceTeam ? "Customer document upload" : "Customer documents"}
          </h2>
          {isServiceTeam && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="font-medium">Status</div>
              <div className="mt-1">
                {service.documents.some((document) => document.uploaded_by_type === "customer")
                  ? "Documents received"
                  : service.document_request_sent_at
                    ? "Awaiting customer docs"
                    : "Upload link not sent"}
              </div>
              {customerUploadUrl ? (
                <a href={customerUploadUrl} target="_blank" rel="noreferrer" className="mt-3 block break-all text-sky-700 underline">
                  {customerUploadUrl}
                </a>
              ) : (
                <div className="mt-3 text-xs text-amber-800">
                  No upload link yet. Use <strong>Open customer upload page</strong> to create one, or email the link to the customer.
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={openCustomerUploadPage}
                  disabled={busy}
                  className="rounded-md border border-sky-300 bg-white px-3 py-2 text-xs font-medium text-sky-800 disabled:opacity-50"
                >
                  Open upload page
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const warn = service.email_bounced ? `The last email to ${service.customer_email} BOUNCED. Please correct the email address first.\n\n` : "";
                    if (!window.confirm(`${warn}Are you sure you want to send the email again?`)) return;
                    run(
                      () => servicesApi.resendDocuments(service.id),
                      { successMessage: `Upload link email resent to ${service.customer_email || "customer"}.` },
                    );
                  }}
                  disabled={busy || !service.customer_email}
                  className={`rounded-md px-3 py-2 text-xs font-medium text-white disabled:opacity-50 ${service.email_bounced ? "border " + BOUNCED_BUTTON : "bg-sky-700"}`}
                >
                  {service.email_bounced ? "Email bounced - fix & resend" : "Resend email to customer"}
                </button>
              </div>
            </div>
          )}
          <div className={`space-y-3 ${isServiceTeam ? "mt-4" : ""}`}>
            {latestDocuments.length === 0 && <div className="text-sm text-slate-400">No customer documents uploaded yet.</div>}
            {latestDocuments.map((document) => (
              <div key={document.id} className="rounded-md border border-slate-200 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{document.document_type}</div>
                    <div className="text-xs text-slate-500">{document.uploaded_by_type} • {new Date(document.uploaded_at).toLocaleString()}</div>
                    <a href={toDownloadUrl(document.file_path)} download target="_blank" rel="noreferrer" className="mt-1 block text-xs text-sky-700 underline">
                      View / download document
                    </a>
                  </div>
                  <div className="space-y-2 text-right">
                    <StatusBadge value={document.status} />
                    {isServiceTeam && !["Reviewed", "Approved", "Rejected"].includes(document.status) && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => run(
                            () => servicesApi.reviewDocument(service.id, document.id, { status: "Reviewed", remarks: "Approved" }),
                            { successMessage: "Document approved. You can now verify the order and assign units." },
                          )}
                          className="rounded-md border border-emerald-300 px-2 py-1 text-xs text-emerald-700"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => run(
                            () => servicesApi.reviewDocument(service.id, document.id, { status: "Rejected", remarks: "Rejected" }),
                            { successMessage: "Document rejected." },
                          )}
                          className="rounded-md border border-rose-300 px-2 py-1 text-xs text-rose-700"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {(isServiceTeam || (roleIsEngineer && engineerWorkUnits.length > 0)) && (
        <ServiceUnitAssignmentPanel
          service={service}
          engineers={engineers}
          isServiceTeam={isServiceTeam}
          isEngineer={isEngineer}
          onRefresh={load}
          run={run}
          workflowUnlocked={documentsWorkflowUnlocked}
          pendingOrderVerifyNo={pendingOrderVerifyNo}
          onServiceUpdated={setService}
          parentBusy={busy}
        />
      )}

      {(isServiceTeam || canCancelAssignment) && (
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-medium text-slate-700">Customer and assignment workflow</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            {isServiceTeam && <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">Link existing customer/order</div>
              <input value={customerSearch} onChange={(e) => setCustomerSearch(e.target.value)} placeholder="Search by mobile, customer, or order no" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                Linked: {linkedCustomerSummary || "Not linked yet"}
              </div>
              <div className="max-h-48 space-y-2 overflow-auto rounded-md border border-slate-200 p-2">
                {customerOptions.length === 0 && <div className="text-sm text-slate-400">No search results yet.</div>}
                {customerOptions.map((option) => (
                  <button
                    key={`${option.source_type || "result"}-${option.order_id || option.customer_mobile || option.customer_name}`}
                    type="button"
                    onClick={() => run(async () => {
                      await servicesApi.identifyCustomer(service.id, {
                        order_id: option.order_id || null,
                        customer_name: option.customer_name || null,
                        customer_mobile: option.customer_mobile || null,
                        customer_email: option.customer_email || null,
                        customer_address: option.customer_address || null,
                      });
                      setSelectedCustomerKey(`${option.source_type || "result"}-${option.order_id || option.customer_mobile || option.customer_name}`);
                      setCustomerSearch(option.customer_name || option.customer_mobile || "");
                      setCustomerOptions([]);
                      if (option.order_no) {
                        setPendingOrderVerifyNo(option.order_no);
                      }
                      return {
                        successMessage: option.order_no
                          ? `Customer linked. Click Verify Order for ${option.order_no} to load installed units.`
                          : "Customer linked. Enter an order number and click Verify Order.",
                      };
                    })}
                    className={`block w-full rounded-md border px-3 py-2 text-left text-sm hover:bg-sky-50 ${selectedCustomerKey === `${option.source_type || "result"}-${option.order_id || option.customer_mobile || option.customer_name}` ? "border-emerald-400 bg-emerald-50" : "border-slate-200"}`}
                  >
                    <div className="font-medium text-slate-800">{option.customer_name}</div>
                    <div className="text-slate-500">{option.order_no} • {option.customer_mobile}</div>
                  </button>
                ))}
              </div>
            </div>}

            <div className="space-y-3">
              {usePerUnitAssignment ? (
                <>
                  <div className="text-sm font-medium text-slate-700">Unit assignment</div>
                  <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-3 text-sm text-sky-900">
                    <p>
                      This order uses <strong>per-serial assignment</strong>.
                      {roleIsEngineer
                        ? (
                          <>
                            {" "}
                            Add each serial in the <strong>Serial workflow (per unit)</strong> section below — that
                            assigns the unit to you and starts verify → service steps.
                          </>
                        )
                        : (
                          <>
                            {" "}
                            Assign engineers in the <strong>Order verify &amp; unit assignment</strong> section above,
                            or engineers can add serials from the workflow section below.
                          </>
                        )}
                    </p>
                    {unitAssignmentSummary && (
                      <div className="mt-3 space-y-1">
                        {unitAssignmentSummary.assigned.map((row) => (
                          <div key={row.name}>
                            <span className="font-medium">{row.name}</span>
                            {" — "}
                            {row.count} unit{row.count === 1 ? "" : "s"} assigned
                          </div>
                        ))}
                        {unitAssignmentSummary.unassigned > 0 && (
                          <div className="text-amber-800">
                            {unitAssignmentSummary.unassigned} unit{unitAssignmentSummary.unassigned === 1 ? "" : "s"} still unassigned
                          </div>
                        )}
                        {unitAssignmentSummary.assigned.length === 0 && unitAssignmentSummary.unassigned > 0 && (
                          <div className="text-amber-800">No units assigned yet.</div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="text-sm font-medium text-slate-700">Assign engineer</div>
                  {assignmentLocked && (
                    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                      This request is already assigned to engineer {activeAssignment.assignee_user_name || "assigned user"}.
                      Cancel the current assignment before assigning again, or ask an admin to reset the workflow from this step.
                    </div>
                  )}
                  {roleCanViewAllServices && <>
                    <select value={assignForm.assignee_id} onChange={(e) => setAssignForm((current) => ({ ...current, assignee_id: e.target.value }))} disabled={assignmentLocked} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500">
                      <option value="">Select engineer</option>
                      {activeAssigneeOptions.map((option) => (
                        <option key={option.id} value={option.id}>{formatEngineerOptionLabel(option)}</option>
                      ))}
                    </select>
                    <p className="text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
                    <textarea value={assignForm.remarks} onChange={(e) => setAssignForm((current) => ({ ...current, remarks: e.target.value }))} disabled={assignmentLocked} rows={3} placeholder="Assignment remarks" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
                    <button
                      onClick={() => {
                        const selectedAssignee = activeAssigneeOptions.find((option) => String(option.id) === String(assignForm.assignee_id));
                        const assigneeLabel = selectedAssignee?.name || "selected assignee";
                        run(
                          () => servicesApi.assign(service.id, { ...assignForm, assignee_type: "engineer", assignee_id: Number(assignForm.assignee_id) }),
                          { successMessage: `Service request assigned to engineer ${assigneeLabel}.` },
                        );
                      }}
                      disabled={busy || !assignForm.assignee_id || assignmentLocked}
                      className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                    >
                      Assign
                    </button>
                  </>}
                  {canCancelAssignment && (
                    <button
                      onClick={() => setCancelAssignmentOpen(true)}
                      disabled={busy}
                      className="ml-2 rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
                    >
                      Cancel Assignment
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </section>
      )}

      {useUnitWorkflow && (isEngineer || isVendor || isServiceTeam) && (
        <EngineerUnitWorkflowPanel
          service={service}
          userId={user?.id}
          isEngineer={isEngineer}
          isVendor={isVendor}
          isServiceTeam={isServiceTeam}
          isPaymentAdmin={roleIsPaymentAdmin}
          run={run}
          busy={busy}
          actionError={err}
        />
      )}

      {(isEngineer || isVendor || isServiceTeam) && !useUnitWorkflow && (
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-medium text-slate-700">Serial verification and engineer workflow</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">Verify product serial number</div>
              <ScanInput value={serialNo} onValue={setSerialNo} disabled={!canVerifySerial} placeholder="Scan or enter serial no" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <button
                onClick={() => run(
                  () => servicesApi.verifySerial(service.id, { serial_no: serialNo }),
                  { successMessage: `Serial number ${serialNo.trim()} verified successfully.` },
                )}
                disabled={busy || !serialNo.trim() || !canVerifySerial}
                className="rounded-md bg-sky-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Verify Serial
              </button>
              {isServiceTeam && service.serial_no && !["Payment Completed", "Closed"].includes(service.status) && (
                <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                  <span className="text-sm font-medium text-slate-700">Billing for this serial</span>
                  <select
                    value={service.service_type === "Paid Service" ? "Paid" : "Free"}
                    disabled={busy}
                    onChange={(e) => run(
                      () => servicesApi.setUnitBilling(service.id, { billing_type: e.target.value }),
                      { successMessage: `Billing updated to ${e.target.value}.` },
                    )}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                  >
                    <option value="Free">Free</option>
                    <option value="Paid">Paid</option>
                  </select>
                </div>
              )}
              {serialVerified && service.serial_no && (
                <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                  <div className="font-medium">
                    Verified serial: {service.serial_no}
                    {service.warranty_status ? ` | ${service.warranty_status}` : ""}
                    {service.service_type ? ` | ${service.service_type}` : ""}
                  </div>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <div>PCB warranty: {formatDate(serialInfo?.pcb_warranty_date)}</div>
                    <div>Component warranty: {formatDate(serialInfo?.component_warranty_date)}</div>
                    <div>Machine warranty: {formatDate(serialInfo?.machine_warranty_date)}</div>
                    <div>
                      Free service pending: {Math.max((serialInfo?.free_service_count || 0) - (serialInfo?.service_consume_count || 0), 0)}
                      {" "}of {serialInfo?.free_service_count ?? 0}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">Observation / diagnosis</div>
              {observationSubmitted && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Observation submitted and pending service approval.
                  {latestObservation?.problem_found ? ` Problem: ${latestObservation.problem_found}.` : ""}
                </div>
              )}
              {!canSubmitObservation && !observationSubmitted && (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Observation unlocks after serial verification.
                </div>
              )}
              <input value={observation.problem_found} onChange={(e) => setObservation((current) => ({ ...current, problem_found: e.target.value }))} disabled={!canSubmitObservation} placeholder="Problem found" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <textarea value={observation.observation} onChange={(e) => setObservation((current) => ({ ...current, observation: e.target.value }))} disabled={!canSubmitObservation} rows={2} placeholder="Engineer observation" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <textarea value={observation.recommended_action} onChange={(e) => setObservation((current) => ({ ...current, recommended_action: e.target.value }))} disabled={!canSubmitObservation} rows={2} placeholder="Recommended action" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <input value={observation.parts_required} onChange={(e) => setObservation((current) => ({ ...current, parts_required: e.target.value }))} disabled={!canSubmitObservation} placeholder="Parts required (comma separated)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <div className="grid grid-cols-2 gap-3">
                <input value={observation.estimated_service_charge} onChange={(e) => setObservation((current) => ({ ...current, estimated_service_charge: e.target.value }))} disabled={!canSubmitObservation} placeholder="Estimated service charge" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
                <input value={observation.estimated_parts_charge} onChange={(e) => setObservation((current) => ({ ...current, estimated_parts_charge: e.target.value }))} disabled={!canSubmitObservation} placeholder="Estimated parts charge" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              </div>
              <textarea value={observation.remarks} onChange={(e) => setObservation((current) => ({ ...current, remarks: e.target.value }))} disabled={!canSubmitObservation} rows={2} placeholder="Remarks" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <button
                onClick={() => run(
                  () => servicesApi.submitObservation(service.id, {
                    ...observation,
                    parts_required: observation.parts_required ? observation.parts_required.split(",").map((item) => item.trim()).filter(Boolean) : [],
                    estimated_service_charge: observation.estimated_service_charge ? Number(observation.estimated_service_charge) : null,
                    estimated_parts_charge: observation.estimated_parts_charge ? Number(observation.estimated_parts_charge) : null,
                  }),
                  { successMessage: "Observation submitted successfully and sent for service approval." },
                )}
                disabled={busy || !canSubmitObservation}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Submit Observation
              </button>
              {canCancelObservation && (
                <button
                  onClick={() => setCancelObservationOpen(true)}
                  disabled={busy}
                  className="ml-2 rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
                >
                  Cancel Observation
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {isServiceTeam && !useUnitWorkflow && (
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-medium text-slate-700">Approval</h2>
          {!approvalPending && !approvalCompleted && (
            <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
              Approval unlocks after engineer observation is submitted.
            </div>
          )}
          {approvalCompleted && (
            <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Approval decision submitted: {service.status}. Cancel approval if you need to change it.
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
            <select value={approval.decision} onChange={(e) => setApproval((current) => ({ ...current, decision: e.target.value }))} disabled={!approvalPending} className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500">
              <option value="Approve">Approve</option>
              <option value="Reject">Reject / Send Back</option>
            </select>
            <textarea value={approval.remarks} onChange={(e) => setApproval((current) => ({ ...current, remarks: e.target.value }))} disabled={!approvalPending} rows={2} placeholder="Approval remarks" className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
            <button
              onClick={() => run(
                () => servicesApi.approve(service.id, approval),
                { successMessage: approval.decision === "Approve" ? "Service approval submitted successfully." : "Service rejection submitted successfully." },
              )}
              disabled={busy || !approvalPending}
              className="rounded-md bg-orange-500 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Submit Decision
            </button>
          </div>
          {canCancelApproval && (
            <button
              onClick={() => setCancelApprovalOpen(true)}
              disabled={busy}
              className="mt-3 rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
            >
              Cancel Approval
            </button>
          )}
        </section>
      )}

      {isServiceTeam && !useUnitWorkflow && completionPendingApproval && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold text-amber-900">Completion approval</h2>
          <p className="mb-4 text-sm text-amber-800">
            The engineer submitted completion with proof. Approve to move to Service Completed (engineer can then raise payment), or reject to send back.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                const remarks = window.prompt("Approval remarks (optional):", "");
                if (remarks === null) return;
                run(
                  () => servicesApi.reviewCompletion(service.id, { decision: "Approve", remarks }),
                  { successMessage: "Completion approved. Engineer can raise payment request." },
                );
              }}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Approve completion
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                const remarks = window.prompt("Rejection remarks (optional):", "");
                if (remarks === null) return;
                run(
                  () => servicesApi.reviewCompletion(service.id, { decision: "Reject", remarks }),
                  { successMessage: "Completion rejected. Engineer can edit and resubmit." },
                );
              }}
              className="rounded-md border border-rose-300 bg-white px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
            >
              Reject completion
            </button>
          </div>
        </section>
      )}

      {(isEngineer || isVendor || isServiceTeam) && !useUnitWorkflow && (
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-medium text-slate-700">Completion and payment</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3">
              {completionPendingApproval && (isEngineer || isVendor) && (
                <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  <div className="font-medium">Waiting for INDcool/Admin completion approval</div>
                  <p className="mt-1 text-amber-800">
                    Your completion and proof are saved. An admin must approve before status becomes Service Completed and you can raise payment.
                  </p>
                </div>
              )}
              {completionSubmitted && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  {completionPendingApproval
                    ? "Completion is pending admin approval."
                    : "Service completion submitted. Cancel completion if you need to edit it."}
                  {isServiceTeam && latestCompletion?.engineer_completion_code && (
                    <div className="mt-1">
                      Happy code entered by engineer:{" "}
                      <span className="font-mono font-semibold">{latestCompletion.engineer_completion_code}</span>
                      {service.completion_code && (
                        <span className="ml-2 text-xs">
                          ({latestCompletion.engineer_completion_code === service.completion_code ? "matches customer code" : "does not match customer code"})
                        </span>
                      )}
                    </div>
                  )}
                  {latestCompletion?.customer_acknowledgement_path && (
                    <a href={toDownloadUrl(latestCompletion.customer_acknowledgement_path)} download target="_blank" rel="noreferrer" className="mt-1 block text-sky-700 underline">
                      Download completion proof
                    </a>
                  )}
                </div>
              )}
              {completionBlockedHint && (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  {completionBlockedHint}
                </div>
              )}
              <input value={completion.work_performed} onChange={(e) => setCompletion((current) => ({ ...current, work_performed: e.target.value }))} disabled={!canCompleteService} placeholder="Work performed" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <input value={completion.parts_replaced} onChange={(e) => setCompletion((current) => ({ ...current, parts_replaced: e.target.value }))} disabled={!canCompleteService} placeholder="Parts replaced (comma separated)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <textarea value={completion.service_notes} onChange={(e) => setCompletion((current) => ({ ...current, service_notes: e.target.value }))} disabled={!canCompleteService} rows={2} placeholder="Service notes" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <div className="grid grid-cols-2 gap-3">
                <input type="date" value={completion.service_date} onChange={(e) => setCompletion((current) => ({ ...current, service_date: e.target.value }))} disabled={!canCompleteService} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
                <input value={completion.final_amount} onChange={(e) => setCompletion((current) => ({ ...current, final_amount: e.target.value }))} disabled={!canCompleteService} placeholder="Final amount" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Completion proof document <span className="text-rose-600">*</span></label>
                {latestCompletion?.customer_acknowledgement_path && (
                  <div className="mb-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                    Saved proof:{" "}
                    <a href={toDownloadUrl(latestCompletion.customer_acknowledgement_path)} download target="_blank" rel="noreferrer" className="font-medium text-sky-700 underline">
                      {fileNameFromPath(latestCompletion.customer_acknowledgement_path)}
                    </a>
                  </div>
                )}
                <input type="file" onChange={(e) => setCompletionProof(e.target.files?.[0] || null)} disabled={!canCompleteService} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
                <p className="mt-1 text-xs text-slate-500">Required before marking service completed.</p>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Completion code (Happy code) <span className="text-rose-600">*</span>
                </label>
                <input
                  value={completion.completion_code}
                  onChange={(e) => setCompletion((current) => ({ ...current, completion_code: e.target.value }))}
                  disabled={!canCompleteService}
                  placeholder="Enter code shared by customer"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Ask the customer for the completion code sent by SMS/email when the engineer was assigned.
                </p>
              </div>
              <textarea value={completion.completion_remarks} onChange={(e) => setCompletion((current) => ({ ...current, completion_remarks: e.target.value }))} disabled={!canCompleteService} rows={2} placeholder="Completion remarks" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <button
                onClick={() => run(
                  () => {
                    const formData = new FormData();
                    formData.append("work_performed", completion.work_performed);
                    formData.append("parts_replaced", JSON.stringify(completion.parts_replaced ? completion.parts_replaced.split(",").map((item) => item.trim()).filter(Boolean) : []));
                    formData.append("service_notes", completion.service_notes);
                    if (completion.service_date) formData.append("service_date", completion.service_date);
                    if (completion.final_amount) formData.append("final_amount", completion.final_amount);
                    formData.append("completion_remarks", completion.completion_remarks);
                    formData.append("completion_code", completion.completion_code);
                    formData.append("proof_document", completionProof);
                    return servicesApi.complete(service.id, formData);
                  },
                  { successMessage: "Service completion submitted successfully." },
                )}
                disabled={busy || !canCompleteService || !completionProof || !completion.completion_code.trim()}
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Mark Service Completed
              </button>
              {canCancelCompletion && (
                <button
                  onClick={() => setCancelCompletionOpen(true)}
                  disabled={busy}
                  className="ml-2 rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
                >
                  Cancel Completion
                </button>
              )}
            </div>

            <div className="space-y-3">
              {isServiceTeam && latestPaymentRequest?.payment_qr_code_path && latestPaymentRequest?.payment_type === "UPI" && (
                <PaymentQrPanel path={latestPaymentRequest.payment_qr_code_path} />
              )}
              {paymentSubmitted && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Payment request submitted. Cancel payment request if you need to edit it.
                  {latestPaymentRequest?.payment_type && (
                    <div className="mt-1">Payment type: {latestPaymentRequest.payment_type}</div>
                  )}
                </div>
              )}
              {canApprovePayment && (
                <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                  <div>
                    <div className="text-sm font-semibold text-emerald-900">
                      {latestPaymentRequest?.approval_stage_label || "Payment"} approval
                    </div>
                    <p className="mt-1 text-xs text-emerald-800">
                      {latestPaymentStageSummary} Only final Admin approval marks payment done.
                    </p>
                  </div>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={paymentApproval.approved_amount}
                    onChange={(e) => setPaymentApproval((current) => ({ ...current, approved_amount: e.target.value }))}
                    placeholder="Approved payment amount"
                    className="w-full rounded-md border border-emerald-300 px-3 py-2 text-sm"
                  />
                  <textarea
                    value={paymentApproval.remarks}
                    onChange={(e) => setPaymentApproval((current) => ({ ...current, remarks: e.target.value }))}
                    rows={2}
                    placeholder="Admin payment approval remarks"
                    className="w-full rounded-md border border-emerald-300 px-3 py-2 text-sm"
                  />
                  {latestPaymentProofRequired && (
                    <div>
                      <label className="mb-1 block text-sm font-medium text-emerald-900">
                        Payment proof document <span className="text-rose-600">*</span>
                      </label>
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                        onChange={(e) => setPaymentApproval((current) => ({ ...current, proof_document: e.target.files?.[0] || null }))}
                        className="block w-full text-sm"
                      />
                      <p className="mt-1 text-xs text-emerald-800">Only final Admin approval requires the actual payment proof.</p>
                    </div>
                  )}
                  <button
                    onClick={() => run(
                      () => {
                        if (latestPaymentProofRequired && !paymentApproval.proof_document && !latestPaymentRequest?.payment_proof_file_path) {
                          throw new Error("Upload Payment Proof / Document is required when payment type is UPI");
                        }
                        return servicesApi.approvePayment(service.id, {
                          approved_amount: Number(paymentApproval.approved_amount),
                          payment_type: latestPaymentRequest?.payment_type || payment.payment_type,
                          remarks: paymentApproval.remarks,
                          proof_document: paymentApproval.proof_document,
                        });
                      },
                      { successMessage: latestPaymentFinalStage ? "Payment approved and added to payment history." : "Payment stage approved and forwarded." },
                    )}
                    disabled={busy || paymentApproval.approved_amount === ""}
                    className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50"
                  >
                    {latestPaymentFinalStage ? "Approve Payment" : "Approve Stage"}
                  </button>
                </div>
              )}
              {paymentCompleted && latestPaymentRequest && (
                <div className="space-y-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800">
                  <div>
                    Payment approved: {formatMoneyInput(latestPaymentRequest.approved_amount)} by {latestPaymentRequest.processed_by_name || "admin"}.
                    This is now available in Payment History.
                  </div>
                  {roleIsAdminLike && (
                    <button
                      onClick={() => run(
                        () => servicesApi.updatePaymentAmount(service.id, {
                          approved_amount: Number(paymentApproval.approved_amount),
                          payment_type: latestPaymentRequest?.payment_type || payment.payment_type,
                          remarks: paymentApproval.remarks,
                        }),
                        { successMessage: "Approved payment amount updated." },
                      )}
                      disabled={busy || paymentApproval.approved_amount === ""}
                      className="rounded-md border border-emerald-400 bg-white px-4 py-2 text-sm text-emerald-900 disabled:opacity-50"
                    >
                      Update approved amount
                    </button>
                  )}
                  {isServiceTeam && (
                    <div className="flex flex-wrap gap-2">
                      {canCloseServiceRequest && (
                        <button
                          onClick={() => setCloseServiceOpen(true)}
                          disabled={busy}
                          className="rounded-md bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-50"
                        >
                          Mark Service Request Closed
                        </button>
                      )}
                      {canReopenToEngineer && (
                        <button
                          onClick={() => setReopenEngineerOpen(true)}
                          disabled={busy}
                          className="rounded-md border border-amber-400 bg-white px-4 py-2 text-sm text-amber-900 disabled:opacity-50"
                        >
                          Reopen to Engineer
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
              {!canRaisePayment && !paymentSubmitted && !paymentCompleted && (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Payment request unlocks after service completion.
                </div>
              )}
              <input value={payment.customer_charge_amount} onChange={(e) => setPayment((current) => ({ ...current, customer_charge_amount: e.target.value }))} disabled={!canRaisePayment} placeholder="Customer charge amount" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <input value={payment.settlement_service_amount} onChange={(e) => setPayment((current) => ({ ...current, settlement_service_amount: e.target.value }))} disabled={!canRaisePayment} placeholder="Settlement service amount" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <input value={payment.settlement_parts_amount} onChange={(e) => setPayment((current) => ({ ...current, settlement_parts_amount: e.target.value }))} disabled={!canRaisePayment} placeholder="Settlement parts amount" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <input value={payment.total_requested_amount} onChange={(e) => setPayment((current) => ({ ...current, total_requested_amount: e.target.value }))} disabled={!canRaisePayment} placeholder="Total requested amount" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <select value={payment.payment_type} onChange={(e) => setPayment((current) => ({ ...current, payment_type: e.target.value }))} disabled={!canRaisePayment} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500">
                {PAYMENT_TYPES.map((paymentType) => <option key={paymentType} value={paymentType}>{paymentType}</option>)}
              </select>
              {paymentQrRequired && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">QR Code <span className="text-rose-600">*</span></label>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => setPaymentQrCode(e.target.files?.[0] || null)}
                    disabled={!canRaisePayment}
                    className="block w-full text-sm disabled:opacity-50"
                  />
                  <p className="mt-1 text-xs text-slate-500">Required when payment type is UPI. Admin can view this QR after submission.</p>
                </div>
              )}
              <textarea value={payment.remarks} onChange={(e) => setPayment((current) => ({ ...current, remarks: e.target.value }))} disabled={!canRaisePayment} rows={2} placeholder="Payment remarks" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500" />
              <button
                onClick={() => run(
                  () => {
                    const formData = new FormData();
                    if (payment.customer_charge_amount) formData.append("customer_charge_amount", payment.customer_charge_amount);
                    if (payment.settlement_service_amount) formData.append("settlement_service_amount", payment.settlement_service_amount);
                    if (payment.settlement_parts_amount) formData.append("settlement_parts_amount", payment.settlement_parts_amount);
                    if (payment.total_requested_amount) formData.append("total_requested_amount", payment.total_requested_amount);
                    formData.append("payment_type", payment.payment_type);
                    formData.append("remarks", payment.remarks);
                    if (paymentQrCode) formData.append("qr_code", paymentQrCode);
                    return servicesApi.requestPayment(service.id, formData);
                  },
                  { successMessage: "Payment request submitted successfully." },
                )}
                disabled={busy || !canRaisePayment || (paymentQrRequired && !paymentQrCode)}
                className="rounded-md bg-slate-700 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Raise Payment Request
              </button>
              {canCancelPayment && (
                <button
                  onClick={() => setCancelPaymentOpen(true)}
                  disabled={busy}
                  className="ml-2 rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
                >
                  Cancel Payment Request
                </button>
              )}
            </div>
          </div>
        </section>
      )}
      {!isEngineer && (
        <section className="grid gap-5 xl:grid-cols-1">
          <div className="rounded-lg bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-medium text-slate-700">History</h2>
            <div className="space-y-3">
              {history.length === 0 && <div className="text-sm text-slate-400">No history entries yet.</div>}
              {history.map((entry) => (
                <div key={entry.id} className="rounded-md border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">{entry.action}</span>
                    {entry.new_status && <StatusBadge value={entry.new_status} />}
                    <span className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</span>
                    <span className="text-xs text-slate-500">by {entry.performed_by_name || entry.performed_role || "System"}</span>
                  </div>
                  {entry.remarks && <div className="mt-2 text-sm text-slate-700">{entry.remarks}</div>}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <UploadDocumentModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSubmit={(documentType, file) => run(async () => {
          const formData = new FormData();
          formData.append("document_type", documentType);
          formData.append("file", file);
          await servicesApi.uploadDocument(service.id, formData);
          setUploadOpen(false);
        })}
      />

      <Modal open={cancelAssignmentOpen} onClose={() => setCancelAssignmentOpen(false)} title="Cancel Assignment">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to cancel the current assignment? This will unlock the request so it can be assigned again.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setCancelAssignmentOpen(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Keep Assignment
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.cancelAssignment(service.id);
                  setCancelAssignmentOpen(false);
                },
                { successMessage: "Current assignment cancelled. You can assign this request again." },
              )}
              disabled={busy}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={cancelObservationOpen} onClose={() => setCancelObservationOpen(false)} title="Cancel Observation">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to cancel the submitted observation? This will unlock the observation form so it can be submitted again.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setCancelObservationOpen(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Keep Observation
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.cancelObservation(service.id);
                  setCancelObservationOpen(false);
                },
                { successMessage: "Observation cancelled. You can submit a new observation now." },
              )}
              disabled={busy}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={cancelApprovalOpen} onClose={() => setCancelApprovalOpen(false)} title="Cancel Approval">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to cancel this approval decision? This will send the request back to pending approval.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setCancelApprovalOpen(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Keep Approval
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.cancelApproval(service.id);
                  setCancelApprovalOpen(false);
                },
                { successMessage: "Approval cancelled. You can submit the decision again." },
              )}
              disabled={busy}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={cancelCompletionOpen} onClose={() => setCancelCompletionOpen(false)} title="Cancel Completion">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to cancel service completion? This will unlock the completion form again.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setCancelCompletionOpen(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Keep Completion
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.cancelCompletion(service.id);
                  setCancelCompletionOpen(false);
                },
                { successMessage: "Completion cancelled. You can submit completion again." },
              )}
              disabled={busy}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={cancelPaymentOpen} onClose={() => setCancelPaymentOpen(false)} title="Cancel Payment Request">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to cancel this payment request? This will unlock payment entry again.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setCancelPaymentOpen(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Keep Payment Request
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.cancelPaymentRequest(service.id);
                  setCancelPaymentOpen(false);
                },
                { successMessage: "Payment request cancelled. You can raise it again." },
              )}
              disabled={busy}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={closeServiceOpen} onClose={() => setCloseServiceOpen(false)} title="Close service request">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            All serials have reached payment completed. Close this service request to finish the workflow.
          </p>
          <textarea
            value={closeRemarks}
            onChange={(e) => setCloseRemarks(e.target.value)}
            rows={3}
            placeholder="Closing remarks (optional)"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setCloseServiceOpen(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Cancel
            </button>
            <button
              onClick={() => run(
                async () => {
                  await servicesApi.close(service.id, { remarks: closeRemarks || null });
                  setCloseServiceOpen(false);
                  setCloseRemarks("");
                },
                { successMessage: "Service request closed successfully." },
              )}
              disabled={busy}
              className="rounded-md bg-slate-800 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Mark closed
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={reopenEngineerOpen} onClose={() => setReopenEngineerOpen(false)} title="Reopen to engineer">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Send this service request back to the engineer for another visit based on customer feedback.
            Payment history is retained; the engineer can complete service again.
          </p>
          <textarea
            value={reopenRemarks}
            onChange={(e) => setReopenRemarks(e.target.value)}
            rows={3}
            placeholder="Reason for reopening (required)"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setReopenEngineerOpen(false)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Cancel
            </button>
            <button
              onClick={() => run(
                async () => {
                  const formData = new FormData();
                  formData.append("remarks", reopenRemarks);
                  await servicesApi.reopenToEngineer(service.id, formData);
                  setReopenEngineerOpen(false);
                  setReopenRemarks("");
                },
                { successMessage: "Service request reopened to engineer." },
              )}
              disabled={busy || !reopenRemarks.trim()}
              className="rounded-md bg-amber-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Reopen to engineer
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
