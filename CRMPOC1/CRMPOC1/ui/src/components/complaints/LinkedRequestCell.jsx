import { getLinkedRequestInfo } from "../../utils/complaintLinks.js";
import ReferenceChip from "./ReferenceChip.jsx";

export default function LinkedRequestCell({ complaint, onClick, plainInstallationLink = false }) {
  const linked = getLinkedRequestInfo(complaint);
  if (!linked) {
    return <span className="text-slate-400">—</span>;
  }

  if (plainInstallationLink && linked.kind === "installation") {
    return <ReferenceChip label={linked.label} title={linked.label} />;
  }

  return (
    <ReferenceChip
      label={linked.label}
      title={`Open ${linked.kind === "installation" ? "installation" : "service"} ${linked.label}`}
      to={linked.path}
      onClick={onClick}
    />
  );
}
