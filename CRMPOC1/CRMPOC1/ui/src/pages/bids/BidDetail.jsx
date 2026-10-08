import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import {
  BidTabs,
  DaysLeft,
  Notice,
  PageTitle,
  StatusPill,
  Steps,
  btnDanger,
  btnGhost,
  btnPrimary,
  errText,
  fieldClass,
  fmtDate,
  labelClass,
  money,
  useBidSide,
  fmtDateTime,
} from "./bidUi.jsx";

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5 py-1.5 sm:flex-row sm:gap-3">
      <dt className="w-44 shrink-0 text-sm text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-sm text-slate-800">{children || "—"}</dd>
    </div>
  );
}

function Card({ title, children, tone = "" }) {
  return (
    <section className={`rounded-lg bg-white p-4 shadow-sm ${tone}`}>
      {title && <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>}
      {children}
    </section>
  );
}

export default function BidDetail() {
  const { id } = useParams();
  const side = useBidSide();
  const [bid, setBid] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pickVendor, setPickVendor] = useState("");
  const [reason, setReason] = useState("");
  const [releaseReason, setReleaseReason] = useState("");
  const [overrideVendor, setOverrideVendor] = useState("");
  const [reference, setReference] = useState("");
  const [resultNote, setResultNote] = useState("");

  const load = useCallback(async () => {
    try {
      setBid(await bidsApi.get(id));
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e, "Could not load the bid") });
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (side.manager) bidsApi.vendors().then(setVendors).catch(() => {}); }, [side.manager]);

  async function run(fn, okText) {
    setBusy(true);
    setMsg(null);
    try {
      const next = await fn();
      setBid(next);
      setMsg({ tone: "ok", text: okText });
      setReason("");
      setReleaseReason("");
      setReference("");
      setResultNote("");
      setPickVendor("");
      setOverrideVendor("");
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e) });
      load();
    } finally {
      setBusy(false);
    }
  }

  if (!bid) {
    return <div>{msg ? <Notice tone={msg.tone}>{msg.text}</Notice> : <p className="text-slate-500">Loading…</p>}<Link to="/bids" className={btnGhost}>Back to bids</Link></div>;
  }

  const held = ["Allocated", "Confirmed", "Submitted"].includes(bid.status);
  const manager = side.manager;
  const vendorSelect = (value, onChange, label = "Vendor") => (
    <div>
      <label className={labelClass}>{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={fieldClass}>
        <option value="">Choose a vendor</option>
        {vendors.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.vendor_code})</option>)}
      </select>
    </div>
  );

  return (
    <div>
      <PageTitle title={bid.bid_number} sub={bid.title}>
        {manager && <Link to={`/bids/${bid.id}/edit`} className={btnGhost}>Edit bid</Link>}
        <Link to="/bids" className={btnGhost}>Back</Link>
      </PageTitle>
      <BidTabs manager={manager} />
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <StatusPill bid={bid} />
        <DaysLeft bid={bid} />
        {bid.vendor_name && <span className="text-sm text-slate-600">Bidder: <strong>{bid.vendor_name}</strong></span>}
        {manager && bid.pending_requests > 0 && (
          <Link to="/bids/requests" className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs text-indigo-700">
            {bid.pending_requests} vendor{bid.pending_requests > 1 ? "s" : ""} asked for this bid
          </Link>
        )}
      </div>

      <div className="mb-4"><Steps bid={bid} /></div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Bid details">
            <dl className="divide-y divide-slate-100">
              <Row label="Bid category">{bid.bid_type}{bid.portal ? `, ${bid.portal}` : ""}</Row>
              <Row label="Item">{bid.title}</Row>
              <Row label="Buyer / department">{bid.department}</Row>
              <Row label="Product">{bid.product_category}{bid.product_type && bid.product_type !== "Other" ? ` / ${bid.product_type}` : ""}</Row>
              {bid.lines?.length > 0 && (
                <Row label="Items">
                  <ul className="space-y-0.5">
                    {bid.lines.map((l, i) => (
                      <li key={i}>{l.item}{l.quantity != null ? <span className="text-slate-500"> × {l.quantity}</span> : null}</li>
                    ))}
                  </ul>
                </Row>
              )}
              <Row label="Quantity">{bid.quantity}</Row>
              <Row label="Estimated value">{money(bid.estimated_value)}</Row>
              <Row label="Published">{fmtDate(bid.publish_date)}</Row>
              <Row label="Bid end date">{fmtDate(bid.end_date)}</Row>
              <Row label="Bid opening">{fmtDate(bid.opening_date)}</Row>
              <Row label="EMD">{[bid.emd_exempt ? "Exempted" : (bid.emd_amount !== null && bid.emd_amount !== undefined ? money(bid.emd_amount) : null), bid.emd_mode].filter(Boolean).join(", ")}</Row>
              <Row label="ePBG">{bid.epbg_details}</Row>
              <Row label="Tender fee">{money(bid.tender_fee)}</Row>
              {manager && <Row label="Internal notes">{bid.notes}</Row>}
            </dl>
          </Card>

          <Card title="History">
            {bid.events.length === 0 && <p className="text-sm text-slate-500">Nothing yet.</p>}
            <ol className="space-y-2">
              {[...bid.events].reverse().map((e) => (
                <li key={e.id} className="flex gap-3 text-sm">
                  <span className="w-24 shrink-0 text-xs text-slate-500">{fmtDate(e.at)}</span>
                  <span><strong className="text-slate-700">{e.actor_name}</strong>: {e.text}</span>
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div className="space-y-4">
          {held && (
            <Card title="Deadlines">
              <dl className="divide-y divide-slate-100">
                <Row label="Bidder">{bid.vendor_name}</Row>
                {bid.status === "Allocated" && <Row label="Accept or reject by">{bid.confirm_due_at ? fmtDateTime(bid.confirm_due_at) : fmtDate(bid.confirm_by)}</Row>}
                {bid.status !== "Submitted" && <Row label="Submit by">{fmtDate(bid.submit_by)}</Row>}
                <Row label="Bid ends">{fmtDate(bid.end_date)}</Row>
                {bid.submission_ref && <Row label="Acknowledgement">{bid.submission_ref}</Row>}
              </dl>
              {bid.status === "Allocated" && <p className="mt-2 text-xs text-slate-500">If there is no answer in time, the bid is withdrawn and opened for allocation to another eligible vendor.</p>}
              {bid.status === "Confirmed" && !bid.is_self && <p className="mt-2 text-xs text-slate-500">If it is not marked submitted in time, the bid is withdrawn and opened for allocation to another eligible vendor.</p>}
            </Card>
          )}

          {/* vendor actions */}
          {!manager && bid.status === "Allocated" && (
            <Card title="Your answer" tone="ring-2 ring-brand-500">
              <p className="mb-3 text-sm text-slate-700">INDcool has allocated this bid to you. Please accept or reject it by {bid.confirm_due_at ? fmtDateTime(bid.confirm_due_at) : fmtDate(bid.confirm_by)}.</p>
              <div className="space-y-2">
                <button type="button" disabled={busy} onClick={() => run(() => bidsApi.confirm(bid.id), "Confirmed. Please submit on the portal by " + fmtDate(bid.submit_by) + ".")} className={`${btnPrimary} w-full`}>Accept: I will bid</button>
                <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason, if you reject (optional)" className={fieldClass} />
                <button type="button" disabled={busy} onClick={() => run(() => bidsApi.decline(bid.id, reason), "You rejected the bid. It went back to INDcool.")} className={`${btnGhost} w-full`}>Reject this bid</button>
              </div>
            </Card>
          )}
          {!manager && bid.status === "Confirmed" && (
            <Card title="Submit on the portal" tone="ring-2 ring-brand-500">
              <p className="mb-2 text-sm text-slate-700">After you submit this bid on the portal, mark it here.</p>
              <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Acknowledgement number (optional)" className={`${fieldClass} mb-2`} />
              <button type="button" disabled={busy} onClick={() => run(() => bidsApi.submit(bid.id, reference), "Marked as submitted.")} className={`${btnPrimary} w-full`}>I have submitted it</button>
            </Card>
          )}

          {/* bid team actions */}
          {manager && bid.status === "Open" && (
            <Card title="Allocate" tone="ring-2 ring-brand-500">
              <p className="mb-2 text-xs text-slate-500">One bid, one bidder. Allocating locks the bid and emails the vendor.</p>
              {vendorSelect(pickVendor, setPickVendor)}
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" disabled={busy || !pickVendor} onClick={() => run(() => bidsApi.allocate(bid.id, { vendor_id: Number(pickVendor) }), "Allocated and the vendor was emailed.")} className={btnPrimary}>Allocate</button>
                <button type="button" disabled={busy} onClick={() => run(() => bidsApi.allocate(bid.id, { self_bid: true }), "INDcool will bid itself. It is confirmed.")} className={btnGhost}>INDcool bids itself</button>
              </div>
            </Card>
          )}
          {manager && held && (
            <Card title="Bid team actions">
              <div className="space-y-3">
                {bid.status === "Allocated" && (
                  <button type="button" disabled={busy} onClick={() => run(() => bidsApi.confirm(bid.id), "Confirmed for the vendor.")} className={`${btnGhost} w-full`}>Confirm for the vendor</button>
                )}
                {bid.status === "Confirmed" && (
                  <div className="space-y-2">
                    <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Acknowledgement number (optional)" className={fieldClass} />
                    <button type="button" disabled={busy} onClick={() => run(() => bidsApi.submit(bid.id, reference), "Marked as submitted.")} className={`${btnPrimary} w-full`}>Mark as submitted</button>
                  </div>
                )}
                {bid.status === "Submitted" && (
                  <div className="space-y-2">
                    <input value={resultNote} onChange={(e) => setResultNote(e.target.value)} placeholder="Result note (optional)" className={fieldClass} />
                    <div className="flex gap-2">
                      <button type="button" disabled={busy} onClick={() => run(() => bidsApi.result(bid.id, "Won", resultNote), "Result saved: Won.")} className={`${btnPrimary} flex-1`}>Won</button>
                      <button type="button" disabled={busy} onClick={() => run(() => bidsApi.result(bid.id, "Lost", resultNote), "Result saved: Lost.")} className={`${btnGhost} flex-1`}>Lost</button>
                    </div>
                  </div>
                )}
                {(bid.status !== "Submitted" || side.canOverride) && (
                  <div className="space-y-2 border-t border-slate-100 pt-3">
                    <input value={releaseReason} onChange={(e) => setReleaseReason(e.target.value)} placeholder="Why is it released? (optional)" className={fieldClass} />
                    <button type="button" disabled={busy} onClick={() => run(() => bidsApi.release(bid.id, releaseReason), "Released. The bid is free for allocation again.")} className={`${btnGhost} w-full`}>Release the bid</button>
                  </div>
                )}
              </div>
            </Card>
          )}
          {manager && side.canOverride && ["Allocated", "Confirmed", "Submitted"].includes(bid.status) && (
            <Card title="Admin override" tone="border border-rose-200">
              <p className="mb-2 text-xs text-rose-700">This bid is locked to {bid.vendor_name}. As admin you can give it to someone else. A reason is required and both vendors are told.</p>
              {vendorSelect(overrideVendor, setOverrideVendor, "Give it to")}
              <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for the override" className={`${fieldClass} mt-2`} />
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || !overrideVendor || !reason.trim()}
                  onClick={() => run(() => bidsApi.allocate(bid.id, { vendor_id: Number(overrideVendor), reason }), "Override done. The earlier bidder was told.")}
                  className={btnDanger}
                >
                  Override and allocate
                </button>
                <button
                  type="button"
                  disabled={busy || !reason.trim()}
                  onClick={() => run(() => bidsApi.allocate(bid.id, { self_bid: true, reason }), "Override done. INDcool bids itself.")}
                  className={btnGhost}
                >
                  Override to INDcool
                </button>
              </div>
            </Card>
          )}
          {manager && !side.canOverride && held && (
            <Card><p className="text-xs text-slate-500">This bid is locked. Only an admin or sub admin can give it to someone else.</p></Card>
          )}
          {bid.status === "Won" || bid.status === "Lost" ? (
            <Card title="Result"><p className="text-sm">{bid.status}{bid.result_note ? `: ${bid.result_note}` : ""}</p></Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
