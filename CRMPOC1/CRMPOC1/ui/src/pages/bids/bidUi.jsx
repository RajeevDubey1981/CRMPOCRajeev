import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-10-12" → "12 Oct 2026" (read by hand so the time zone can never shift the day). */
export function fmtDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return String(iso);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

// a time from the server (UTC, no zone mark) shown in India time: 10 Oct 2026, 11:30 AM
export function fmtDateTime(iso) {
  if (!iso) return "—";
  const text = String(iso);
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
}

export function fmtShort(iso) {
  return fmtDate(iso).slice(0, -5);
}

export function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function errText(e, fallback = "Something went wrong") {
  const detail = e?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  return detail || fallback;
}

export function isoDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export const STATUS_TONE = {
  Open: "bg-sky-100 text-sky-800 border-sky-200",
  Allocated: "bg-amber-100 text-amber-800 border-amber-200",
  Confirmed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  Submitted: "bg-teal-100 text-teal-800 border-teal-200",
  Won: "bg-emerald-600 text-white border-emerald-700",
  Lost: "bg-slate-200 text-slate-700 border-slate-300",
  Closed: "bg-rose-100 text-rose-800 border-rose-200",
};

export function statusLabel(bid) {
  if (bid.status === "Closed") return "Closed, not submitted";
  if (bid.status === "Open") return "Open for allocation";
  return bid.status;
}

export function StatusPill({ bid }) {
  return (
    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_TONE[bid.status] || "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {statusLabel(bid)}
    </span>
  );
}

export function DaysLeft({ bid }) {
  if (!["Open", "Allocated", "Confirmed"].includes(bid.status)) return null;
  const n = bid.days_left;
  if (n === null || n === undefined) return null;
  const tone = n < 0 ? "bg-rose-100 text-rose-700" : n <= 1 ? "bg-rose-100 text-rose-700" : n <= 3 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600";
  const text = n < 0 ? "ended" : n === 0 ? "closes TODAY" : `${n} day${n > 1 ? "s" : ""} left`;
  return <span className={`ml-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium ${tone}`}>{text}</span>;
}

const STEPS = [
  ["Entered", "Bid team enters it"],
  ["Allocated", "One bidder is picked"],
  ["Confirmed", "Bidder confirms in time"],
  ["Submitted", "Bidder submits on the portal"],
  ["Result", "Won or lost"],
];

export function Steps({ bid }) {
  let cur = 0;
  if (bid.status === "Allocated") cur = 1;
  else if (bid.status === "Confirmed") cur = 2;
  else if (bid.status === "Submitted") cur = 3;
  else if (bid.status === "Won" || bid.status === "Lost") cur = 5;
  return (
    <ol className="grid grid-cols-1 gap-2 sm:grid-cols-5">
      {STEPS.map(([name, sub], i) => {
        const done = i < cur;
        const current = i === cur;
        const closed = bid.status === "Closed" && current;
        const tone = closed
          ? "border-rose-300 bg-rose-50 text-rose-800"
          : done
            ? "border-emerald-300 bg-emerald-50 text-emerald-800"
            : current
              ? "border-brand-500 bg-brand-50 text-brand-700 ring-1 ring-brand-500"
              : "border-slate-200 bg-white text-slate-400";
        return (
          <li key={name} className={`rounded-md border px-3 py-2 text-xs ${tone}`}>
            <div className="font-semibold">{i + 1}. {name}</div>
            <div>{closed ? "Not submitted before the end date" : sub}</div>
          </li>
        );
      })}
    </ol>
  );
}

/** Row of links shown at the top of every bids page. Managers and vendors see different tabs. */
export function BidTabs({ manager }) {
  const tabs = manager
    ? [["/bids", "Bids", true], ["/bids/allocation", "Allocation"], ["/bids/requests", "Vendor requests"], ["/bids/stats", "Stats"], ["/bids/calendar", "Calendar"]]
    : [["/bids", "My bids", true], ["/bids/request", "Request a bid"], ["/bids/stats", "My stats"], ["/bids/calendar", "Calendar"]];
  return (
    <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200">
      {tabs.map(([to, label, end]) => (
        <NavLink
          key={to}
          to={to}
          end={!!end}
          className={({ isActive }) =>
            `-mb-px border-b-2 px-3 py-2 text-sm ${isActive ? "border-brand-600 font-semibold text-brand-700" : "border-transparent text-slate-600 hover:text-slate-900"}`
          }
        >
          {label}
        </NavLink>
      ))}
    </div>
  );
}

export function useBidSide() {
  const { user } = useAuth();
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const bids = permissions.find((p) => p.module === "bids" && !p.sub_module);
  return {
    allowed: !!bids?.can_view,
    manager: !!(bids?.can_view && bids?.can_edit),
    canOverride: !!bids?.can_delete,
  };
}

export function PageTitle({ title, sub, children }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">{title}</h1>
        {sub && <p className="text-sm text-slate-500">{sub}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

export function Notice({ tone = "info", children }) {
  if (!children) return null;
  const tones = {
    info: "bg-sky-50 text-sky-800 border-sky-200",
    ok: "bg-emerald-50 text-emerald-800 border-emerald-200",
    warn: "bg-amber-50 text-amber-800 border-amber-200",
    bad: "bg-rose-50 text-rose-700 border-rose-200",
  };
  return <div className={`mb-3 rounded-md border px-3 py-2 text-sm ${tones[tone]}`}>{children}</div>;
}

export const btnPrimary = "rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50";
export const btnGhost = "rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50";
export const btnDanger = "rounded-md bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50";
export const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";
export const labelClass = "mb-1 block text-sm font-medium text-slate-700";

export function BidLink({ bid, children }) {
  return (
    <Link to={`/bids/${bid.id}`} className="font-mono text-brand-700 hover:underline">
      {children || bid.bid_number}
    </Link>
  );
}
