import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { DaysLeft, StatusPill, errText, fmtDate } from "../../pages/bids/bidUi.jsx";

const HELD = ["Allocated", "Confirmed", "Submitted"];

/** The vendor's own allocated bids, only when the bids module is switched on for them. */
export function useVendorBids() {
  const { user } = useAuth();
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const enabled = (user?.role || "").toLowerCase() === "vendor" && permissions.some((p) => p.module === "bids" && p.can_view);
  const [bids, setBids] = useState([]);
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    if (!enabled) return;
    bidsApi.list({}).then((rows) => setBids(rows.filter((b) => HELD.includes(b.status)))).catch(() => {});
  }, [enabled]);
  useEffect(() => { load(); }, [load]);

  async function confirm(bid) {
    try {
      await bidsApi.confirm(bid.id);
      setMsg({ tone: "ok", text: `${bid.bid_number} confirmed. Submit on the portal by ${fmtDate(bid.submit_by)}.` });
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e) });
    }
    load();
  }

  return { enabled, bids, msg, confirm };
}

export function BidStatCard({ bids }) {
  const navigate = useNavigate();
  const next = bids.filter((b) => b.status !== "Submitted").sort((a, b) => (a.end_date < b.end_date ? -1 : 1))[0];
  return (
    <div
      onClick={() => navigate("/bids")}
      className="flex min-w-[160px] flex-1 cursor-pointer items-center gap-4 rounded bg-brand-600 p-5 shadow ring-2 ring-brand-500 ring-offset-2 transition-transform hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="text-4xl opacity-90">📑</div>
      <div>
        <h5 className="text-base font-semibold text-white">Bids allocated to you</h5>
        <p className="mt-0.5 text-sm text-white/85">{bids.length} {bids.length === 1 ? "bid" : "bids"}</p>
        <p className="text-xs text-white/80">{next ? `Next closes ${fmtDate(next.end_date)}` : "Nothing open"}</p>
      </div>
    </div>
  );
}

export function BidsAside({ bids, msg, onConfirm }) {
  const need = bids.filter((b) => b.status === "Allocated").length;
  return (
    <aside className="rounded border-2 border-brand-600 bg-brand-50 p-3 lg:sticky lg:top-2">
      <div className="flex items-center justify-between gap-2 font-semibold text-slate-800">
        <span>Your bids</span>
        {need > 0 && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">{need} need{need > 1 ? "" : "s"} your answer</span>}
      </div>
      <p className="mb-2 text-xs text-slate-600">Only bids INDcool has allocated to you appear here.</p>
      {msg && <div className={`mb-2 rounded px-2 py-1 text-xs ${msg.tone === "ok" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-700"}`}>{msg.text}</div>}
      {bids.length === 0 && (
        <div className="rounded border border-sky-200 bg-white p-3 text-sm text-sky-800">
          Nothing is allocated to you right now. When INDcool allocates a bid, it shows here and you get an email.
        </div>
      )}
      <div className="space-y-2">
        {bids.map((b) => {
          const urgent = b.status !== "Submitted" && b.days_left <= 1;
          const soon = b.status !== "Submitted" && b.days_left <= 3;
          return (
            <div key={b.id} className={`rounded border-l-4 bg-white p-2.5 text-sm shadow-sm ${urgent ? "border-rose-500" : soon ? "border-amber-500" : "border-brand-600"}`}>
              <Link to={`/bids/${b.id}`} className="font-mono text-xs font-semibold text-brand-700 hover:underline">{b.bid_number}</Link>
              <div className="text-xs text-slate-500">{b.product_category}{b.product_type && b.product_type !== "Other" ? ` / ${b.product_type}` : ""}</div>
              <div className="text-slate-800">{b.title}</div>
              <div className="mt-1 flex flex-wrap items-center gap-1">
                <StatusPill bid={b} />
                {b.status !== "Submitted" && <span className="text-xs text-slate-600">closes {fmtDate(b.end_date)}</span>}
                <DaysLeft bid={b} />
              </div>
              {b.status === "Allocated" && (
                <>
                  <div className="mt-1 text-xs text-slate-600">Please confirm by {fmtDate(b.confirm_by)}. After that it goes back to INDcool.</div>
                  <button type="button" onClick={() => onConfirm(b)} className="mt-2 rounded bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700">Confirm bidding</button>
                </>
              )}
              {b.status === "Confirmed" && <div className="mt-1 text-xs text-slate-600">Submit on the portal by {fmtDate(b.submit_by)}.</div>}
              {b.status === "Submitted" && <div className="mt-1 text-xs text-slate-600">Submitted. Waiting for the result.</div>}
            </div>
          );
        })}
      </div>
      <Link to="/bids/request" className="mt-3 block rounded border border-brand-600 bg-white px-3 py-1.5 text-center text-sm text-brand-700 hover:bg-brand-50">Request a bid</Link>
    </aside>
  );
}
