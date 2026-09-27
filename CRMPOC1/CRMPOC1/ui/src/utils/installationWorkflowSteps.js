/** Call-center installation workflow step helpers (steps 2–9 on installation detail). */

export const INSTALLATION_WORKFLOW_STEP_OPTIONS = [
  {
    step: 1,
    label: "Step 1 — Full reset (request created)",
    vendorLabel: "Step 1 — Vendor submitted (order linked)",
  },
  { step: 2, label: "Step 2 — Link / verify order", callcenterOnly: true },
  { step: 3, label: "Step 3 — Customer documents", callcenterOnly: true },
  {
    step: 4,
    label: "Step 4 — Assign engineer",
    vendorLabel: "Step 4 — Assign engineer (vendor order)",
  },
  { step: 5, label: "Step 5 — Engineer serial entry" },
  { step: 6, label: "Step 6 — Admin serial verification" },
  { step: 7, label: "Step 7 — Engineer completion" },
  { step: 8, label: "Step 8 — Admin completion approval" },
  { step: 9, label: "Step 9 — Engineer payment request" },
  { step: 10, label: "Step 10 — Admin payment approval" },
];

export function isVendorInitiatedInstallation(installation) {
  return (installation?.source || "vendor").toLowerCase() === "vendor"
    && Boolean(installation?.order_item_id || installation?.order_id);
}

export function getInstallationWorkflowStepOptions(installation) {
  const vendor = isVendorInitiatedInstallation(installation);
  return INSTALLATION_WORKFLOW_STEP_OPTIONS
    .filter((option) => !(option.callcenterOnly && vendor))
    .map((option) => ({
      ...option,
      label: vendor && option.vendorLabel ? option.vendorLabel : option.label,
    }));
}

export function getCurrentInstallationWorkflowStep(installation) {
  const { activeStep, steps } = getInstallationWorkflowStepState(installation);
  if (activeStep) return activeStep;
  if (steps[10]?.done) return 10;
  if (steps[9]?.done) return 9;
  if (steps[8]?.done) return 8;
  if (steps[7]?.done) return 7;
  if (steps[6]?.done) return 6;
  if (steps[5]?.done) return 5;
  if (steps[4]?.done) return 4;
  if (steps[3]?.done) return 3;
  if (steps[2]?.done) return 2;
  return 1;
}

export function isPaidInstallation(installation) {
  return (installation?.admin_billing_type || "Free") === "Paid";
}

export function isVendorAssignedInstallation(installation) {
  return isVendorInitiatedInstallation(installation)
    && Boolean(installation?.assigned_engineer);
}

export function usesStructuredInstallationWorkflow(installation) {
  const source = (installation?.source || "vendor").toLowerCase();
  return source === "callcenter" || isVendorInitiatedInstallation(installation);
}

export function isAssignedToUser(installation, userId) {
  if (!installation?.assigned_engineer || userId == null) return false;
  return Number(installation.assigned_engineer) === Number(userId);
}

export function installationSerialReady(installation) {
  if (installation?.serial_verified_at) return true;
  return isVendorAssignedInstallation(installation) && Boolean((installation?.serial_no || "").trim());
}

const ENGINEER_BULK_WORKFLOW_STATUSES = new Set([
  "Assigned",
  "In Progress",
  "Returned",
  "Rejected",
  "Serial Pending Verification",
  "Completion Pending Approval",
  "Installation Completed",
  "Payment Pending",
]);

const ADMIN_BULK_WORKFLOW_EXTRA_STATUSES = new Set(["Submitted"]);

export function isBulkWorkflowEligibleRow(row, { isAdminLike = false, userId, userName = "" } = {}) {
  if (!row || row.status === "Completed") return false;
  const source = (row.source || "vendor").toLowerCase();
  if (source !== "vendor") return false;
  const status = row.status || "";
  const statusAllowed = ENGINEER_BULK_WORKFLOW_STATUSES.has(status)
    || (isAdminLike && ADMIN_BULK_WORKFLOW_EXTRA_STATUSES.has(status));
  if (!statusAllowed) return false;
  if (isAdminLike) return true;
  if (row.assigned_engineer != null && userId != null) {
    return Number(row.assigned_engineer) === Number(userId);
  }
  if (userName && row.assigned_engineer_name) {
    return row.assigned_engineer_name.trim().toLowerCase() === userName.trim().toLowerCase();
  }
  return Boolean(row.assigned_engineer_name);
}

export function canUseBulkInstallationWorkflow(row, userId, userName = "") {
  return isBulkWorkflowEligibleRow(row, { isAdminLike: false, userId, userName });
}

