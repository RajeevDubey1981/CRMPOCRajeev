// The Registered column: the day, the time and how long ago, the same on every list. Times are shown as Indian time.
const TZ = "Asia/Kolkata";
const dayKey = (d) => d.toLocaleDateString("en-CA", { timeZone: TZ });

export function registeredParts(at) {
  if (!at) return null;
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(String(at)) ? at : `${at}Z`);
  if (Number.isNaN(d.getTime())) return null;
  const days = Math.round((new Date(dayKey(new Date())) - new Date(dayKey(d))) / 864e5);
  return {
    date: d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: TZ }),
    time: d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: TZ }),
    ago: days <= 0 ? "Today" : days === 1 ? "Yesterday" : `${days} days ago`,
  };
}

export default function RegisteredCell({ at }) {
  const p = registeredParts(at);
  if (!p) return <span className="text-slate-400">—</span>;
  return (
    <div className="whitespace-nowrap">
      <div className="font-semibold text-slate-800">{p.date}</div>
      <div className="text-[11px] text-slate-400">{p.time} · {p.ago}</div>
    </div>
  );
}
