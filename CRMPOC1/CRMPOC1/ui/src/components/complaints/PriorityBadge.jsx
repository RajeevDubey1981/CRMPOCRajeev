// Blinking marker for a complaint the call centre / service team marked as HIGH priority.
export default function PriorityBadge({ at, by, className = "" }) {
  const tip = ["High priority", by ? `marked by ${by}` : null, at ? new Date(at).toLocaleString() : null].filter(Boolean).join(" - ");
  return (
    <span title={tip} className={`prio-badge ${className}`}>
      <span className="prio-dot" aria-hidden="true" />
      HIGH PRIORITY
    </span>
  );
}
