import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { queriesApi } from "../../api/queries.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isQueryStaffRole } from "../../utils/roles.js";
import RaiseQueryModal from "./RaiseQueryModal.jsx";
import useQuerySummary, { STATUS_STYLE, timeAgo } from "./useQuerySummary.js";

function Stat({ label, value, hot }) {
  return (
    <div className={`rounded-md px-3 py-1.5 text-center ${hot ? "bg-rose-600 text-white" : "bg-white/15 text-white"}`}>
      <div className="text-lg font-bold leading-tight">{value ?? "-"}</div>
      <div className="text-[11px] opacity-90">{label}</div>
    </div>
  );
}

/**
 * Sits at the top of the dashboards.
 * Engineer / vendor / service team: a highlighted "Raise query" box with the answers waiting for them.
 * Admin and Sub Admin: the queries waiting for them, with who is asking, and a way to write to a user.
 */
export default function QueriesPanel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const staff = isQueryStaffRole(user?.role);
  const { summary } = useQuerySummary();
  const [rows, setRows] = useState([]);
  const [raising, setRaising] = useState(false);

  const load = useCallback(() => {
    queriesApi.list({ status: "Active", limit: 4 }).then((data) => setRows(data.slice(0, 4))).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    window.addEventListener("queries-changed", load);
    return () => { clearInterval(timer); window.removeEventListener("queries-changed", load); };
  }, [load]);

  const unread = summary?.unread ?? 0;

  return (
    <>
    <section className="overflow-hidden rounded-lg bg-gradient-to-r from-indcool-navy to-indcool-blue p-4 text-white shadow-md" aria-label="Queries">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-base font-semibold">
            <span aria-hidden="true">💬</span>
            {staff ? "Queries from the team" : "Need help? Ask the Admin team"}
            {unread > 0 && <span className="rounded-full bg-rose-600 px-2 py-0.5 text-xs font-bold">{unread} new</span>}
          </div>
          <p className="mt-0.5 text-sm text-slate-200">
            {staff
              ? "Open a query to answer it. You can also write to any user."
              : "Stuck on an order, a job, a payment or the app? Raise a query and the Admin team answers here."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Stat label={staff ? "Waiting for you" : "Open"} value={summary?.open} hot={staff && (summary?.open || 0) > 0} />
          {!staff && <Stat label="Answered" value={summary?.answered} hot={(summary?.answered || 0) > 0 && unread > 0} />}
          <button
            type="button"
            onClick={() => setRaising(true)}
            className="rounded-md bg-indcool-lime px-4 py-2.5 text-sm font-bold text-indcool-navy shadow hover:brightness-95"
          >
            {staff ? "+ Write to a user" : "+ Raise query"}
          </button>
          <Link to="/queries" className="rounded-md border border-white/40 px-3 py-2 text-sm font-medium text-white hover:bg-white/10">
            {staff ? "Open inbox" : "My queries"}
          </Link>
        </div>
      </div>

      {rows.length > 0 && (
        <ul className="mt-3 divide-y divide-white/15 rounded-md bg-white/10">
          {rows.map((q) => (
            <li key={q.id}>
              <Link to={`/queries/${q.id}`} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 px-3 py-2 text-sm hover:bg-white/10">
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[q.status] || ""}`}>{q.status}</span>
                <span className={q.unread_count > 0 ? "font-bold" : "font-medium"}>{q.subject}</span>
                {staff && <span className="text-slate-200">· {q.owner_name}</span>}
                {q.unread_count > 0 && <span className="rounded bg-rose-600 px-1.5 text-[10px] font-bold">{q.unread_count} new</span>}
                <span className="ml-auto text-xs text-slate-300">{timeAgo(q.last_message_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>

    {/* outside the blue box, so the form does not inherit its white text */}
    <RaiseQueryModal
      open={raising}
      staff={staff}
      onClose={() => setRaising(false)}
      onCreated={(created) => { setRaising(false); navigate(`/queries/${created.id}`); }}
    />
    </>
  );
}
