import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

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
  money,
} from "./bidUi.jsx";

const STATE_CHIPS = ["Live", "Open", "Allocated", "Confirmed", "Submitted", "Won", "Lost", "Closed", "All"];

function Kpi({ label, value, tone, active, onClick, hint }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border bg-white p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow ${active ? "ring-2 ring-brand-500" : ""} ${tone}`}
    >
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-sm font-medium">{label}</div>
      {hint && <div className="text-xs opacity-75">{hint}</div>}
    </button>
  );
}

export default function BidList() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [meta, setMeta] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [all, setAll] = useState([]);
  const [rows, setRows] = useState([]);
  const [requestsOpen, setRequestsOpen] = useState(0);
  const [filters, setFilters] = useState({
    q: "",
    state: searchParams.get("state") || "Live",
    bid_type: "",
    category: "",
    product_type: "",
    vendor_id: searchParams.get("vendor_id") || "",
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { bidsApi.meta().then(setMeta).catch(() => {}); }, []);
  useEffect(() => { bidsApi.vendors().then(setVendors).catch(() => {}); }, []);

  const loadAll = useCallback(() => {
    bidsApi.list({}).then(setAll).catch(() => {});
    bidsApi.requests({ state: "Requested" }).then((r) => setRequestsOpen(r.length)).catch(() => {});
  }, []);
  useEffect(() => { loadAll(); }, [loadAll]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      setErr("");
      try {
        const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
        setRows(await bidsApi.list(params));
      } catch (e) {
        setErr(errText(e, "Could not load bids"));
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [filters]);

  const counts = useMemo(() => {
    const c = { Open: 0, Allocated: 0, Confirmed: 0, Submitted: 0, closing: 0 };
    all.forEach((b) => {
      if (c[b.status] !== undefined) c[b.status] += 1;
      if (["Open", "Allocated", "Confirmed"].includes(b.status) && b.days_left >= 0 && b.days_left <= 3) c.closing += 1;
    });
    return c;
  }, [all]);

  function set(key, value) {
    setFilters((f) => ({ ...f, [key]: value, ...(key === "category" ? { product_type: "" } : {}) }));
  }

  const categories = meta ? Object.keys(meta.types) : [];
  const typeOptions = meta && filters.category ? meta.types[filters.category] : [];

  return (
    <div>
      <PageTitle title="Bid Management" sub="One bid, one bidder. Enter bids, allocate them and follow them to the result.">
        <Link to="/bids/new" className={btnPrimary}>+ Enter bid</Link>
      </PageTitle>
      <BidTabs manager />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Kpi label="Open for allocation" value={counts.Open} tone="border-sky-200 text-sky-800" active={filters.state === "Open"} onClick={() => set("state", "Open")} />
        <Kpi label="Waiting to confirm" value={counts.Allocated} tone="border-amber-200 text-amber-800" active={filters.state === "Allocated"} onClick={() => set("state", "Allocated")} />
        <Kpi label="Confirmed, to submit" value={counts.Confirmed} tone="border-emerald-200 text-emerald-800" active={filters.state === "Confirmed"} onClick={() => set("state", "Confirmed")} />
        <Kpi label="Submitted" value={counts.Submitted} tone="border-teal-200 text-teal-800" active={filters.state === "Submitted"} onClick={() => set("state", "Submitted")} />
        <Kpi label="Closing in 3 days" value={counts.closing} tone="border-rose-200 text-rose-700" hint="not yet submitted" onClick={() => set("state", "Live")} />
        <Kpi label="Vendor requests" value={requestsOpen} tone="border-indigo-200 text-indigo-800" hint="waiting for an answer" onClick={() => navigate("/bids/requests")} />
      </div>

      <div className="mb-3 rounded-lg bg-white p-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={filters.q}
            onChange={(e) => set("q", e.target.value)}
            placeholder="Search a bid number, item or bidder. Spaces and small typing mistakes are fine"
            className={`${fieldClass} md:max-w-md`}
            aria-label="Search bids"
          />
          <select value={filters.vendor_id} onChange={(e) => set("vendor_id", e.target.value)} className={`${fieldClass} md:w-56`} aria-label="Vendor">
            <option value="">All vendors</option>
            {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          <select value={filters.bid_type} onChange={(e) => set("bid_type", e.target.value)} className={`${fieldClass} md:w-40`} aria-label="Bid category">
            <option value="">GeM and State govt</option>
            {(meta?.bid_types || ["GeM", "State govt"]).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={filters.category} onChange={(e) => set("category", e.target.value)} className={`${fieldClass} md:w-56`} aria-label="Product category">
            <option value="">All product categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={filters.product_type} onChange={(e) => set("product_type", e.target.value)} disabled={!filters.category} className={`${fieldClass} md:w-48`} aria-label="Product type">
            <option value="">All types</option>
            {typeOptions.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {STATE_CHIPS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => set("state", s)}
              className={`rounded-full border px-3 py-1 text-xs ${filters.state === s ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <Notice tone="bad">{err}</Notice>

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-xs font-semibold text-slate-600">
            <tr>
              <th className="px-3 py-2">Bid number</th>
              <th className="px-3 py-2">Item</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Closes</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Bidder</th>
              <th className="px-3 py-2 text-right">EMD</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && rows.length === 0 && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">Loading…</td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">No bids match.</td></tr>}
            {rows.map((b) => (
              <tr key={b.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  <BidLink bid={b} />
                  {b.pending_requests > 0 && (
                    <span className="ml-1.5 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] text-indigo-700" title="Vendors have asked for this bid">
                      {b.pending_requests} asked
                    </span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <div className="max-w-[280px] truncate" title={b.title}>{b.title}</div>
                  {b.lines?.length > 0 && (
                    <div className="max-w-[280px] truncate text-xs text-slate-600" title={b.lines.map((l) => `${l.item}${l.quantity != null ? ` × ${l.quantity}` : ""}`).join(", ")}>
                      {b.lines.map((l) => `${l.item}${l.quantity != null ? ` × ${l.quantity}` : ""}`).join(" · ")}
                    </div>
                  )}
                  <div className="text-xs text-slate-500">{b.product_category}{b.product_type && b.product_type !== "Other" ? ` / ${b.product_type}` : ""}</div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{b.bid_type}</td>
                <td className="px-3 py-2 whitespace-nowrap">{fmtDate(b.end_date)}<DaysLeft bid={b} /></td>
                <td className="px-3 py-2"><StatusPill bid={b} /></td>
                <td className="px-3 py-2">{b.vendor_name || <span className="text-slate-400">Not allocated</span>}</td>
                <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap">{b.emd_exempt ? "Exempt" : money(b.emd_amount)}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap"><Link to={`/bids/${b.id}`} className={btnGhost}>Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-500">{rows.length} bid{rows.length === 1 ? "" : "s"} shown. Dates and day counts are in India time.</p>
    </div>
  );
}
