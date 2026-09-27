import { useEffect, useMemo, useState } from "react";

import { servicesApi } from "../../api/services.js";
import { engineerIdsMatch } from "../../utils/engineerAssignment.js";
import Modal from "../../components/Modal.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";

const PAYMENT_TYPES = ["Cash", "UPI"];
const BILLING_LOCKED_STATUSES = ["Payment Completed", "Closed"];

function unitBillingValue(unit) {
  if (unit?.admin_billing_type === "Paid" || unit?.admin_billing_type === "Free") {
    return unit.admin_billing_type;
  }
  return unit?.service_type === "Paid Service" ? "Paid" : "Free";
}

function unitBillingLocked(unit) {
  return BILLING_LOCKED_STATUSES.includes(unit?.unit_status || "");
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

function isImagePath(path) {
  return /\.(png|jpe?g|gif|webp)$/i.test(path || "");
}

function AttachmentPreview({ title, path, description }) {
  if (!path) {
    return null;
  }
  const url = toDownloadUrl(path);
  const image = isImagePath(path);
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="text-sm font-medium text-slate-800">{title}</div>
      {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
      {image && (
        <img
          src={url}
          alt={title}
          className="mt-2 max-h-72 w-full rounded border border-slate-200 bg-white object-contain"
        />
      )}
      <a
        href={url}
        download
        target="_blank"
        rel="noreferrer"
        className="mt-2 inline-block text-sm font-medium text-sky-700 underline"
      >
        {image ? "Download image" : `Download ${fileNameFromPath(path)}`}
      </a>
    </div>
  );
}

function emptyRow(unit) {
  return {
    unit_id: unit.id,
    problem_found: unit.problem_found || "",
    observation: unit.observation_text || "",
    recommended_action: unit.recommended_action || "",
    parts_required: (unit.parts_required || []).join(", "),
    estimated_service_charge: unit.estimated_service_charge ?? "",
    estimated_parts_charge: unit.estimated_parts_charge ?? "",
    remarks: unit.observation_remarks || "",
  };
}

function emptyCompletion(unit) {
  const partsReplaced = Array.isArray(unit.parts_replaced)
    ? unit.parts_replaced.join(", ")
    : (unit.parts_replaced || "");
  return {
    work_performed: unit.work_performed || "",
    parts_replaced: partsReplaced,
    service_notes: unit.service_notes || "",
    service_date: unit.service_date ? String(unit.service_date).slice(0, 10) : "",
    final_amount: unit.final_amount ?? "",
    completion_remarks: unit.completion_remarks || "",
    completion_code: "",
    completion_status: ["Waiting for Part", "Customer Not Available"].includes(unit.unit_status)
      ? unit.unit_status
      : "Service Completed",
  };
}

function emptyPayment(unit) {
  return {
    customer_charge_amount: unit.customer_charge_amount ?? "",
    settlement_service_amount: unit.estimated_service_charge ?? unit.settlement_service_amount ?? "",
    settlement_parts_amount: unit.estimated_parts_charge ?? unit.settlement_parts_amount ?? "",
    total_requested_amount: unit.total_requested_amount ?? "",
    payment_type: unit.payment_type || "Cash",
    remarks: unit.payment_remarks || "",
  };
}

function FieldLabel({ children, required }) {
  return (
    <label className="mb-1 block text-sm font-medium text-slate-700">
      {children}
      {required && <span className="text-rose-600"> *</span>}
    </label>
  );
}

function inputClass(disabled = false) {
  return `w-full rounded-md border border-slate-300 px-3 py-2 text-sm ${disabled ? "bg-slate-100 text-slate-500" : ""}`;
}

function proofActionLink(unit, onOpen) {
  if (!unit?.completion_proof_path) {
    return null;
  }
  return (
    <button type="button" onClick={() => onOpen("serviceProof", unit.id)} className="text-xs text-sky-700 underline">
      View service proof
    </button>
  );
}

function WorkflowSteps({ unit }) {
  const steps = [
    { label: "Verify", done: Boolean(unit.serial_verified_at) },
    { label: "Observe", done: Boolean(unit.observation_id) },
    {
      label: "Complete",
      done: ["Service Completed", "Payment Requested", "Payment Completed"].includes(unit.unit_status),
    },
    {
      label: "Payment",
      done: ["Payment Requested", "Payment Completed", "Closed"].includes(unit.unit_status),
    },
  ];
  return (
    <div className="flex flex-col gap-0.5 text-xs">
      {steps.map((step) => (
        <span key={step.label} className={step.done ? "font-medium text-emerald-700" : "text-slate-400"}>
          {step.done ? "✓" : "○"} {step.label}
        </span>
      ))}
    </div>
  );
}

export default function EngineerUnitWorkflowPanel({
  service,
  userId,
  isEngineer,
  isVendor,
  isServiceTeam,
  run,
  busy = false,
  actionError = "",
}) {
  const workUnits = useMemo(() => {
    const units = service?.units || [];
    if (isEngineer) {
      return units.filter((unit) => engineerIdsMatch(unit.assigned_engineer_id, userId));
    }
    return units.filter((unit) => unit.assigned_engineer_id);
  }, [service?.units, isEngineer, userId]);

  const [rows, setRows] = useState([]);
  const [serialInputs, setSerialInputs] = useState({});
  const [completionRows, setCompletionRows] = useState({});
  const [paymentRows, setPaymentRows] = useState({});
  const [completionProofs, setCompletionProofs] = useState({});
  const [paymentQrCodes, setPaymentQrCodes] = useState({});
  const [approvalRemarks, setApprovalRemarks] = useState({});
  const [serialReviewForms, setSerialReviewForms] = useState({});
  const [paymentApprovalForms, setPaymentApprovalForms] = useState({});
  const [completionReviewRemarks, setCompletionReviewRemarks] = useState({});
  const [activeModal, setActiveModal] = useState(null);
  const [newVisitSerial, setNewVisitSerial] = useState("");

  useEffect(() => {
    setRows(workUnits.map((unit) => emptyRow(unit)));
    setSerialInputs(Object.fromEntries(workUnits.map((unit) => [unit.id, unit.serial_no || ""])));
    const completionMap = {};
    const paymentMap = {};
    const approvalMap = {};
    const paymentApprovalMap = {};
    workUnits.forEach((unit) => {
      completionMap[unit.id] = emptyCompletion(unit);
      paymentMap[unit.id] = emptyPayment(unit);
      approvalMap[unit.id] = "";
      paymentApprovalMap[unit.id] = {
        approved_amount: String(unit.total_requested_amount || unit.estimated_service_charge || ""),
        remarks: "",
      };
    });
    setCompletionRows(completionMap);
    setPaymentRows(paymentMap);
    setApprovalRemarks(approvalMap);
    setPaymentApprovalForms(paymentApprovalMap);
  }, [workUnits]);

  const canVerifyOrObserve = Boolean(
    (isEngineer || isVendor || isServiceTeam)
    && workUnits.length > 0
    && ["Assigned", "Engineer Visit", "Serial Verified", "Pending Service Approval", "Service In Progress"].includes(service?.status),
  );

  const unverifiedUnits = workUnits.filter((unit) => !unit.serial_verified_at && unit.unit_status === "Assigned");
  const unitsNeedingObservation = workUnits.filter((unit) => unit.serial_verified_at && !unit.observation_id);
  const unitsPendingApproval = workUnits.filter((unit) => unit.unit_status === "Pending Service Approval");
  const unitsAwaitingSerialReview = workUnits.filter(
    (unit) => unit.unit_status === "Serial Verification Pending",
  );
  const unitsWithUnknownSerial = unitsAwaitingSerialReview.filter((unit) => unit.serial_not_in_order);

  function closeModal() {
    setActiveModal(null);
  }

  function openModal(type, unitId) {
    setActiveModal({ type, unitId });
  }

  function activeUnit() {
    if (!activeModal) return null;
    return workUnits.find((unit) => unit.id === activeModal.unitId) || null;
  }

  function updateRow(unitId, field, value) {
    setRows((current) => current.map((row) => (
      row.unit_id === unitId ? { ...row, [field]: value } : row
    )));
  }

  function updateCompletion(unitId, field, value) {
    setCompletionRows((current) => ({
      ...current,
      [unitId]: { ...current[unitId], [field]: value },
    }));
  }

  function updatePayment(unitId, field, value) {
    setPaymentRows((current) => ({
      ...current,
      [unitId]: { ...current[unitId], [field]: value },
    }));
  }

  async function verifyOne(unit) {
    const serialNo = (serialInputs[unit.id] || "").trim();
    if (!serialNo) return;
    await run(async () => {
      const updated = await servicesApi.verifySerial(service.id, { unit_id: unit.id, serial_no: serialNo });
      const updatedUnit = (updated.units || []).find((row) => row.id === unit.id);
      const notInOrder = Boolean(updatedUnit?.serial_not_in_order);
      return {
        successMessage: notInOrder
          ? `Serial ${serialNo} submitted for Admin/Indcool review. It was not found in order records — admin will verify and decide.`
          : `Serial ${serialNo} submitted for Admin/Indcool review.`,
      };
    });
  }

  async function verifyAll() {
    await run(
      () => servicesApi.verifySerialsBulk(service.id, { unit_ids: unverifiedUnits.map((unit) => unit.id) }),
      { successMessage: `Verified ${unverifiedUnits.length} serial(s).` },
    );
  }

  async function addSerialToVisit() {
    const serial = newVisitSerial.trim();
    if (!serial || busy) return;
    setNewVisitSerial("");
    await run(
      async () => {
        const updated = await servicesApi.addUnitBySerial(service.id, { serial_no: serial });
        const assignedToYou = (updated.units || []).some(
          (unit) => engineerIdsMatch(unit.assigned_engineer_id, userId),
        );
        const message = assignedToYou
          ? `Serial ${serial} added and assigned to you. Use Verify on that row below to continue.`
          : `Serial ${serial} was saved on this request. If you do not see a row below, refresh or ask service team to assign the unit.`;
        return { ...updated, successMessage: message };
      },
      { scrollToId: "engineer-serial-workflow-table" },
    );
  }

  function openSerialReview(unit) {
    setSerialReviewForms((current) => ({
      ...current,
      [unit.id]: {
        remarks: current[unit.id]?.remarks || (unit.serial_not_in_order ? "" : "Approved"),
        override_serial: unit.serial_no || "",
        associate_with_order: Boolean(unit.serial_not_in_order),
        billing_type: current[unit.id]?.billing_type || unitBillingValue(unit),
      },
    }));
    openModal("serialReview", unit.id);
  }

  async function saveUnitBilling(unit, billingType) {
    if (!unit?.id || unitBillingLocked(unit)) return;
    await run(
      () => servicesApi.setUnitBilling(service.id, { unit_id: unit.id, billing_type: billingType }),
      { successMessage: `Billing set to ${billingType} for ${unit.serial_no || "serial"}.` },
    );
  }

  function updateSerialReview(unitId, field, value) {
    setSerialReviewForms((current) => ({
      ...current,
      [unitId]: { ...current[unitId], [field]: value },
    }));
  }

  async function submitSerialReview(decision) {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "serialReview") return;
    const form = serialReviewForms[unit.id] || {};
    const remarks = (form.remarks || "").trim();
    if (decision === "reject" && !remarks) {
      window.alert("Please enter a reason for rejecting this serial.");
      return;
    }
    const payload = {
      unit_id: unit.id,
      decision,
      remarks: remarks || null,
      serial_no: (form.override_serial || unit.serial_no || "").trim() || null,
      associate_serial_with_order: Boolean(form.associate_with_order),
      billing_type: form.billing_type || unitBillingValue(unit),
    };
    const successMessages = {
      approve: unit.serial_not_in_order
        ? "Serial verified and linked to order."
        : "Serial verification approved.",
      override: "Serial override approved and linked to order.",
      reject: "Serial rejected — engineer can submit again.",
    };
    await run(
      () => servicesApi.reviewSerial(service.id, payload),
      { successMessage: successMessages[decision] || "Serial review saved." },
    );
    closeModal();
  }

  async function submitOne(unitId) {
    const row = rows.find((item) => item.unit_id === unitId);
    if (!row) return;
    await run(
      () => servicesApi.submitObservation(service.id, {
        unit_id: unitId,
        problem_found: row.problem_found || null,
        observation: row.observation || null,
        recommended_action: row.recommended_action || null,
        parts_required: row.parts_required
          ? row.parts_required.split(",").map((item) => item.trim()).filter(Boolean)
          : [],
        estimated_service_charge: row.estimated_service_charge === "" ? null : Number(row.estimated_service_charge),
        estimated_parts_charge: row.estimated_parts_charge === "" ? null : Number(row.estimated_parts_charge),
        remarks: row.remarks || null,
      }),
      { successMessage: "Observation submitted. You can finish this serial end-to-end or continue with other serials." },
    );
    closeModal();
  }

  async function submitAll() {
    const payload = unitsNeedingObservation.map((unit) => {
      const row = rows.find((item) => item.unit_id === unit.id);
      return {
        unit_id: unit.id,
        problem_found: row?.problem_found || null,
        observation: row?.observation || null,
        recommended_action: row?.recommended_action || null,
        parts_required: row?.parts_required
          ? row.parts_required.split(",").map((item) => item.trim()).filter(Boolean)
          : [],
        estimated_service_charge: row?.estimated_service_charge === "" || row?.estimated_service_charge === undefined
          ? null
          : Number(row.estimated_service_charge),
        estimated_parts_charge: row?.estimated_parts_charge === "" || row?.estimated_parts_charge === undefined
          ? null
          : Number(row.estimated_parts_charge),
        remarks: row?.remarks || null,
      };
    });
    await run(
      () => servicesApi.submitObservationsBulk(service.id, { observations: payload }),
      { successMessage: `Submitted observations for ${payload.length} serial(s).` },
    );
  }

  async function approveUnit(unitId, decision) {
    await run(
      () => servicesApi.approve(service.id, {
        unit_id: unitId,
        decision,
        remarks: approvalRemarks[unitId] || (decision === "Approve" ? "Approved" : "Rejected"),
      }),
      { successMessage: decision === "Approve" ? "Serial approved for service." : "Serial sent back." },
    );
    closeModal();
  }

  async function approveAllPending() {
    await run(
      () => servicesApi.approveBulk(service.id, { decision: "Approve", remarks: "Bulk approved" }),
      { successMessage: "All pending serials approved." },
    );
  }

  function openCompletionReview(unit) {
    setCompletionReviewRemarks((current) => ({
      ...current,
      [unit.id]: current[unit.id] || "",
    }));
    openModal("completionReview", unit.id);
  }

  async function submitCompletionReview(decision) {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "completionReview") return;
    const remarks = (completionReviewRemarks[unit.id] || "").trim();
    if (decision === "Reject" && !remarks) {
      window.alert("Please enter a reason for rejecting this completion.");
      return;
    }
    await run(
      () => servicesApi.reviewCompletion(service.id, {
        unit_id: unit.id,
        decision,
        remarks: remarks || null,
      }),
      {
        successMessage: decision === "Approve"
          ? "Completion approved. Engineer can raise payment."
          : "Completion rejected and returned to engineer.",
      },
    );
    closeModal();
  }

  async function completeUnit(unitId) {
    const row = completionRows[unitId];
    const proof = completionProofs[unitId];
    const completionStatus = row?.completion_status || "Service Completed";
    if (completionStatus === "Service Completed" && (!proof || !row?.completion_code?.trim())) return;
    const formData = new FormData();
    formData.append("unit_id", String(unitId));
    formData.append("work_performed", row.work_performed || "");
    formData.append("parts_replaced", JSON.stringify(
      row.parts_replaced ? row.parts_replaced.split(",").map((item) => item.trim()).filter(Boolean) : [],
    ));
    formData.append("service_notes", row.service_notes || "");
    if (row.service_date) formData.append("service_date", row.service_date);
    if (row.final_amount !== "") formData.append("final_amount", row.final_amount);
    formData.append("completion_remarks", row.completion_remarks || "");
    formData.append("completion_code", row.completion_code || "");
    formData.append("completion_status", completionStatus);
    if (proof) formData.append("proof_document", proof);
    await run(
      () => servicesApi.complete(service.id, formData),
      { successMessage: completionStatus === "Service Completed" ? "Service completed for this serial. Use Step 5 to raise payment when ready." : `Status updated to ${completionStatus}.` },
    );
    closeModal();
  }

  async function requestPayment(unitId) {
    const row = paymentRows[unitId];
    const qr = paymentQrCodes[unitId];
    if (row.payment_type === "UPI" && !qr) return;
    const formData = new FormData();
    formData.append("unit_id", String(unitId));
    if (row.customer_charge_amount !== "") formData.append("customer_charge_amount", row.customer_charge_amount);
    if (row.settlement_service_amount !== "") formData.append("settlement_service_amount", row.settlement_service_amount);
    if (row.settlement_parts_amount !== "") formData.append("settlement_parts_amount", row.settlement_parts_amount);
    if (row.total_requested_amount !== "") formData.append("total_requested_amount", row.total_requested_amount);
    formData.append("payment_type", row.payment_type || "Cash");
    formData.append("remarks", row.remarks || "");
    if (row.payment_type === "UPI" && qr) formData.append("qr_code", qr);
    await run(
      () => servicesApi.requestPayment(service.id, formData),
      { successMessage: "Payment request raised for this serial." },
    );
    closeModal();
  }

  async function rejectPayment(unitId) {
    const form = paymentApprovalForms[unitId] || { remarks: "" };
    if (!form.remarks?.trim()) {
      return;
    }
    await run(
      () => servicesApi.cancelPaymentRequest(service.id, {
        unit_id: unitId,
        remarks: form.remarks,
        reject: true,
      }),
      { successMessage: "Payment request rejected. Engineer can update and re-submit." },
    );
    closeModal();
  }

  function progressSummary(unit) {
    if (unit.unit_status === "Payment Requested") {
      if (unit.total_requested_amount != null) {
        return `Payment requested (${unit.payment_type || "—"}): ${unit.total_requested_amount}`;
      }
      return "Payment requested — awaiting admin approval";
    }
    if (unit.unit_status === "Payment Completed") {
      return "Payment completed — awaiting service request close";
    }
    if (unit.unit_status === "Closed") {
      return "Serial closed";
    }
    if (unit.problem_found) {
      return unit.problem_found;
    }
    const row = rows.find((item) => item.unit_id === unit.id);
    if (row?.problem_found) {
      return row.problem_found;
    }
    if (!unit.serial_verified_at) {
      return "Awaiting serial verification";
    }
    if (!unit.observation_id) {
      return "Awaiting observation";
    }
    if (unit.unit_status === "Pending Service Approval") {
      return "Awaiting approval";
    }
    if (unit.unit_status === "Approved for Service") {
      return "Ready to complete";
    }
    if (unit.unit_status === "Service Completed") {
      return "Service completed — raise payment request next";
    }
    return "—";
  }

  function renderStepButton(unit) {
    const verified = Boolean(unit.serial_verified_at);
    const observed = Boolean(unit.observation_id);

    if (unit.unit_status === "Serial Verification Pending") {
      if (isServiceTeam) {
        return (
          <div className="flex flex-col items-end gap-1">
            <button
              type="button"
              onClick={() => openSerialReview(unit)}
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs text-white"
            >
              Review serial
            </button>
            {unit.serial_not_in_order && (
              <span className="text-xs text-amber-700">Not in order records</span>
            )}
          </div>
        );
      }
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-amber-700">
            {unit.serial_not_in_order
              ? "Awaiting Admin/Indcool review — serial not in order records"
              : "Awaiting admin serial review"}
          </span>
          <button
            type="button"
            onClick={() => openModal("serial", unit.id)}
            className="rounded-md border border-sky-300 px-3 py-1.5 text-xs text-sky-700"
          >
            Change serial
          </button>
        </div>
      );
    }

    if (!verified) {
      return (
        <button
          type="button"
          onClick={() => openModal("serial", unit.id)}
          disabled={!canVerifyOrObserve}
          className="rounded-md border border-sky-300 px-3 py-1.5 text-xs text-sky-700 disabled:opacity-50"
        >
          Verify serial
        </button>
      );
    }

    if (!observed && canVerifyOrObserve) {
      return (
        <button
          type="button"
          onClick={() => openModal("observation", unit.id)}
          className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs text-white"
        >
          Add observation
        </button>
      );
    }

    if (isEngineer && observed && unit.unit_status === "Rejected") {
      return (
        <button
          type="button"
          onClick={() => openModal("observation", unit.id)}
          className="rounded-md bg-amber-600 px-3 py-1.5 text-xs text-white"
        >
          Update observation
        </button>
      );
    }

    if ((isEngineer || isVendor) && ["Waiting for Part", "Customer Not Available"].includes(unit.unit_status)) {
      return (
        <button
          type="button"
          onClick={() => openModal("completion", unit.id)}
          className="rounded-md bg-amber-600 px-3 py-1.5 text-xs text-white"
        >
          Change status
        </button>
      );
    }

    if (isServiceTeam && unit.unit_status === "Pending Service Approval") {
      return (
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={() => openModal("approval", unit.id)}
            className="rounded-md bg-orange-500 px-3 py-1.5 text-xs text-white"
          >
            Review &amp; approve
          </button>
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Completion Pending Approval") {
      if (isServiceTeam) {
        return (
          <div className="flex flex-col items-end gap-1">
            <button
              type="button"
              onClick={() => openCompletionReview(unit)}
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs text-white"
            >
              Review completion
            </button>
            {proofActionLink(unit, openModal)}
          </div>
        );
      }
      return <span className="text-xs text-amber-700">Waiting for admin completion approval</span>;
    }

    if (unit.unit_status === "Payment Requested" && isServiceTeam) {
      return (
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={() => openModal("paymentApproval", unit.id)}
            className="rounded-md bg-orange-500 px-3 py-1.5 text-xs text-white"
          >
            Approve payment
          </button>
          {proofActionLink(unit, openModal)}
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Approved for Service" && (isEngineer || isVendor)) {
      return (
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={() => openModal("completion", unit.id)}
            className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs text-white"
          >
            Step 4: Complete service
          </button>
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Service Completed" && (isEngineer || isVendor)) {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs font-medium text-emerald-700">✓ Step 4: Service completed</span>
          <button
            type="button"
            onClick={() => openModal("payment", unit.id)}
            className="rounded-md bg-brand-600 px-3 py-1.5 text-xs text-white"
          >
            Step 5: Raise payment request
          </button>
          {proofActionLink(unit, openModal)}
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Service Completed" && isServiceTeam) {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-amber-700">Awaiting engineer payment request</span>
          {proofActionLink(unit, openModal)}
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Payment Requested" && !isServiceTeam) {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-amber-700">Payment pending admin approval</span>
          {proofActionLink(unit, openModal)}
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (unit.unit_status === "Closed") {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-slate-600">Serial closed</span>
          {proofActionLink(unit, openModal)}
        </div>
      );
    }

    if (unit.unit_status === "Payment Completed") {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-emerald-700">✓ Payment approved for this serial</span>
          {proofActionLink(unit, openModal)}
          {observed && (
            <button type="button" onClick={() => openModal("observation", unit.id)} className="text-xs text-sky-700 underline">
              View observation
            </button>
          )}
        </div>
      );
    }

    if (observed) {
      return (
        <button
          type="button"
          onClick={() => openModal("observation", unit.id)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-700"
        >
          View observation
        </button>
      );
    }

    return <span className="text-xs text-slate-400">—</span>;
  }

  function renderObservationModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "observation") return null;
    const row = rows.find((item) => item.unit_id === unit.id) || emptyRow(unit);
    const observationEditable = ["Pending Service Approval", "Rejected"].includes(unit.unit_status);
    const readOnly = Boolean(unit.observation_id && !observationEditable);
    const canEdit = canVerifyOrObserve && (!unit.observation_id || observationEditable) && unit.serial_verified_at;

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Observation — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          {unit.observation_id && !readOnly && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Observation is pending Admin/Indcool approval. You can still edit and resubmit it.
            </div>
          )}
          <div>
            <FieldLabel required={canEdit}>Problem found</FieldLabel>
            <input
              value={row.problem_found}
              onChange={(e) => updateRow(unit.id, "problem_found", e.target.value)}
              disabled={!canEdit}
              placeholder="Problem found"
              className={inputClass(!canEdit)}
            />
          </div>
          <div>
            <FieldLabel required={canEdit}>Engineer observation</FieldLabel>
            <textarea
              value={row.observation}
              onChange={(e) => updateRow(unit.id, "observation", e.target.value)}
              disabled={!canEdit}
              rows={3}
              placeholder="Engineer observation"
              className={inputClass(!canEdit)}
            />
          </div>
          <div>
            <FieldLabel>Recommended action</FieldLabel>
            <textarea
              value={row.recommended_action}
              onChange={(e) => updateRow(unit.id, "recommended_action", e.target.value)}
              disabled={!canEdit}
              rows={2}
              placeholder="Recommended action"
              className={inputClass(!canEdit)}
            />
          </div>
          <div>
            <FieldLabel>Parts required</FieldLabel>
            <input
              value={row.parts_required}
              onChange={(e) => updateRow(unit.id, "parts_required", e.target.value)}
              disabled={!canEdit}
              placeholder="Parts required (comma separated)"
              className={inputClass(!canEdit)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel>Estimated service charge</FieldLabel>
              <input
                value={row.estimated_service_charge}
                onChange={(e) => updateRow(unit.id, "estimated_service_charge", e.target.value)}
                disabled={!canEdit}
                placeholder="Estimated service charge"
                className={inputClass(!canEdit)}
              />
            </div>
            <div>
              <FieldLabel>Estimated parts charge</FieldLabel>
              <input
                value={row.estimated_parts_charge}
                onChange={(e) => updateRow(unit.id, "estimated_parts_charge", e.target.value)}
                disabled={!canEdit}
                placeholder="Estimated parts charge"
                className={inputClass(!canEdit)}
              />
            </div>
          </div>
          <div>
            <FieldLabel>Remarks</FieldLabel>
            <textarea
              value={row.remarks}
              onChange={(e) => updateRow(unit.id, "remarks", e.target.value)}
              disabled={!canEdit}
              rows={2}
              placeholder="Remarks"
              className={inputClass(!canEdit)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              {canEdit ? "Cancel" : "Close"}
            </button>
            {canEdit && (
              <button
                type="button"
                onClick={() => submitOne(unit.id)}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white"
              >
                {unit.observation_id ? "Update observation" : "Submit observation"}
              </button>
            )}
          </div>
        </div>
      </Modal>
    );
  }

  function renderSerialModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "serial") return null;
    const isChange = unit.unit_status === "Serial Verification Pending";
    return (
      <Modal open onClose={closeModal} title={isChange ? "Change serial for admin review" : "Verify serial"} maxWidth="max-w-md">
        <div className="space-y-3">
          <p className="text-sm text-slate-600">
            {isChange
              ? "Enter the correct serial number. It will be submitted again for Admin/Indcool approval."
              : "Enter the serial number. It will be submitted to Admin/Indcool for approval. If the serial is not on the order, Admin/Indcool will review and decide."}
          </p>
          <input
            value={serialInputs[unit.id] || ""}
            onChange={(event) => setSerialInputs((current) => ({ ...current, [unit.id]: event.target.value }))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Serial number"
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button
              type="button"
              onClick={() => verifyOne(unit).then(closeModal)}
              disabled={!serialInputs[unit.id]?.trim()}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              {isChange ? "Submit changed serial" : "Submit serial for review"}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderSerialReviewModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "serialReview") return null;
    const form = serialReviewForms[unit.id] || {
      remarks: unit.serial_not_in_order ? "" : "Approved",
      override_serial: unit.serial_no || "",
      associate_with_order: Boolean(unit.serial_not_in_order),
      billing_type: unitBillingValue(unit),
    };

    return (
      <Modal open onClose={closeModal} title="Review engineer serial" maxWidth="max-w-lg">
        <div className="space-y-4">
          {unit.serial_not_in_order ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Engineer submitted serial <strong className="font-mono">{unit.serial_no}</strong>, which was
              <strong> not found in order records</strong>. Approve and link it to the order, override with a
              corrected serial, or reject so the engineer can try again.
            </div>
          ) : (
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
              Engineer submitted serial <strong className="font-mono">{unit.serial_no}</strong> for approval.
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Serial to approve</label>
            <input
              value={form.override_serial || ""}
              onChange={(event) => updateSerialReview(unit.id, "override_serial", event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono"
              placeholder="Serial number"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Service billing</label>
            <select
              value={form.billing_type || "Free"}
              onChange={(event) => updateSerialReview(unit.id, "billing_type", event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="Free">Free</option>
              <option value="Paid">Paid</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Applies to this serial for the rest of the service (observation, completion, payment).
            </p>
          </div>

          {unit.serial_not_in_order && (
            <label className="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={Boolean(form.associate_with_order)}
                onChange={(event) => updateSerialReview(unit.id, "associate_with_order", event.target.checked)}
                className="mt-1"
              />
              <span>Associate this serial with the linked order if it is not already on an order line.</span>
            </label>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Remarks</label>
            <textarea
              value={form.remarks || ""}
              onChange={(event) => updateSerialReview(unit.id, "remarks", event.target.value)}
              rows={3}
              placeholder={unit.serial_not_in_order ? "Optional approval remarks" : "Approval remarks"}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => submitSerialReview("reject")}
              className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700"
            >
              Reject
            </button>
            {unit.serial_not_in_order && (
              <button
                type="button"
                onClick={() => submitSerialReview("override")}
                disabled={!form.override_serial?.trim()}
                className="rounded-md border border-sky-300 px-3 py-2 text-sm text-sky-700 disabled:opacity-50"
              >
                Override &amp; approve
              </button>
            )}
            <button
              type="button"
              onClick={() => submitSerialReview("approve")}
              disabled={!form.override_serial?.trim()}
              className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Approve serial
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderCompletionReviewModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "completionReview") return null;
    const remarks = completionReviewRemarks[unit.id] || "";

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Review completion — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-lg"
      >
        <div className="space-y-4">
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Engineer submitted completion for this serial. Approve to allow payment request, or reject to send it back.
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 space-y-1">
            <div>
              <strong>Serial:</strong>{" "}
              <span className="font-mono">{unit.serial_no || "—"}</span>
            </div>
            <div>
              <strong>Billing:</strong> {unit.admin_billing_type || (unit.service_type === "Paid Service" ? "Paid" : "Free")}
            </div>
            {unit.work_performed && (
              <div><strong>Work performed:</strong> {unit.work_performed}</div>
            )}
            {unit.final_amount != null && unit.final_amount !== "" && (
              <div><strong>Final amount:</strong> {unit.final_amount}</div>
            )}
            {unit.engineer_completion_code && (
              <div>
                <strong>Happy code:</strong>{" "}
                <span className="font-mono font-semibold">{unit.engineer_completion_code}</span>
                {service?.completion_code && (
                  <span className="ml-2 text-xs text-slate-500">
                    ({unit.engineer_completion_code === service.completion_code ? "matches" : "does not match"})
                  </span>
                )}
              </div>
            )}
          </div>

          {unit.completion_proof_path ? (
            <AttachmentPreview
              title="Service proof"
              path={unit.completion_proof_path}
              description="Uploaded by engineer with completion."
            />
          ) : (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              No service proof uploaded for this serial.
            </div>
          )}

          <div>
            <FieldLabel>Remarks {remarks.trim() ? "" : "(required to reject)"}</FieldLabel>
            <textarea
              value={remarks}
              onChange={(e) => setCompletionReviewRemarks((current) => ({
                ...current,
                [unit.id]: e.target.value,
              }))}
              rows={3}
              placeholder="Optional approval remarks, or reason for rejection"
              className={inputClass()}
            />
          </div>

          <div className="flex flex-wrap justify-end gap-2 pt-1">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => submitCompletionReview("Reject")}
              disabled={busy || !remarks.trim()}
              className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
            >
              Reject completion
            </button>
            <button
              type="button"
              onClick={() => submitCompletionReview("Approve")}
              disabled={busy}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Approve completion
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderApprovalModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "approval") return null;

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Approval — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-lg"
      >
        <div className="space-y-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <div><strong>Problem:</strong> {unit.problem_found || "—"}</div>
            <div className="mt-1"><strong>Observation:</strong> {unit.observation_text || "—"}</div>
            <div className="mt-1"><strong>Recommended action:</strong> {unit.recommended_action || "—"}</div>
          </div>
          <div>
            <FieldLabel>Approval remarks</FieldLabel>
            <textarea
              value={approvalRemarks[unit.id] || ""}
              onChange={(e) => setApprovalRemarks((current) => ({ ...current, [unit.id]: e.target.value }))}
              rows={3}
              placeholder="Approval remarks"
              className={inputClass()}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => approveUnit(unit.id, "Reject")}
              className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700"
            >
              Reject / Send back
            </button>
            <button
              type="button"
              onClick={() => approveUnit(unit.id, "Approve")}
              className="rounded-md bg-orange-500 px-4 py-2 text-sm text-white"
            >
              Approve
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderCompletionModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "completion") return null;
    const completion = completionRows[unit.id] || emptyCompletion(unit);
    const proof = completionProofs[unit.id];

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Step 4: Complete service — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          <div>
            <FieldLabel required>Request status</FieldLabel>
            <select
              value={completion.completion_status || "Service Completed"}
              onChange={(e) => updateCompletion(unit.id, "completion_status", e.target.value)}
              className={inputClass()}
            >
              <option value="Service Completed">Service Completed</option>
              <option value="Waiting for Part">Waiting for Part</option>
              <option value="Customer Not Available">Customer Not Available</option>
            </select>
          </div>
          <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            Select the current outcome. Proof and Happy Code are required only when marking service completed.
          </div>
          <div>
            <FieldLabel required>Work performed</FieldLabel>
            <input
              value={completion.work_performed}
              onChange={(e) => updateCompletion(unit.id, "work_performed", e.target.value)}
              placeholder="Work performed"
              className={inputClass()}
            />
          </div>
          <div>
            <FieldLabel>Parts replaced</FieldLabel>
            <input
              value={completion.parts_replaced}
              onChange={(e) => updateCompletion(unit.id, "parts_replaced", e.target.value)}
              placeholder="Parts replaced (comma separated)"
              className={inputClass()}
            />
          </div>
          <div>
            <FieldLabel>Service notes</FieldLabel>
            <textarea
              value={completion.service_notes}
              onChange={(e) => updateCompletion(unit.id, "service_notes", e.target.value)}
              rows={2}
              placeholder="Service notes"
              className={inputClass()}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel>Service date</FieldLabel>
              <input
                type="date"
                value={completion.service_date}
                onChange={(e) => updateCompletion(unit.id, "service_date", e.target.value)}
                className={inputClass()}
              />
            </div>
            <div>
              <FieldLabel>Final amount</FieldLabel>
              <input
                value={completion.final_amount}
                onChange={(e) => updateCompletion(unit.id, "final_amount", e.target.value)}
                placeholder="Final amount"
                className={inputClass()}
              />
            </div>
          </div>
          <div>
            <FieldLabel required={completion.completion_status === "Service Completed"}>Proof of service document</FieldLabel>
            {unit.completion_proof_path && (
              <div className="mb-2">
                <AttachmentPreview
                  title="Previously uploaded proof"
                  path={unit.completion_proof_path}
                />
              </div>
            )}
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              onChange={(e) => setCompletionProofs((current) => ({ ...current, [unit.id]: e.target.files?.[0] || null }))}
              className="block w-full text-sm"
            />
            <p className="mt-1 text-xs text-slate-500">
              Upload customer-signed acknowledgement, service report, or photo proof. Required before marking service completed.
            </p>
          </div>
          <div>
            <FieldLabel required={completion.completion_status === "Service Completed"}>Completion code (Happy code)</FieldLabel>
            <input
              value={completion.completion_code}
              onChange={(e) => updateCompletion(unit.id, "completion_code", e.target.value)}
              placeholder="Enter Happy Code"
              className={inputClass()}
            />
            <p className="mt-1 text-xs text-slate-500">
              Ask the customer for the completion code sent when the engineer was assigned.
            </p>
          </div>
          <div>
            <FieldLabel>Completion remarks</FieldLabel>
            <textarea
              value={completion.completion_remarks}
              onChange={(e) => updateCompletion(unit.id, "completion_remarks", e.target.value)}
              rows={2}
              placeholder="Completion remarks"
              className={inputClass()}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => completeUnit(unit.id)}
              disabled={completion.completion_status === "Service Completed" && (!proof || !completion.completion_code?.trim())}
              className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {completion.completion_status === "Service Completed" ? "Mark service completed" : `Save ${completion.completion_status}`}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderPaymentModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "payment") return null;
    const payment = paymentRows[unit.id] || emptyPayment(unit);
    const qr = paymentQrCodes[unit.id];
    const qrRequired = payment.payment_type === "UPI";

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Step 5: Raise payment request — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            Service is already completed for this serial. Submit payment details only — proof of service was uploaded in Step 4.
          </div>
          <div>
            <FieldLabel>Customer charge amount</FieldLabel>
            <input
              value={payment.customer_charge_amount}
              onChange={(e) => updatePayment(unit.id, "customer_charge_amount", e.target.value)}
              placeholder="Customer charge amount"
              className={inputClass()}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel>Settlement service amount</FieldLabel>
              <input
                value={payment.settlement_service_amount}
                onChange={(e) => updatePayment(unit.id, "settlement_service_amount", e.target.value)}
                placeholder="Settlement service amount"
                className={inputClass()}
              />
            </div>
            <div>
              <FieldLabel>Settlement parts amount</FieldLabel>
              <input
                value={payment.settlement_parts_amount}
                onChange={(e) => updatePayment(unit.id, "settlement_parts_amount", e.target.value)}
                placeholder="Settlement parts amount"
                className={inputClass()}
              />
            </div>
          </div>
          <div>
            <FieldLabel>Total requested amount</FieldLabel>
            <input
              value={payment.total_requested_amount}
              onChange={(e) => updatePayment(unit.id, "total_requested_amount", e.target.value)}
              placeholder="Total requested amount"
              className={inputClass()}
            />
          </div>
          <div>
            <FieldLabel>Payment type</FieldLabel>
            <select
              value={payment.payment_type}
              onChange={(e) => updatePayment(unit.id, "payment_type", e.target.value)}
              className={inputClass()}
            >
              {PAYMENT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </div>
          {qrRequired && (
            <div>
              <FieldLabel required>QR code</FieldLabel>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => setPaymentQrCodes((current) => ({ ...current, [unit.id]: e.target.files?.[0] || null }))}
                className="block w-full text-sm"
              />
              <p className="mt-1 text-xs text-slate-500">Required when payment type is UPI.</p>
            </div>
          )}
          <div>
            <FieldLabel>Payment remarks</FieldLabel>
            <textarea
              value={payment.remarks}
              onChange={(e) => updatePayment(unit.id, "remarks", e.target.value)}
              rows={2}
              placeholder="Payment remarks"
              className={inputClass()}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => requestPayment(unit.id)}
              disabled={qrRequired && !qr}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Submit payment request
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderPaymentApprovalModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "paymentApproval") return null;
    const payment = paymentRows[unit.id] || emptyPayment(unit);
    const form = paymentApprovalForms[unit.id] || { approved_amount: "", remarks: "" };

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Approve payment — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <div><strong>Requested:</strong> {unit.total_requested_amount ?? payment.total_requested_amount ?? "—"}</div>
            <div className="mt-1"><strong>Payment type:</strong> {unit.payment_type || payment.payment_type}</div>
          </div>

          {(unit.payment_type || payment.payment_type) === "UPI" && !unit.payment_qr_code_path && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              UPI QR code is missing on this payment request. Ask the engineer to re-submit with a QR image.
            </div>
          )}

          {(unit.payment_type || payment.payment_type) === "UPI" && unit.payment_qr_code_path && (
            <AttachmentPreview
              title="Engineer UPI QR code"
              path={unit.payment_qr_code_path}
              description="Scan this QR code to pay the engineer before approving."
            />
          )}

          <AttachmentPreview
            title="Proof of service"
            path={unit.completion_proof_path}
            description="Review the engineer's service completion document before approving payment."
          />

          <div>
            <FieldLabel required>Approved payment amount</FieldLabel>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.approved_amount}
              onChange={(e) => setPaymentApprovalForms((current) => ({
                ...current,
                [unit.id]: { ...form, approved_amount: e.target.value },
              }))}
              placeholder="Approved payment amount"
              className={inputClass()}
            />
          </div>
          <div>
            <FieldLabel>Admin remarks {form.remarks ? "" : "(required to reject)"}</FieldLabel>
            <textarea
              value={form.remarks}
              onChange={(e) => setPaymentApprovalForms((current) => ({
                ...current,
                [unit.id]: { ...form, remarks: e.target.value },
              }))}
              rows={2}
              placeholder="Admin payment approval remarks"
              className={inputClass()}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => rejectPayment(unit.id)}
              disabled={!form.remarks?.trim()}
              className="rounded-md border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-50"
            >
              Reject payment
            </button>
            <button
              type="button"
              onClick={async () => {
                await run(
                  () => servicesApi.approvePayment(service.id, {
                    unit_id: unit.id,
                    approved_amount: Number(form.approved_amount),
                    payment_type: unit.payment_type || payment.payment_type,
                    remarks: form.remarks,
                  }),
                  { successMessage: "Payment approved for this serial." },
                );
                closeModal();
              }}
              disabled={form.approved_amount === ""}
              className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Approve payment
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  function renderServiceProofModal() {
    const unit = activeUnit();
    if (!unit || activeModal?.type !== "serviceProof") return null;

    return (
      <Modal
        open
        onClose={closeModal}
        title={`Service proof — ${unit.serial_no || "Serial"}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          {unit.work_performed && (
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <strong>Work performed:</strong> {unit.work_performed}
            </div>
          )}
          {isServiceTeam && unit.engineer_completion_code && (
            <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
              <strong>Happy code entered by engineer:</strong>{" "}
              <span className="font-mono font-semibold">{unit.engineer_completion_code}</span>
              {service?.completion_code && (
                <span className="ml-2 text-xs">
                  ({unit.engineer_completion_code === service.completion_code ? "matches customer code" : "does not match customer code"})
                </span>
              )}
            </div>
          )}
          {unit.completion_proof_path ? (
            <AttachmentPreview
              title="Proof of service document"
              path={unit.completion_proof_path}
              description="Uploaded by engineer when marking service completed."
            />
          ) : (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              No service proof uploaded yet for this serial.
            </div>
          )}
          <div className="flex justify-end">
            <button type="button" onClick={closeModal} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Close
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  const customerIdentified = Boolean(
    service?.order_id
    || (service?.customer_mobile || "").trim()
    || (service?.customer_email || "").trim()
    || (service?.customer_name || "").trim(),
  );
  const addSerialBlock = (isEngineer || isServiceTeam) && customerIdentified && (
    <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 space-y-2">
      <div className="text-sm font-medium text-sky-900">Multiple serials on one visit</div>
      <p className="text-xs text-sky-800">
        Scan or enter each installed serial to add it to this visit. The serial may be on this order or another order
        for the same customer. Admin reviews each serial (free/paid); then complete and raise payment per serial.
      </p>
      <div className="flex flex-wrap gap-2">
        <input
          value={newVisitSerial}
          onChange={(e) => setNewVisitSerial(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addSerialToVisit();
            }
          }}
          placeholder="Serial number"
          className="min-w-[12rem] flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={addSerialToVisit}
          disabled={busy || !newVisitSerial.trim()}
          className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Adding…" : "Add serial"}
        </button>
      </div>
      {actionError && (
        <p className="text-sm text-rose-700">{actionError}</p>
      )}
    </div>
  );

  if (!workUnits.length) {
    if (!addSerialBlock) return null;
    return (
      <section className="rounded-lg bg-white p-6 shadow-sm space-y-4" id="engineer-serial-workflow-table">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Serial workflow (per unit)</h2>
        {addSerialBlock}
        {!busy && (service?.units || []).length > 0 && workUnits.length === 0 && isEngineer && (
          <p className="text-sm text-amber-800">
            This order has {service.units.length} unit(s) on the request, but none are assigned to you yet. Adding a serial
            here assigns that unit to you and opens the verify → service steps.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-lg bg-white p-6 shadow-sm space-y-6" id="engineer-serial-workflow-table">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
          Serial workflow (per unit)
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Each serial moves step by step: verify → observation → approval → <strong>complete service (with proof)</strong> → <strong>raise payment</strong> → admin payment approval. Only admin closes the request.
        </p>
      </div>

      {addSerialBlock}

      {isEngineer && unitsWithUnknownSerial.length > 0 && (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          {unitsWithUnknownSerial.length === 1
            ? `Serial ${unitsWithUnknownSerial[0].serial_no} was submitted for Admin/Indcool review because it was not found in order records. You will be notified when admin decides.`
            : `${unitsWithUnknownSerial.length} serial(s) were submitted for Admin/Indcool review because they were not found in order records.`}
        </div>
      )}

      {isServiceTeam && unitsWithUnknownSerial.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>Serial review required:</strong> {unitsWithUnknownSerial.length} unit(s) have serial numbers not found
          in order records ({unitsWithUnknownSerial.map((unit) => unit.serial_no).join(", ")}). Review each serial and
          approve, override, or reject.
        </div>
      )}

      {isServiceTeam && unitsAwaitingSerialReview.length > unitsWithUnknownSerial.length && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          {unitsAwaitingSerialReview.length - unitsWithUnknownSerial.length} serial(s) are waiting for routine admin approval.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {canVerifyOrObserve && unverifiedUnits.length > 0 && (
          <button type="button" onClick={verifyAll} className="rounded-md bg-sky-600 px-3 py-2 text-sm text-white">
            Verify all ({unverifiedUnits.length})
          </button>
        )}
        {canVerifyOrObserve && unitsNeedingObservation.length > 0 && (
          <button type="button" onClick={submitAll} className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white">
            Submit all observations ({unitsNeedingObservation.length})
          </button>
        )}
        {isServiceTeam && unitsPendingApproval.length > 0 && (
          <button type="button" onClick={approveAllPending} className="rounded-md bg-orange-500 px-3 py-2 text-sm text-white">
            Approve all pending ({unitsPendingApproval.length})
          </button>
        )}
      </div>

      <div className="overflow-x-auto rounded-md border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              {isServiceTeam && <th className="px-3 py-2">Billing</th>}
              <th className="px-3 py-2">Serial</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Verify</th>
              {!isEngineer && <th className="px-3 py-2">Steps</th>}
              {!isEngineer && <th className="px-3 py-2">Progress</th>}
              <th className="px-3 py-2 text-right">Step action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {workUnits.map((unit) => {
              const verified = Boolean(unit.serial_verified_at);
              return (
                <tr key={unit.id}>
                  {isServiceTeam && (
                    <td className="px-3 py-2">
                      <select
                        value={unitBillingValue(unit)}
                        disabled={busy || unitBillingLocked(unit) || !unit.serial_no}
                        onChange={(event) => saveUnitBilling(unit, event.target.value)}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs disabled:bg-slate-100"
                        title={
                          unitBillingLocked(unit)
                            ? "Billing is locked after payment or close"
                            : "Free or paid service for this serial"
                        }
                      >
                        <option value="Free">Free</option>
                        <option value="Paid">Paid</option>
                      </select>
                    </td>
                  )}
                  <td className="px-3 py-2 font-mono text-xs">{unit.serial_no || "—"}</td>
                  <td className="px-3 py-2"><StatusBadge value={unit.unit_status || "Assigned"} /></td>
                  <td className="px-3 py-2">
                    {verified ? (
                      <span className="text-xs text-emerald-700">Verified</span>
                    ) : (
                      <div className="space-y-1">
                        <span className="block text-xs text-slate-500">
                          {unit.unit_status === "Serial Verification Pending" ? "Submitted" : "Pending"}
                        </span>
                        {unit.unit_status === "Serial Verification Pending" && unit.serial_not_in_order && (
                          <span className="block text-xs text-amber-700">Not in order records</span>
                        )}
                      </div>
                    )}
                  </td>
                  {!isEngineer && <td className="px-3 py-2"><WorkflowSteps unit={unit} /></td>}
                  {!isEngineer && <td className="px-3 py-2 text-slate-600">{progressSummary(unit)}</td>}
                  <td className="px-3 py-2 text-right">{renderStepButton(unit)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {renderObservationModal()}
      {renderSerialModal()}
      {renderSerialReviewModal()}
      {renderApprovalModal()}
      {renderCompletionReviewModal()}
      {renderCompletionModal()}
      {renderPaymentModal()}
      {renderPaymentApprovalModal()}
      {renderServiceProofModal()}
    </section>
  );
}
