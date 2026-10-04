import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { BidTabs, Notice, PageTitle, STATUS_TONE, btnGhost, errText, fmtDate, isoDate, useBidSide } from "./bidUi.jsx";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export default function BidCalendar() {
  const side = useBidSide();
  const [bids, setBids] = useState([]);
  const [err, setErr] = useState("");
  const now = new Date();
  const [cursor, setCursor] = useState({ y: now.getFullYear(), m: now.getMonth() });

  useEffect(() => { bidsApi.list({}).then(setBids).catch((e) => setErr(errText(e))); }, []);

  // every date that matters for a bid: the end date, plus confirm-by and submit-by while it is held
  const marks = useMemo(() => {
    const byDay = {};
    const add = (day, mark) => { if (day) (byDay[day] = byDay[day] || []).push(mark); };
    bids.forEach((b) => {
      add(b.end_date, { bid: b, kind: "ends" });
      if (b.status === "Allocated") add(b.confirm_by, { bid: b, kind: "confirm" });
      if (b.status === "Allocated" || b.status === "Confirmed") add(b.submit_by, { bid: b, kind: "submit" });
    });
    return byDay;
  }, [bids]);

  const first = new Date(cursor.y, cursor.m, 1);
  const lead = (first.getDay() + 6) % 7;
  const total = new Date(cursor.y, cursor.m + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < lead; i += 1) cells.push(null);
  for (let d = 1; d <= total; d += 1) cells.push(new Date(cursor.y, cursor.m, d));
  const today = isoDate(now);

  function shift(n) {
    const d = new Date(cursor.y, cursor.m + n, 1);
    setCursor({ y: d.getFullYear(), m: d.getMonth() });
  }

  const label = { ends: "closes", confirm: "confirm by", submit: "submit by" };
  const monthMarks = Object.entries(marks)
    .filter(([day]) => day.startsWith(`${cursor.y}-${String(cursor.m + 1).padStart(2, "0")}`))
    .sort(([a], [b]) => a.localeCompare(b));

  return (
    <div>
      <PageTitle title="Bid calendar" sub="Closing dates, and the confirm-by and submit-by dates of allocated bids.">
        <button type="button" className={btnGhost} onClick={() => shift(-1)}>‹ Previous</button>
        <button type="button" className={btnGhost} onClick={() => setCursor({ y: now.getFullYear(), m: now.getMonth() })}>Today</button>
        <button type="button" className={btnGhost} onClick={() => shift(1)}>Next ›</button>
      </PageTitle>
      <BidTabs manager={side.manager} />
      <Notice tone="bad">{err}</Notice>
      <h2 className="mb-2 text-lg font-semibold text-slate-800">{MONTH_NAMES[cursor.m]} {cursor.y}</h2>

      <div className="hidden overflow-hidden rounded-lg border border-slate-200 bg-white md:block">
        <div className="grid grid-cols-7 border-b bg-slate-50 text-center text-xs font-semibold text-slate-600">
          {DAYS.map((d) => <div key={d} className="px-2 py-2">{d}</div>)}
        </div>
        <div className="grid grid-cols-7">
          {cells.map((d, i) => {
            const key = d ? isoDate(d) : `x${i}`;
            const list = d ? marks[key] || [] : [];
            return (
              <div key={key} className={`min-h-[96px] border-b border-r border-slate-100 p-1 ${d && key === today ? "bg-sky-50" : ""}`}>
                {d && <div className={`mb-1 text-xs ${key === today ? "font-bold text-brand-700" : "text-slate-500"}`}>{d.getDate()}</div>}
                <div className="space-y-1">
                  {list.slice(0, 4).map((mk, j) => (
                    <Link
                      key={j}
                      to={`/bids/${mk.bid.id}`}
                      title={`${mk.bid.bid_number}: ${mk.bid.title}`}
                      className={`block truncate rounded border px-1 py-0.5 text-[11px] ${mk.kind === "ends" ? STATUS_TONE[mk.bid.status] : "border-dashed border-amber-300 bg-amber-50 text-amber-800"}`}
                    >
                      {mk.bid.bid_number.split("/").pop()} {label[mk.kind]}
                    </Link>
                  ))}
                  {list.length > 4 && <div className="text-[11px] text-slate-500">+{list.length - 4} more</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 space-y-2 md:mt-6">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">This month in a list</h3>
        {monthMarks.length === 0 && <p className="text-sm text-slate-500">No bid dates in this month.</p>}
        {monthMarks.map(([day, list]) => (
          <div key={day} className="rounded-lg bg-white p-3 shadow-sm">
            <div className="mb-1 text-sm font-semibold text-slate-700">{fmtDate(day)}</div>
            {list.map((mk, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 py-0.5 text-sm">
                <Link to={`/bids/${mk.bid.id}`} className="font-mono text-brand-700 hover:underline">{mk.bid.bid_number}</Link>
                <span className="text-slate-500">{label[mk.kind]}</span>
                <span className="truncate text-slate-600">{mk.bid.title}</span>
                {side.manager && mk.bid.vendor_name && <span className="text-xs text-slate-500">({mk.bid.vendor_name})</span>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
