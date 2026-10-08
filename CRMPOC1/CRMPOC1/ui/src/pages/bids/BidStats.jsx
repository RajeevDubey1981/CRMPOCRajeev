import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { bidsApi } from "../../api/bids.js";
import { BidTabs, Notice, PageTitle, errText, fieldClass, isoDate, useBidSide } from "./bidUi.jsx";

// One step of the bid journey = one shade of blue, light to dark, the same in every chart on this page.
const STEP = {
  allocated: { label: "Allocated", color: "#86b6ef" },
  confirmed: { label: "Confirmed", color: "#3987e5" },
  submitted: { label: "Submitted (fulfilled)", color: "#1c5cab" },
  won: { label: "Won", color: "#104281" },
};
const LEAK = {
  declined: { label: "Declined", color: "#eb6834", hint: "said no when asked to confirm" },
  expired: { label: "Expired", color: "#4a3aa7", hint: "let the confirm or submit date pass, bid went back" },
};
const AXIS = { fontSize: 12, fill: "#52514e" };

const PERIODS = [
  { key: "all", label: "All time" },
  { key: "month", label: "This month" },
  { key: "30", label: "Last 30 days" },
  { key: "90", label: "Last 90 days" },
  { key: "year", label: "This year" },
  { key: "custom", label: "Pick dates" },
];

function periodRange(key, custom) {
  const today = new Date();
  const back = (days) => { const d = new Date(today); d.setDate(d.getDate() - days); return isoDate(d); };
  if (key === "month") return { from: isoDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: isoDate(today) };
  if (key === "30") return { from: back(30), to: isoDate(today) };
  if (key === "90") return { from: back(90), to: isoDate(today) };
  if (key === "year") return { from: isoDate(new Date(today.getFullYear(), 0, 1)), to: isoDate(today) };
  if (key === "custom") return { from: custom.from || undefined, to: custom.to || undefined };
  return {};
}

function pct(value) {
  return value === null || value === undefined ? "-" : `${value}%`;
}

function Tile({ label, value, color, hint, rate }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm" title={hint}>
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
        <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} aria-hidden="true" />
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-800">{value}</div>
      <div className="h-4 text-xs text-slate-500">{rate || ""}</div>
    </div>
  );
}

function ChartCard({ title, sub, children, legend }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {sub && <p className="text-xs text-slate-500">{sub}</p>}
        </div>
        {legend && (
          <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
            {legend.map((item) => (
              <li key={item.label} className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: item.color }} aria-hidden="true" />
                {item.label}
              </li>
            ))}
          </ul>
        )}
      </div>
      {children}
    </section>
  );
}

function TooltipBox({ active, payload, label, title }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-semibold text-slate-800">{title || label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-slate-600">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: p.fill || p.color }} aria-hidden="true" />
            {STEP[p.dataKey]?.label || p.name}
          </span>
          <span className="font-semibold tabular-nums text-slate-800">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function Empty({ children }) {
  return <div className="flex h-40 items-center justify-center text-sm text-slate-500">{children}</div>;
}