export function adminBulkReviewActionLabel(status) {
  switch (status) {
    case "Completion Pending Approval":
      return "Approve completion (Step 8)";
    case "Payment Pending":
      return "Approve payment (Step 10)";
    case "Serial Pending Verification":
      return "Verify serials (Step 6)";
    case "Installation Completed":
      return "Review / payment request";
    case "Submitted":
      return "Assign engineer";
    case "Assigned":
    case "In Progress":
      return "Monitor engineer progress";
    default:
      return "Open workflow";
  }
}

export function getInstallationWorkflowStepState(installation) {
  const status = installation?.status || "";
  const paid = isPaidInstallation(installation);

  function forwardStepState(stepNum, done, activeStep) {
    if (done) return { done: true, locked: true };
    if (activeStep === stepNum) return { done: false, locked: false };
    if (activeStep != null && stepNum > activeStep) return { done: false, locked: true };
    return { done: false, locked: false };
  }

  if (isVendorInitiatedInstallation(installation)) {
    const step4Done = Boolean(installation?.assigned_engineer);
    if (!step4Done) {
      const steps = {
        2: { done: true, locked: true },
        3: { done: true, locked: true },
        4: { done: false, locked: false },
        5: { done: false, locked: true },
        6: { done: false, locked: true },
        7: { done: false, locked: true },
        8: { done: false, locked: true },
        9: { done: false, locked: true },
        10: { done: false, locked: true },
      };
      return { steps, activeStep: 4, paid };
    }

    const step5Done = status !== "Assigned"
      || Boolean(installation?.engineer_serials_submitted_at);
    const step6Done = installationSerialReady(installation);
    const step7Done = ["Completion Pending Approval", "Installation Completed", "Payment Pending", "Completed"].includes(status);
    const step8Done = ["Installation Completed", "Payment Pending", "Completed"].includes(status);
    const step9Done = Boolean(installation?.payment_requested_at)
      || status === "Payment Pending"
      || status === "Completed";
    const step10Done = status === "Completed";

    const activeStep = !step5Done && !step6Done ? 5
      : !step6Done ? 6
      : !step7Done ? 7
      : !step8Done ? 8
      : !step9Done ? 9
      : !step10Done ? 10
      : null;

    const steps = {
      2: { done: true, locked: true },
      3: { done: true, locked: true },
      4: { done: step4Done, locked: step6Done },
      5: forwardStepState(5, step5Done || step6Done, activeStep),
      6: forwardStepState(6, step6Done, activeStep),
      7: forwardStepState(7, step7Done, activeStep),
      8: forwardStepState(8, step8Done, activeStep),
      9: forwardStepState(9, step9Done, activeStep),
      10: forwardStepState(10, step10Done, activeStep),
    };

    return { steps, activeStep, paid };
  }

  const step2Done = Boolean(installation?.order_verified_at);
  const step3Done = Boolean(installation?.document_request_sent_at);
  const step4Done = Boolean(installation?.assigned_engineer);
  const step5Done = Boolean(installation?.engineer_serials_submitted_at)
    || status === "Serial Pending Verification"
    || Boolean(installation?.serial_verified_at);
  const step6Done = Boolean(installation?.serial_verified_at);
  const step7Done = ["Completion Pending Approval", "Installation Completed", "Payment Pending", "Completed"].includes(status);
  const step8Done = ["Installation Completed", "Payment Pending", "Completed"].includes(status);
  const step9Done = Boolean(installation?.payment_requested_at)
    || status === "Payment Pending"
    || status === "Completed";
  const step10Done = status === "Completed";

  const activeStep = !step2Done ? 2
    : !step4Done ? 4
    : !step5Done ? 5
    : !step6Done ? 6
    : !step7Done ? 7
    : !step8Done ? 8
    : !step9Done ? 9
    : !step10Done ? 10
    : null;

  const steps = {
    2: { done: step2Done, locked: step2Done },
    3: { done: step3Done, locked: step3Done },
    4: { done: step4Done, locked: step6Done },
    5: forwardStepState(5, step5Done, activeStep),
    6: forwardStepState(6, step6Done, activeStep),
    7: forwardStepState(7, step7Done, activeStep),
    8: forwardStepState(8, step8Done, activeStep),
    9: forwardStepState(9, step9Done, activeStep),
    10: forwardStepState(10, step10Done, activeStep),
  };

  return { steps, activeStep, paid };
}

const CALLCENTER_NON_ASSIGNABLE_STATUSES = [
  "Installation Completed",
  "Payment Pending",
  "Completed",
  "Settlement Pending",
  "Settlement Approved",
  "Returned",
  "Rejected",
];

/** Admin can assign/re-assign until serial numbers are verified (same engineer may hold multiple units on one order). */
export function canAssignCallcenterEngineer(installation) {
  if (installation?.serial_verified_at) return false;
  return !CALLCENTER_NON_ASSIGNABLE_STATUSES.includes(installation?.status || "");
}
