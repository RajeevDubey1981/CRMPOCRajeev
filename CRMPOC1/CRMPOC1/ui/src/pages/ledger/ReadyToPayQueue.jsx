import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

const URGENCY = {
  urgent: { label: "7+ days", cls: "bg-rose-100 text-rose-700", icon: "⚠ " },
  soon: { label: "3–6 days", cls: "bg-amber-100 text-amber-700", icon: "" },
  ontime: { label: "On time", cls: "bg-emerald-100 text-emerald-700", icon: "" },
};

const BUCKET_LABEL = { all: "Ready to pay", urgent: "Urgent (7+ days)", soon: "Due soon (3–6 days)", ontime: "On time" };

/** Everything that's cleared Audit and is sitting at the Admin stage, across both Installations
 * and Service Requests -- a finding/prioritizing view. Actually paying still happens on that
 * record's own detail page ("Pay now" just opens it). */
export default function ReadyToPayQueue() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [engineerFilter, setEngineerFilter] = useState("");
  const [vendorFilter, setVendorFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [sortBy, setSortBy] = useState("oldest");
  const [bucket, setBucket] = useState("all");

  useEffect(() => {
    setLoading(true);
    api.get("/api/dashboard/ready-to-pay", {
      params: {
        search: search || undefined,
        engineer: engineerFilter || undefined,
        vendor: vendorFilter || undefined,
        module: moduleFilter || undefined,
      },
    })
      .then((r) => setItems(r.data))
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, [search, engineerFilter, vendorFilter, moduleFilter]);

  const counts = useMemo(() => ({
    all: items.length,
    urgent: items.filter((i) => i.urgency === "urgent").length,
    soon: items.filter((i) => i.urgency === "soon").length,
    ontime: items.filter((i) => i.urgency === "ontime").length,
  }), [items]);

  const visible = useMemo(() => {
    let rows = bucket === "all" ? items : items.filter((i) => i.urgency === bucket);
    rows = [...rows];
    if (sortBy === "oldest") rows.sort((a, b) => b.days_waiting - a.days_waiting);
    else if (sortBy === "newest") rows.sort((a, b) => a.days_waiting - b.days_waiting);
    else if (sortBy === "amount") rows.sort((a, b) => b.amount - a.amount);
    return rows;
  }, [items, bucket, sortBy]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Ready to pay</h1>
        <p className="text-sm text-slate-500">
          Everything here has already cleared Audit. "Waiting" flags how long it's been since the request was first raised, oldest first.
        </p>
      </div>

      {err && <div className="rounded bg-rose-50 p-3 text-sm text-rose-700">{err}</div>}

      <div className="flex flex-wrap gap-3">
        {["all", "urgent", "soon", "ontime"].map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setBucket(key)}
            className={`min-w-[150px] flex-1 rounded-lg bg-white p-3 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${
              bucket === key ? "ring-2" : ""
            } ${key === "urgent" ? "border-l-4 border-rose-600" : key === "soon" ? "border-l-4 border-amber-500" : key === "ontime" ? "border-l-4 border-emerald-600" : "border-l-4 border-slate-700"}`}
            style={bucket === key ? { "--tw-ring-color": key === "urgent" ? "#be123c" : key === "soon" ? "#b45309" : key === "ontime" ? "#047857" : "#334155" } : undefined}
          >
            <div className={`text-xl font-extrabold ${key === "urgent" ? "text-rose-700" : key === "soon" ? "text-amber-700" : key === "ontime" ? "text-emerald-700" : "text-slate-800"}`}>
              {counts[key]}
            </div>
            <div className="text-xs uppercase tracking-wide text-slate-500">{BUCKET_LABEL[key]}</div>
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Search (ID or name)</label>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="#4821" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Engineer</label>
            <input value={engineerFilter} onChange={(e) => setEngineerFilter(e.target.value)} placeholder="Name" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Vendor</label>
            <input value={vendorFilter} onChange={(e) => setVendorFilter(e.target.value)} placeholder="Name" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Module</label>
            <select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">All</option>
              <option value="installation">Installation</option>
              <option value="service">Service</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Sort by</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="oldest">Oldest first (most urgent)</option>
              <option value="newest">Newest first</option>
              <option value="amount">Amount, highest first</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-3 py-2">Module</th>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Paying</th>
              <th className="px-3 py-2">Requested</th>
              <th className="px-3 py-2">Waiting</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Nothing here right now.</td></tr>
            )}
            {!loading && visible.map((item) => {
              const u = URGENCY[item.urgency] || URGENCY.ontime;
              return (
                <tr key={`${item.module}-${item.entity_id}`} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase text-white ${item.module === "installation" ? "bg-sky-600" : "bg-violet-600"}`}>
                      {item.module === "installation" ? "Installation" : "Service"}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono">{item.label}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-slate-800">{item.payee_name || "—"}</div>
                    {item.payee_type && <div className="text-xs text-slate-500">{item.payee_type}</div>}
                  </td>
                  <td className="px-3 py-2">{fmtDate(item.requested_at)}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${u.cls}`}>
                      {u.icon}{item.days_waiting === 0 ? "Today" : `${item.days_waiting} day${item.days_waiting === 1 ? "" : "s"}`}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(item.amount)}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => navigate(item.href)}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
                    >
                      Pay now
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">
        "Pay now" opens that record's own detail page — the real Approve &amp; Release Payment form, same as today. This screen is for finding and prioritizing, not a separate place to actually pay from.
      </p>
    </div>
  );
}
