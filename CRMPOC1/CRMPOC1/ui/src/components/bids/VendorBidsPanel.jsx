import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { errText, fmtDate } from "../../pages/bids/bidUi.jsx";

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