export default function BidStats() {
  const side = useBidSide();
  const manager = side.manager;
  const [vendors, setVendors] = useState([]);
  const [vendorId, setVendorId] = useState("");
  const [period, setPeriod] = useState("all");
  const [custom, setCustom] = useState({ from: "", to: "" });
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (manager) bidsApi.vendors().then(setVendors).catch(() => {});
  }, [manager]);

  useEffect(() => {
    let alive = true;
    const range = periodRange(period, custom);
    if (period === "custom" && range.from && range.to && range.to < range.from) {
      setErr("The end date is before the start date");
      return undefined;
    }
    setErr("");
    bidsApi.stats({ vendor_id: manager && vendorId ? vendorId : undefined, from: range.from, to: range.to })
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(errText(e, "Could not load the figures")); });
    return () => { alive = false; };
  }, [manager, vendorId, period, custom]);

  const totals = data?.totals;
  const rows = data?.vendors || [];
  const picked = vendors.find((v) => String(v.id) === String(vendorId));
  const scope = manager ? (picked ? picked.name : "All vendors") : "Your bids";

  const funnel = useMemo(() => (totals
    ? Object.keys(STEP).map((key) => ({
      key,
      name: STEP[key].label,
      value: totals[key],
      color: STEP[key].color,
      of: totals.allocated ? Math.round((totals[key] * 100) / totals.allocated) : null,
    }))
    : []), [totals]);

  const compare = useMemo(() => rows.filter((r) => r.allocated > 0).slice(0, 10), [rows]);
  const hasActivity = !!totals && (totals.allocated + totals.holding + totals.declined + totals.expired) > 0;

  return (
    <div>
      <PageTitle title={manager ? "Bid statistics" : "My bid statistics"} sub={manager ? "How each vendor is doing with the bids given to them." : "How the bids given to you have gone."} />
      <BidTabs manager={manager} />
      {err && <Notice tone="bad">{err}</Notice>}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg bg-white p-3 shadow-sm">
        {manager && (
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">Vendor</span>
            <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} className={`${fieldClass} md:w-64`}>
              <option value="">All vendors</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </label>
        )}
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Period</span>
          <select value={period} onChange={(e) => setPeriod(e.target.value)} className={`${fieldClass} md:w-44`}>
            {PERIODS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
          </select>
        </label>
        {period === "custom" && (
          <>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-700">From</span>
              <input type="date" value={custom.from} onChange={(e) => setCustom((c) => ({ ...c, from: e.target.value }))} className={fieldClass} />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-700">To</span>
              <input type="date" value={custom.to} onChange={(e) => setCustom((c) => ({ ...c, to: e.target.value }))} className={fieldClass} />
            </label>
          </>
        )}
        <div className="ml-auto text-sm text-slate-600">
          Showing <span className="font-semibold text-slate-800">{scope}</span>
          {manager && picked && <> · <Link to={`/bids?vendor_id=${picked.id}&state=All`} className="text-brand-700 underline">see their bids</Link></>}
        </div>
      </div>

      {!data ? (
        <p className="p-6 text-sm text-slate-500">Loading...</p>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
            <Tile label="Allocated" value={totals.allocated} color={STEP.allocated.color} hint="Bids given to the vendor" />
            <Tile label="Confirmed" value={totals.confirmed} color={STEP.confirmed.color} rate={`${pct(totals.confirm_rate)} of allocated`} />
            <Tile label="Submitted" value={totals.submitted} color={STEP.submitted.color} hint="Bids the vendor put in on the portal" rate={`${pct(totals.submit_rate)} of confirmed`} />
            <Tile label="Won" value={totals.won} color={STEP.won.color} rate={`${pct(totals.win_rate)} of results`} />
            <Tile label="Declined" value={totals.declined} color={LEAK.declined.color} hint={LEAK.declined.hint} />
            <Tile label="Expired" value={totals.expired} color={LEAK.expired.color} hint={LEAK.expired.hint} />
            <Tile label="Holding now" value={totals.holding} color="#52514e" hint="Allocated, confirmed or submitted and waiting right now" />
          </div>

          {!hasActivity ? (
            <Notice tone="info">{manager ? "No bid has been allocated for these choices yet." : "No bid has been allocated to you yet. When one is, your figures and graphs show here."}</Notice>
          ) : (
            <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {manager && !picked && (
                <div className="lg:col-span-2">
                  <ChartCard
                    title="Vendor comparison"
                    sub={`Bids per vendor, the ${compare.length} with the most allocated`}
                    legend={Object.values(STEP)}
                  >
                    {compare.length === 0 ? <Empty>Nothing was allocated in this period.</Empty> : (
                      <div role="img" aria-label="Bars of allocated, confirmed, submitted and won bids for each vendor" style={{ height: Math.max(220, compare.length * 62) }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={compare} layout="vertical" margin={{ top: 4, right: 36, bottom: 4, left: 8 }} barGap={2} barCategoryGap="22%">
                            <CartesianGrid horizontal={false} stroke="#e7e6e2" />
                            <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                            <YAxis type="category" dataKey="vendor_name" width={150} tick={AXIS} axisLine={false} tickLine={false} />
                            <Tooltip cursor={{ fill: "rgba(15,23,42,0.05)" }} content={<TooltipBox />} />
                            {Object.keys(STEP).map((key) => (
                              <Bar key={key} dataKey={key} name={STEP[key].label} fill={STEP[key].color} radius={[0, 4, 4, 0]} maxBarSize={14}>
                                {key === "allocated" && <LabelList dataKey={key} position="right" style={{ fontSize: 11, fill: "#52514e" }} />}
                              </Bar>
                            ))}
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </ChartCard>
                </div>
              )}

              <ChartCard title="From allocated to won" sub={`${scope}. The percentage is of everything allocated`}>
                <div role="img" aria-label="Funnel of allocated, confirmed, submitted and won bids" style={{ height: 230 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={funnel} layout="vertical" margin={{ top: 4, right: 72, bottom: 4, left: 8 }} barCategoryGap="28%">
                      <CartesianGrid horizontal={false} stroke="#e7e6e2" />
                      <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="name" width={130} tick={AXIS} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: "rgba(15,23,42,0.05)" }} content={({ active, payload }) => (active && payload?.length ? (
                        <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg">
                          <div className="font-semibold text-slate-800">{payload[0].payload.name}</div>
                          <div className="text-slate-600">{payload[0].value} bids{payload[0].payload.of !== null ? ` · ${payload[0].payload.of}% of allocated` : ""}</div>
                        </div>
                      ) : null)}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={26}>
                        {funnel.map((f) => <Cell key={f.key} fill={f.color} />)}
                        <LabelList
                          dataKey="value"
                          position="right"
                          content={({ x, y, width, height, value, index }) => (
                            <text x={x + width + 6} y={y + height / 2} dy={4} style={{ fontSize: 12, fill: "#0b0b0b", fontWeight: 600 }}>
                              {value}{funnel[index]?.of !== null && funnel[index]?.key !== "allocated" ? ` (${funnel[index].of}%)` : ""}
                            </text>
                          )}
                        />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Not taken up: <span className="font-semibold text-slate-700">{totals.declined}</span> declined, <span className="font-semibold text-slate-700">{totals.expired}</span> expired, <span className="font-semibold text-slate-700">{totals.lost}</span> lost.
                </p>
              </ChartCard>

              <ChartCard title="Month by month" sub="The last 6 months, all dates (the period above does not change this)" legend={Object.values(STEP)}>
                <div role="img" aria-label="Bars of allocated, confirmed, submitted and won bids for each of the last six months" style={{ height: 230 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.monthly} margin={{ top: 8, right: 8, bottom: 4, left: -16 }} barGap={2} barCategoryGap="22%">
                      <CartesianGrid vertical={false} stroke="#e7e6e2" />
                      <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
                      <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: "rgba(15,23,42,0.05)" }} content={<TooltipBox />} />
                      {Object.keys(STEP).map((key) => (
                        <Bar key={key} dataKey={key} name={STEP[key].label} fill={STEP[key].color} radius={[4, 4, 0, 0]} maxBarSize={16} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            </div>
          )}

          {manager && (
            <section className="overflow-hidden rounded-lg bg-white shadow-sm" aria-label="Vendor-wise table">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-800">Vendor-wise</h2>
                <p className="text-xs text-slate-500">The same figures as a table. Click a vendor to look at only theirs.</p>
              </div>
              <div className="crm-scroll overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Vendor</th>
                      <th className="px-3 py-2 text-right">Allocated</th>
                      <th className="px-3 py-2 text-right">Confirmed</th>
                      <th className="px-3 py-2 text-right">Submitted</th>
                      <th className="px-3 py-2 text-right">Won</th>
                      <th className="px-3 py-2 text-right">Lost</th>
                      <th className="px-3 py-2 text-right">Declined</th>
                      <th className="px-3 py-2 text-right">Expired</th>
                      <th className="px-3 py-2 text-right">Holding</th>
                      <th className="px-3 py-2 text-right">Confirm %</th>
                      <th className="px-3 py-2 text-right">Win %</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 tabular-nums">
                    {rows.map((r) => (
                      <tr key={r.vendor_id} className="hover:bg-sky-50">
                        <td className="px-3 py-2 font-medium text-slate-800">
                          <button type="button" onClick={() => setVendorId(String(r.vendor_id))} className="text-left hover:text-brand-700 hover:underline">{r.vendor_name}</button>
                        </td>
                        <td className="px-3 py-2 text-right">{r.allocated}</td>
                        <td className="px-3 py-2 text-right">{r.confirmed}</td>
                        <td className="px-3 py-2 text-right">{r.submitted}</td>
                        <td className="px-3 py-2 text-right font-semibold text-emerald-700">{r.won}</td>
                        <td className="px-3 py-2 text-right">{r.lost}</td>
                        <td className="px-3 py-2 text-right text-orange-700">{r.declined}</td>
                        <td className="px-3 py-2 text-right text-violet-800">{r.expired}</td>
                        <td className="px-3 py-2 text-right">{r.holding}</td>
                        <td className="px-3 py-2 text-right">{pct(r.confirm_rate)}</td>
                        <td className="px-3 py-2 text-right">{pct(r.win_rate)}</td>
                        <td className="px-3 py-2 text-right"><Link to={`/bids?vendor_id=${r.vendor_id}&state=All`} className="text-xs text-brand-700 underline">Bids</Link></td>
                      </tr>
                    ))}
                    {rows.length === 0 && <tr><td colSpan={12} className="px-3 py-6 text-center text-slate-500">No vendor has any bid for these choices.</td></tr>}
                  </tbody>
                  {rows.length > 1 && (
                    <tfoot className="bg-slate-50 font-semibold tabular-nums">
                      <tr>
                        <td className="px-3 py-2">All vendors</td>
                        <td className="px-3 py-2 text-right">{totals.allocated}</td>
                        <td className="px-3 py-2 text-right">{totals.confirmed}</td>
                        <td className="px-3 py-2 text-right">{totals.submitted}</td>
                        <td className="px-3 py-2 text-right">{totals.won}</td>
                        <td className="px-3 py-2 text-right">{totals.lost}</td>
                        <td className="px-3 py-2 text-right">{totals.declined}</td>
                        <td className="px-3 py-2 text-right">{totals.expired}</td>
                        <td className="px-3 py-2 text-right">{totals.holding}</td>
                        <td className="px-3 py-2 text-right">{pct(totals.confirm_rate)}</td>
                        <td className="px-3 py-2 text-right">{pct(totals.win_rate)}</td>
                        <td />
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
