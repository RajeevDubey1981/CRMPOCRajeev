export default function WarrantyBadge({ value }) {
  if (!value) return <span className="text-slate-400">—</span>;
  const inWarranty = value === "IN WARRANTY";
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${
        inWarranty ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
      }`}
    >
      {value}
    </span>
  );
}
