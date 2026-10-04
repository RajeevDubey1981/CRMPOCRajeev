import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import {
  BidLink,
  BidTabs,
  DaysLeft,
  Notice,
  PageTitle,
  StatusPill,
  btnGhost,
  btnPrimary,
  errText,
  fieldClass,
  fmtDate,
  useBidSide,
} from "./bidUi.jsx";

function OpenRow({ bid, vendors, onDone, onMsg }) {
  const [vendorId, setVendorId] = useState("");
  const [busy, setBusy] = useState(false);

  async function go(body, okText) {
    setBusy(true);
    try {
      await bidsApi.allocate(bid.id, body);
      onMsg({ tone: "ok", text: `${bid.bid_number}: ${okText}` });
      onDone();
    } catch (e) {
      onMsg({ tone: "bad", text: `${bid.bid_number}: ${errText(e)}` });
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-3 py-2"><BidLink bid={bid} />{bid.pending_requests > 0 && <span className="ml-1.5 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] text-indigo-700">{bid.pending_requests} asked</span>}</td>
      <td className="px-3 py-2"><div className="max-w-[260px] truncate" title={bid.title}>{bid.title}</div><div className="text-xs text-slate-500">{bid.product_category}</div></td>
      <td className="px-3 py-2 whitespace-nowrap">{fmtDate(bid.end_date)}<DaysLeft bid={bid} /></td>
      <td className="px-3 py-2">
        <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} className={`${fieldClass} min-w-[180px]`} aria-label={`Vendor for ${bid.bid_number}`}>
          <option value="">Choose a vendor</option>
          {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
      </td>
      <td className="px-3 py-2 whitespace-nowrap text-right">
        <button type="button" disabled={busy || !vendorId} onClick={() => go({ vendor_id: Number(vendorId) }, "allocated and the vendor was emailed")} className={btnPrimary}>Allocate</button>
        <button type="button" disabled={busy} onClick={() => go({ self_bid: true }, "INDcool will bid itself")} className={`${btnGhost} ml-2`}>INDcool bids</button>
      </td>
    </tr>
  );
}

export default function BidAllocation() {
  const side = useBidSide();
  const [bids, setBids] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => { bidsApi.list({ state: "Live" }).then(setBids).catch((e) => setMsg({ tone: "bad", text: errText(e) })); }, []);
  useEffect(() => { load(); bidsApi.vendors().then(setVendors).catch(() => {}); }, [load]);

  const open = bids.filter((b) => b.status === "Open");
  const held = bids.filter((b) => b.status !== "Open");

  return (
    <div>
      <PageTitle title="Allocation" sub="Give each free bid to one bidder. The vendor gets an email, the bid is locked, and it comes back if they do not confirm or submit in time." />
      <BidTabs manager />
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Free for allocation ({open.length})</h2>
      <div className="mb-6 overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-xs font-semibold text-slate-600">
            <tr><th className="px-3 py-2">Bid number</th><th className="px-3 py-2">Item</th><th className="px-3 py-2">Closes</th><th className="px-3 py-2">Vendor</th><th className="px-3 py-2" /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {open.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No free bids. <Link to="/bids/new" className="text-brand-700 underline">Enter a bid</Link></td></tr>}
            {open.map((b) => <OpenRow key={b.id} bid={b} vendors={vendors} onDone={load} onMsg={setMsg} />)}
          </tbody>
        </table>
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Locked to a bidder ({held.length})</h2>
      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-xs font-semibold text-slate-600">
            <tr><th className="px-3 py-2">Bid number</th><th className="px-3 py-2">Bidder</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Confirm by</th><th className="px-3 py-2">Submit by</th><th className="px-3 py-2">Closes</th><th className="px-3 py-2" /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {held.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Nothing is locked right now.</td></tr>}
            {held.map((b) => (
              <tr key={b.id} className="hover:bg-slate-50">
                <td className="px-3 py-2"><BidLink bid={b} /></td>
                <td className="px-3 py-2">{b.vendor_name}</td>
                <td className="px-3 py-2"><StatusPill bid={b} /></td>
                <td className="px-3 py-2 whitespace-nowrap">{b.status === "Allocated" ? fmtDate(b.confirm_by) : "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">{b.status === "Submitted" ? "Submitted" : fmtDate(b.submit_by)}</td>
                <td className="px-3 py-2 whitespace-nowrap">{fmtDate(b.end_date)}<DaysLeft bid={b} /></td>
                <td className="px-3 py-2 text-right"><Link to={`/bids/${b.id}`} className={btnGhost}>{side.canOverride ? "Open / override" : "Open"}</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
