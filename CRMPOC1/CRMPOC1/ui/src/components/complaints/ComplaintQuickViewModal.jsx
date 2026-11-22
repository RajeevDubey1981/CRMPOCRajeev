import { useNavigate } from "react-router-dom";

import Modal from "../Modal.jsx";
import StatusBadge from "../StatusBadge.jsx";
import { getComplaintOpenPath, getLinkedRequestInfo, isInstallationEngineerAssigned, linkedRequestColumnLabel } from "../../utils/complaintLinks.js";
import { fmtIST } from "../../utils/time.js";

function fmtDate(s) {
  if (!s) return "—";
  try {
    return fmtIST(s, "Date", "en-IN", { day: "2-digit", month: "2-digit", year: "numeric" });
  } catch {
    return s;
  }
}

function ViewField({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? "sm:col-span-2" : ""}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>
        {value || "—"}
      </div>
    </div>
  );
}

export default function ComplaintQuickViewModal({
  complaint,
  open,
  onClose,
  isAdminLike = false,
  isCallcenter = false,
  canEdit = false,
  onEdit,
  onDelete,
  onReject,
}) {
  const navigate = useNavigate();
  if (!complaint) return null;

  const linked = getLinkedRequestInfo(complaint);
  const linkedLabel = linkedRequestColumnLabel(complaint);
  const installationLocked = isInstallationEngineerAssigned(complaint);
  const showLinkedOpenButton = Boolean(linked);
  const showOpenFullPage = !linked;
  const lockTitle = "Cannot reject or delete after an engineer is assigned to the installation request";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Complaint ${complaint.comp_no}`}
    >
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <StatusBadge value={complaint.status} />
          <span className="text-sm text-slate-500">{complaint.query_type || "—"}</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ViewField label="ID" value={String(complaint.id)} mono />
          <ViewField label="Ref No" value={complaint.comp_no} mono />
          <ViewField label="Customer Name" value={complaint.customer_name} />
          <ViewField label="Mobile" value={complaint.customer_mobile} mono />
          <ViewField label="Email" value={complaint.customer_email} />
          <ViewField label="Query Type" value={complaint.query_type} />
          <ViewField label={linkedLabel} value={linked?.label || "—"} />
          <ViewField label="Assigned Engineer" value={complaint.assigned_engineer_name} />
          <ViewField label="Status Date" value={fmtDate(complaint.status_date)} />
          <ViewField label="Created At" value={fmtDate(complaint.created_at)} />
          <ViewField label="Created By" value={complaint.created_by_name} />
          <ViewField label="Remark" value={complaint.remark} full />
          <ViewField label="Model Details" value={complaint.model_details} full />
          <ViewField label="Problem Description" value={complaint.problem_description} full />
          <ViewField label="Customer Address" value={complaint.customer_address} full />
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
          <button onClick={onClose} className="rounded border border-slate-300 px-3 py-2 text-sm">
            Close
          </button>
          {isAdminLike && complaint.status !== "Rejected" && onReject && (
            <button
              onClick={() => onReject(complaint)}
              disabled={installationLocked}
              title={installationLocked ? lockTitle : undefined}
              className="rounded border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400 disabled:hover:bg-transparent"
            >
              Reject
            </button>
          )}
          {canEdit && onEdit && (
            <button
              onClick={() => onEdit(complaint)}
              className="rounded border border-brand-300 px-3 py-2 text-sm text-brand-700 hover:bg-brand-50"
            >
              Edit
            </button>
          )}
          {isAdminLike && onDelete && (
            <button
              onClick={() => onDelete(complaint)}
              disabled={installationLocked}
              title={installationLocked ? lockTitle : undefined}
              className="rounded border border-rose-400 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400 disabled:hover:bg-transparent"
            >
              Delete
            </button>
          )}
          {showLinkedOpenButton && (
            <button
              onClick={() => {
                navigate(linked.path);
                onClose();
              }}
              className="rounded border border-sky-300 px-3 py-2 text-sm text-sky-800 hover:bg-sky-50"
            >
              {linked.kind === "installation" ? "Open installation request" : "Open service request"}
            </button>
          )}
          {showOpenFullPage && (
            <button
              onClick={() => {
                navigate(getComplaintOpenPath(complaint, { preferInstallationWorkflow: false }));
                onClose();
              }}
              className="rounded bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700"
            >
              Open full page
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
