const TONES = {
  Pending: "bg-orange-100 text-orange-700 border-orange-200",
  Resolved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  "Under Process": "bg-sky-100 text-sky-700 border-sky-200",
  Rejected: "bg-rose-100 text-rose-700 border-rose-200",
  "In Process": "bg-slate-200 text-slate-700 border-slate-300",
  "Admin Review Document": "bg-amber-100 text-amber-800 border-amber-200",
  Reviewed: "bg-emerald-100 text-emerald-700 border-emerald-200",
  Approved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  Verified: "bg-emerald-100 text-emerald-700 border-emerald-200",
  "Serial Verification Review": "bg-amber-100 text-amber-800 border-amber-200",
  "Waiting for Part": "bg-orange-100 text-orange-800 border-orange-200",
  "Customer Not Available": "bg-violet-100 text-violet-800 border-violet-200",
  "Service Team Review": "bg-sky-100 text-sky-800 border-sky-200",
  "New": "bg-amber-100 text-amber-800 border-amber-200",
  Assigned: "bg-sky-100 text-sky-800 border-sky-200",
  Cancelled: "bg-slate-200 text-slate-700 border-slate-300",
};

const LABELS = {
  "Serial Verification Review": "Waiting for Admin Approval",
};

export default function StatusBadge({ value }) {
  const tone = TONES[value] || "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-block max-w-none whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-medium leading-snug ${tone}`}>
      {LABELS[value] || value || "—"}
    </span>
  );
}
