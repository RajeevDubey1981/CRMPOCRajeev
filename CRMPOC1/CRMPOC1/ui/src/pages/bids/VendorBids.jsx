import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { BidTabs, DaysLeft, Notice, PageTitle, StatusPill, btnGhost, btnPrimary, errText, fmtDate, fmtDateTime } from "./bidUi.jsx";

export default function VendorBids() {
  const [bids, setBids] = useState([]);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(0);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(() => {
    bidsApi.list({}).then((r) => { setBids(r); setLoaded(true); }).catch((e) => setMsg({ tone: "bad", text: errText(e) }));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function confirm(bid) {
    setBusy(bid.id);
    try {
      await bidsApi.confirm(bid.id);
      setMsg({ tone: "ok", text: `${bid.bid_number} confirmed. Please submit it on the portal by ${fmtDate(bid.submit_by)}.` });
      load();
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e) });
      load();
    } finally {
      setBusy(0);
    }
  }

  const live = bids.filter((b) => ["Allocated", "Confirmed", "Submitted"].includes(b.status));
  const past = bids.filter((b) => !["Allocated", "Confirmed", "Submitted"].includes(b.status));

  return (
    <div>
      <PageTitle title="My bids" sub="Only the bids INDcool has allocated to you are shown here." />
      <BidTabs manager={false} />
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      {loaded && live.length === 0 && (
        <Notice tone="info">Nothing is allocated to you right now. When INDcool allocates a bid you get an email and it shows here. You can also <Link to="/bids/request" className="underline">ask for a bid</Link>.</Notice>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {live.map((b) => (
          <div key={b.id} className="rounded-lg border-l-4 border-brand-600 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link to={`/bids/${b.id}`} className="font-mono font-semibold text-brand-700 hover:underline">{b.bid_number}</Link>
              <StatusPill bid={b} />
            </div>
            <div className="mt-1 text-sm text-slate-700">{b.title}</div>
            <div className="text-xs text-slate-500">{b.product_category}{b.product_type && b.product_type !== "Other" ? ` / ${b.product_type}` : ""}</div>
            <div className="mt-2 text-sm">Closes {fmtDate(b.end_date)}<DaysLeft bid={b} /></div>
            {b.status === "Allocated" && <p className="mt-1 text-xs text-slate-600">Please accept or reject by {b.confirm_due_at ? fmtDateTime(b.confirm_due_at) : fmtDate(b.confirm_by)}. After that it is withdrawn and opened for another eligible vendor.</p>}
            {b.status === "Confirmed" && <p className="mt-1 text-xs text-slate-600">Submit on the portal by {fmtDate(b.submit_by)}, then mark it submitted.</p>}
            {b.status === "Submitted" && <p className="mt-1 text-xs text-slate-600">Submitted. Waiting for the result.</p>}
            <div className="mt-3 flex gap-2">
              {b.status === "Allocated" && <button type="button" disabled={busy === b.id} onClick={() => confirm(b)} className={btnPrimary}>Confirm bidding</button>}
              <Link to={`/bids/${b.id}`} className={btnGhost}>Open</Link>
            </div>
          </div>
        ))}
      </div>
      {past.length > 0 && (
        <>
          <h2 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-slate-500">Earlier bids</h2>
          <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {past.map((b) => (
                  <tr key={b.id}>
                    <td className="px-3 py-2"><Link to={`/bids/${b.id}`} className="font-mono text-brand-700 hover:underline">{b.bid_number}</Link></td>
                    <td className="px-3 py-2">{b.title}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fmtDate(b.end_date)}</td>
                    <td className="px-3 py-2"><StatusPill bid={b} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
