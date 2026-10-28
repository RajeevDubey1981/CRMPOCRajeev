// The stages an installation request is shown in, on every installation screen and dashboard (the server groups the
// exact statuses the same way).
export const INSTALLATION_STAGES = [
  { key: "na", label: "Not assigned", color: "#EF9F27", text: "text-amber-700" },
  { key: "as", label: "Assigned", color: "#378ADD", text: "text-sky-700" },
  { key: "ip", label: "In progress", color: "#534AB7", text: "text-violet-700" },
  { key: "vp", label: "Verification Pending", color: "#0E8A8A", text: "text-teal-700" },
  { key: "ap", label: "Approval Pending", color: "#B5179E", text: "text-fuchsia-700" },
  { key: "in", label: "Installed", color: "#1D9E75", text: "text-emerald-700" },
  { key: "pay", label: "Payment", color: "#BA7517", text: "text-orange-700" },
  { key: "done", label: "Completed", color: "#0F6E56", text: "text-emerald-800" },
  { key: "rr", label: "Returned or rejected", color: "#D64545", text: "text-rose-700" },
];

export const stageLabel = (key) => INSTALLATION_STAGES.find((s) => s.key === key)?.label || "";
