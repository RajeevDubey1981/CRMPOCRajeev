/** Shown while data loads: a simple INDcool-navy spinner. */
export default function PageLoader({ label = "Loading…", className = "" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center gap-2 py-10 text-sm font-bold text-indcool-navy ${className}`}
    >
      <span className="h-8 w-8 animate-spin rounded-full border-4 border-indcool-navy/20 border-t-indcool-navy" />
      <span>{label}</span>
    </div>
  );
}
