import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { accountLedgerApi } from "../../api/accountLedger.js";

function inputClass() {
  return "block w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
}

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

const STATES = ["Rajasthan", "Maharashtra", "Uttar Pradesh", "Gujarat", "Delhi", "Haryana", "Punjab", "Karnataka", "Tamil Nadu", "West Bengal"];

/** One lookup screen, reused for both Sales (vendors only) and Service Team/Manager (engineers only) —
 * which party type it searches is fixed by the `partyType` prop, never a user choice. */
export default function LedgerSearch({ partyType }) {
  const navigate = useNavigate();
  const isVendor = partyType === "vendor";
  const [filters, setFilters] = useState({ state: "", district: "", phone: "", code: "", q: "" });
  const [rows, setRows] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  function patch(field, value) {
    setFilters((cur) => ({ ...cur, [field]: value }));
  }

  async function search() {
    setLoading(true); setErr(""); setSearched(true);
    try {
      const params = { state: filters.state || undefined, district: filters.district || undefined, phone: filters.phone || undefined, q: filters.q || undefined };
      if (isVendor) params.code = filters.code || undefined;
      const data = isVendor ? await accountLedgerApi.listVendors(params) : await accountLedgerApi.listEngineers(params);
      setRows(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Find {isVendor ? "a vendor's" : "an engineer's"} account</h1>
        <p className="text-sm text-slate-500">{isVendor ? "Vendors" : "Engineers"} only — {isVendor ? "engineers" : "vendors"} never show up here.</p>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">State</label>
            <select value={filters.state} onChange={(e) => patch("state", e.target.value)} className={`${inputClass()} mt-1`}>
              <option value="">All states</option>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">District</label>
            <input value={filters.district} onChange={(e) => patch("district", e.target.value)} placeholder="District" className={`${inputClass()} mt-1`} />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Phone number</label>
            <input value={filters.phone} onChange={(e) => patch("phone", e.target.value)} placeholder="Phone number" className={`${inputClass()} mt-1`} />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">{isVendor ? "Vendor code" : "Name"}</label>
            <input
              value={isVendor ? filters.code : filters.q}
              onChange={(e) => patch(isVendor ? "code" : "q", e.target.value)}
              placeholder={isVendor ? "e.g. DT-0117" : "Technician name"}
              className={`${inputClass()} mt-1`}
            />
          </div>
        </div>
        {isVendor && (
          <div className="mt-3">
            <label className="text-xs uppercase tracking-wide text-slate-500">Or company name</label>
            <input value={filters.q} onChange={(e) => patch("q", e.target.value)} placeholder="Company name" className={`${inputClass()} mt-1`} />
          </div>
        )}
        <div className="mt-3 flex justify-end">
          <button type="button" onClick={search} disabled={loading} className="rounded-md bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        {err && <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      </div>

      {searched && (
        <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">{isVendor ? "Vendor" : "Engineer"}</th>
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Phone</th>
                {!isVendor && <th className="px-3 py-2">Type</th>}
                <th className="px-3 py-2 text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 ? (
                <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No results.</td></tr>
              ) : rows.map((r) => (
                <tr key={r.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/ledger/${partyType}/${r.id}`)}>
                  <td className="px-3 py-2">
                    <div className="font-medium text-slate-800">{r.name}</div>
                    {r.overdue_days > 0 && <div className="text-xs font-semibold text-rose-700">⚠ Overdue {r.overdue_days}d</div>}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">{r.code}</td>
                  <td className="px-3 py-2 text-xs text-slate-500">{r.phone || "—"}</td>
                  {!isVendor && <td className="px-3 py-2 text-xs text-slate-500">{r.role}</td>}
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
