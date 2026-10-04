import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { BidTabs, Notice, PageTitle, btnPrimary, errText, fieldClass, fmtDate } from "./bidUi.jsx";

const TONES = {
  Requested: "bg-amber-100 text-amber-800",
  Allocated: "bg-emerald-100 text-emerald-800",
  Declined: "bg-slate-200 text-slate-700",
  "Not available": "bg-rose-100 text-rose-700",
};

const AVAIL = {
  available: ["Free for allocation", "bg-emerald-100 text-emerald-800"],
  allocated: ["Already allocated", "bg-rose-100 text-rose-700"],
  mine: ["Allocated to you", "bg-sky-100 text-sky-800"],
  closed: ["Closed", "bg-slate-200 text-slate-700"],
};

export default function VendorRequest() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState(null);
  const [mine, setMine] = useState([]);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadMine = useCallback(() => { bidsApi.requests({}).then(setMine).catch(() => {}); }, []);
  useEffect(() => { loadMine(); }, [loadMine]);

  // searches while typing: spaces, slashes and a mistyped character or two are fine
  useEffect(() => {
    if (q.trim().length < 2) { setHits(null); return undefined; }
    const timer = setTimeout(() => { bidsApi.lookup(q).then(setHits).catch((e) => setMsg({ tone: "bad", text: errText(e) })); }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  async function request(number) {
    setBusy(true);
    setMsg(null);
    try {
      await bidsApi.requestCreate(number, note);
      setMsg({ tone: "ok", text: `Your request for ${number} went to the INDcool bid team.` });
      setNote("");
      loadMine();
      bidsApi.lookup(q).then(setHits).catch(() => {});
    } catch (e) {
      setMsg({ tone: "bad", text: errText(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageTitle title="Request a bid" sub="Type the bid number. If it is free, ask INDcool for it. If INDcool has not entered it yet, send the number." />
      <BidTabs manager={false} />
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

      <div className="mb-6 rounded-lg bg-white p-4 shadow-sm">
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="bid-q">Bid number</label>
        <input id="bid-q" value={q} onChange={(e) => setQ(e.target.value)} className={`${fieldClass} md:max-w-lg`} placeholder="For example 5821904 or GEM/2026/B/5821904" autoComplete="off" />
        <input value={note} onChange={(e) => setNote(e.target.value)} className={`${fieldClass} mt-2 md:max-w-lg`} placeholder="Note for the bid team (optional)" />

        {hits && hits.length > 0 && (
          <ul className="mt-3 divide-y divide-slate-100 rounded-md border border-slate-200">
            {hits.map((h) => {
              const [label, tone] = AVAIL[h.availability] || AVAIL.closed;
              return (
                <li key={h.bid_number} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                  <div className="min-w-0">
                    <div className="font-mono text-sm font-semibold">{h.bid_number}</div>
                    <div className="truncate text-xs text-slate-600">{h.title}</div>
                    <div className="text-xs text-slate-500">{h.bid_type} · closes {fmtDate(h.end_date)}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}>{label}</span>
                    {h.availability === "available" && !h.already_requested && (
                      <button type="button" disabled={busy} onClick={() => request(h.bid_number)} className={btnPrimary}>Request this bid</button>
                    )}
                    {h.availability === "available" && h.already_requested && <span className="text-xs text-slate-500">You asked already</span>}
                    {h.availability === "mine" && h.bid_id && <Link to={`/bids/${h.bid_id}`} className="text-sm text-brand-700 underline">Open</Link>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {hits && hits.length === 0 && q.trim().length >= 3 && (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            No bid with that number is in the system yet. You can send the number to INDcool and the bid team will enter it.
            <div className="mt-2"><button type="button" disabled={busy} onClick={() => request(q.trim())} className={btnPrimary}>Send bid number to INDcool</button></div>
          </div>
        )}
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Your requests</h2>
      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-xs font-semibold text-slate-600">
            <tr><th className="px-3 py-2">Asked on</th><th className="px-3 py-2">Bid number</th><th className="px-3 py-2">Note</th><th className="px-3 py-2">Answer</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {mine.length === 0 && <tr><td colSpan={4} className="px-3 py-6 text-center text-slate-500">You have not asked for any bid yet.</td></tr>}
            {mine.map((r) => (
              <tr key={r.id}>
                <td className="px-3 py-2 whitespace-nowrap">{fmtDate(r.created_at)}</td>
                <td className="px-3 py-2 font-mono">{r.bid_number}</td>
                <td className="px-3 py-2">{r.note || "—"}</td>
                <td className="px-3 py-2"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[r.status] || "bg-slate-100"}`}>{r.status === "Requested" ? "Waiting for INDcool" : r.status}</span>{r.decision_note && <div className="text-xs text-slate-500">{r.decision_note}</div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
