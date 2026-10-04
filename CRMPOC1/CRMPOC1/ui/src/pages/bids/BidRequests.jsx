import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import Modal from "../../components/Modal.jsx";
import { BidTabs, Notice, PageTitle, btnGhost, btnPrimary, errText, fieldClass, fmtDate, useBidSide } from "./bidUi.jsx";

const TONES = {
  Requested: "bg-amber-100 text-amber-800",
  Allocated: "bg-emerald-100 text-emerald-800",
  Declined: "bg-slate-200 text-slate-700",
  "Not available": "bg-rose-100 text-rose-700",
};

export default function BidRequests() {
  const side = useBidSide();
  const [rows, setRows] = useState([]);
  const [state, setState] = useState("Requested");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(0);
  const [declining, setDeclining] = useState(null);
  const [declineNote, setDeclineNote] = useState("");

  const load = useCallback(() => {
    bidsApi.requests(state === "All" ? {} : { state }).then(setRows).catch((e) => setMsg({ tone: "bad", text: errText(e) }));
  }, [state]);
  useEffect(() => { load(); }, [load]);

  async function act(row, kind) {
    setBusy(row.id);
    setMsg(null);
    try {
      if (kind === "allocate") {
        await bidsApi.requestAllocate(row.id);
        setMsg({ tone: "ok", text: `${row.bid_number} is allocated to ${row.vendor_name}. Other vendors who asked were told it is not available.` });
      } else {
        await bidsApi.requestDecline(row.id, declineNote);
        setMsg({ tone: "ok", text: `Declined. ${row.vendor_name} was told.` });
        setDeclining(null);
        setDeclineNote("");
      }
      load();
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e) });
    } finally {
      setBusy(0);
    }
  }

  return (
    <div>
      <PageTitle title="Vendor requests" sub="Vendors type a bid number and ask for it. A bid that is already locked is never given away here." />
      <BidTabs manager />
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {["Requested", "Allocated", "Declined", "Not available", "All"].map((s) => (
          <button key={s} type="button" onClick={() => setState(s)} className={`rounded-full border px-3 py-1 text-xs ${state === s ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"}`}>{s}</button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-xs font-semibold text-slate-600">
            <tr><th className="px-3 py-2">Asked on</th><th className="px-3 py-2">Bid number</th><th className="px-3 py-2">Vendor</th><th className="px-3 py-2">Note</th><th className="px-3 py-2">State</th><th className="px-3 py-2" /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-500">No requests here.</td></tr>}
            {rows.map((r) => {
              const locked = r.bid_status && !["Open", "Closed", "Won", "Lost"].includes(r.bid_status);
              return (
                <tr key={r.id} className="align-top hover:bg-slate-50">
                  <td className="px-3 py-2 whitespace-nowrap">{fmtDate(r.created_at)}</td>
                  <td className="px-3 py-2">
                    {r.bid_id ? <Link to={`/bids/${r.bid_id}`} className="font-mono text-brand-700 hover:underline">{r.bid_number}</Link> : <span className="font-mono">{r.bid_number}</span>}
                    {r.bid_title && <div className="max-w-[240px] truncate text-xs text-slate-500">{r.bid_title}</div>}
                    {!r.bid_id && <div className="text-xs text-amber-700">Not entered yet</div>}
                    {r.asked_by_others > 0 && r.status === "Requested" && <div className="text-xs text-indigo-700">{r.asked_by_others + 1} vendors asked</div>}
                  </td>
                  <td className="px-3 py-2">{r.vendor_name}</td>
                  <td className="px-3 py-2 max-w-[220px]">{r.note || <span className="text-slate-400">—</span>}{r.decision_note && <div className="text-xs text-slate-500">Answer: {r.decision_note}</div>}</td>
                  <td className="px-3 py-2"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[r.status] || "bg-slate-100"}`}>{r.status}</span></td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {r.status === "Requested" && !r.bid_id && <Link to={`/bids/new?number=${encodeURIComponent(r.bid_number)}`} className={btnPrimary}>Enter this bid</Link>}
                    {r.status === "Requested" && r.bid_id && !locked && (
                      <button type="button" disabled={busy === r.id} onClick={() => act(r, "allocate")} className={btnPrimary}>Allocate to {r.vendor_name}</button>
                    )}
                    {r.status === "Requested" && locked && (
                      <span className="mr-2 text-xs text-slate-600">Already allocated{r.holder ? ` to ${r.holder}` : ""}{side.canOverride && <> · <Link to={`/bids/${r.bid_id}`} className="text-brand-700 underline">Open to override</Link></>}</span>
                    )}
                    {r.status === "Requested" && <button type="button" disabled={busy === r.id} onClick={() => setDeclining(r)} className={`${btnGhost} ml-2`}>Decline</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Modal open={!!declining} onClose={() => setDeclining(null)} title={`Decline ${declining?.bid_number || ""}`}>
        <p className="mb-2 text-sm text-slate-600">{declining?.vendor_name} will be told by email. Add a reason if you like.</p>
        <textarea rows={3} value={declineNote} onChange={(e) => setDeclineNote(e.target.value)} className={fieldClass} placeholder="Reason (optional)" />
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={() => setDeclining(null)} className={btnGhost}>Cancel</button>
          <button type="button" disabled={busy === declining?.id} onClick={() => act(declining, "decline")} className={btnPrimary}>Decline request</button>
        </div>
      </Modal>
    </div>
  );
}
