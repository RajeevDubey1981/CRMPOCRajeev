import { Link } from "react-router-dom";

const chipClass =
  "inline-block max-w-[11rem] truncate whitespace-nowrap rounded-md border border-sky-200/80 bg-sky-50/90 px-2 py-0.5 font-mono text-[11px] font-semibold leading-tight text-sky-900 shadow-sm transition-colors hover:border-sky-300 hover:bg-sky-100";

/** Compact, single-line ref display for grids (IDC_…, SRV_…). */
export default function ReferenceChip({
  label,
  title,
  to,
  onClick,
  asButton = false,
}) {
  const text = (label || "").trim();
  if (!text) {
    return <span className="text-slate-400">—</span>;
  }
  const tip = title || text;

  if (asButton) {
    return (
      <button
        type="button"
        title={tip}
        onClick={onClick}
        className={`${chipClass} cursor-pointer text-left`}
      >
        {text}
      </button>
    );
  }

  if (to) {
    return (
      <Link
        to={to}
        title={tip}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.(e);
        }}
        className={chipClass}
      >
        {text}
      </Link>
    );
  }

  return (
    <span title={tip} className={`${chipClass} text-slate-700`}>
      {text}
    </span>
  );
}
