import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { accountLedgerApi } from "../../api/accountLedger.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

function monthLabel(ym) {
  try {
    const [y, m] = ym.split("-");
    return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-IN", { month: "short" });
  } catch { return ym; }
}

function fmtDateTime(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "numeric", minute: "2-digit" }); } catch { return d; }
}

function isThisMonth(d) {
  if (!d) return false;
  const dt = new Date(d);
  const now = new Date();
  return dt.getFullYear() === now.getFullYear() && dt.getMonth() === now.getMonth();
}

function median(nums) {
  if (nums.length === 0) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

const STATUS_PILL = {
  Pending: "bg-amber-100 text-amber-800 border border-amber-300",
  Approved: "bg-emerald-100 text-emerald-700 border border-emerald-300",
  Rejected: "bg-rose-100 text-rose-700 border border-rose-300",
};

/** Every vendor-expense request across every vendor -- Pending, Approved and Rejected -- for Accounts
 * to audit. Nothing here posts to a ledger; approving already does that automatically elsewhere. */
function VendorApprovalHistoryPanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [vendorFilter, setVendorFilter] = useState("");
  const [raisedByFilter, setRaisedByFilter] = useState("");

  useEffect(() => {
    accountLedgerApi.listVendorExpenses({})
      .then(setRows)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load approval history"))
      .finally(() => setLoading(false));
  }, []);

  const vendorOptions = [...new Map(rows.map((r) => [r.vendor_id, r.vendor_name])).entries()];

  const pendingCount = rows.filter((r) => r.status === "Pending").length;
  const approvedThisMonth = rows.filter((r) => r.status === "Approved" && isThisMonth(r.decided_at));
  const approvedThisMonthSum = approvedThisMonth.reduce((sum, r) => sum + r.amount, 0);
  const rejectedThisMonthCount = rows.filter((r) => r.status === "Rejected" && isThisMonth(r.decided_at)).length;
  const responseHours = rows
    .filter((r) => r.decided_at)
    .map((r) => (new Date(r.decided_at) - new Date(r.created_at)) / 36e5);
  const medianHours = median(responseHours);

  const filtered = rows.filter((r) =>
    (!statusFilter || r.status === statusFilter) &&
    (!vendorFilter || String(r.vendor_id) === vendorFilter) &&
    (!raisedByFilter || r.raised_by_type === raisedByFilter)
  );

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Vendor Approval History — every request, every vendor</p>
      <p className="mt-0.5 text-xs text-slate-500">What Sales/Service raised, and what each vendor decided. Approving debits the vendor automatically; nothing here does.</p>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-amber-700">Pending</div>
          <div className="text-xl font-bold text-amber-700">{pendingCount}</div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-emerald-700">Approved this month</div>
          <div className="text-xl font-bold text-emerald-700">{fmtMoney(approvedThisMonthSum)}</div>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="text-[10px] uppercase tracking-wide text-rose-700">Rejected this month</div>
          <div className="text-xl font-bold text-rose-700">{rejectedThisMonthCount}</div>
        </div>
        <div className="rounded-lg border border-slate-200 p-3">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">Median response time</div>
          <div className="text-xl font-bold">{medianHours == null ? "—" : medianHours < 48 ? `${medianHours.toFixed(1)} hrs` : `${(medianHours / 24).toFixed(1)} days`}</div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-xs">
          <option value="">All statuses</option>
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
        </select>
        <select value={vendorFilter} onChange={(e) => setVendorFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-xs">
          <option value="">All vendors</option>
          {vendorOptions.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
        <select value={raisedByFilter} onChange={(e) => setRaisedByFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-xs">
          <option value="">Raised by: anyone</option>
          <option value="sales">Sales</option>
          <option value="service_team">Service Team</option>
        </select>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Order</th>
              <th className="px-3 py-2">Vendor</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2">Raised by</th>
              <th className="px-3 py-2">Raised on</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Decided</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">No requests match this filter.</td></tr>
            ) : filtered.map((r) => (
              <tr key={r.id} title={r.decision_note || ""}>
                <td className="px-3 py-2 font-mono text-xs">{r.order_no || `#${r.order_id}`}</td>
                <td className="px-3 py-2">{r.vendor_name || "—"}</td>
                <td className="px-3 py-2">{r.reason}</td>
                <td className="px-3 py-2 text-xs">{r.raised_by_name || "—"} <span className="text-slate-400">({r.raised_by_type === "service_team" ? "Service" : "Sales"})</span></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDateTime(r.created_at)}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.amount)}</td>
                <td className="px-3 py-2"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_PILL[r.status]}`}>{r.status}</span></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDateTime(r.decided_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReturnsPanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(null); // order_id being processed
  const [form, setForm] = useState({ return_amount: "", return_charges_amount: "", note: "" });
  const [busy, setBusy] = useState(false);

  function load() {
    setLoading(true);
    accountLedgerApi.listPendingReturns()
      .then(setRows)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load returns"))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  function startProcess(row) {
    setOpen(row.order_id);
    setForm({ return_amount: row.suggested_return_amount ?? "", return_charges_amount: "", note: "" });
  }

  async function submit(orderId) {
    setBusy(true);
    try {
      await accountLedgerApi.processReturn(orderId, {
        return_amount: Number(form.return_amount || 0),
        return_charges_amount: Number(form.return_charges_amount || 0),
        note: form.note,
      });
      setOpen(null);
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to process return");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
      <div className="px-4 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Returns &amp; Cancellations — awaiting Accounts</p>
        <p className="mt-0.5 text-xs text-slate-500">Nothing here has touched a vendor's ledger yet. Sales/Service must confirm material receipt first.</p>
      </div>
      {err && <p className="px-4 pt-2 text-xs text-rose-700">{err}</p>}
      <table className="mt-2 min-w-full text-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr>
            <th className="px-3 py-2">Order</th>
            <th className="px-3 py-2">Vendor</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Material receipt</th>
            <th className="px-3 py-2 text-right">OEM bill</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {loading ? (
            <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
          ) : rows.length === 0 ? (
            <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">No returned or cancelled orders waiting.</td></tr>
          ) : rows.map((row) => (
            <>
              <tr key={row.order_id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium">{row.order_no || `#${row.order_id}`}</td>
                <td className="px-3 py-2">{row.vendor_name || "—"}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${row.status === "Cancelled" ? "bg-slate-200 text-slate-700" : "bg-amber-100 text-amber-800"}`}>{row.status}</span>
                </td>
                <td className="px-3 py-2 text-xs">
                  {row.material_receipt_confirmed_at ? (
                    <span className="text-emerald-700">Confirmed by {row.material_receipt_confirmed_by}</span>
                  ) : (
                    <span className="text-slate-400">Waiting on Sales/Service</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(row.oem_bill_amount)}</td>
                <td className="px-3 py-2 text-right">
                  {row.material_receipt_confirmed_at ? (
                    <button type="button" onClick={() => startProcess(row)} className="rounded-md bg-brand-600 px-3 py-1 text-xs font-semibold text-white hover:bg-brand-700">
                      Process return
                    </button>
                  ) : null}
                </td>
              </tr>
              {open === row.order_id && (
                <tr key={`${row.order_id}-form`}>
                  <td colSpan={6} className="bg-slate-50 px-4 py-3">
                    <div className="grid gap-3 sm:grid-cols-3">
                      <label className="text-xs text-slate-600">
                        Return amount
                        <input type="number" className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={form.return_amount}
                          onChange={(e) => setForm((f) => ({ ...f, return_amount: e.target.value }))} />
                      </label>
                      <label className="text-xs text-slate-600">
                        Return / courier charges
                        <input type="number" className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={form.return_charges_amount}
                          onChange={(e) => setForm((f) => ({ ...f, return_charges_amount: e.target.value }))} />
                      </label>
                      <label className="text-xs text-slate-600">
                        Note
                        <input type="text" className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={form.note}
                          onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))} />
                      </label>
                    </div>
                    <p className="mt-2 text-[11px] text-slate-500">These post as two separate debits on the vendor's ledger — they are never combined into one figure.</p>
                    <div className="mt-2 flex gap-2">
                      <button type="button" disabled={busy} onClick={() => submit(row.order_id)} className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
                        {busy ? "Saving…" : "Debit vendor"}
                      </button>
                      <button type="button" onClick={() => setOpen(null)} className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-600 hover:bg-slate-100">Cancel</button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatementUploadPanel() {
  const [upload, setUpload] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function onFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const result = await accountLedgerApi.uploadStatement(file);
      setUpload(result);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Failed to parse this file");
    } finally {
      setBusy(false);
    }
  }

  async function confirmLine(line) {
    if (!line.matched_party_type) return;
    setBusy(true);
    try {
      await accountLedgerApi.confirmStatementLine(upload.id, line.id, {
        party_type: line.matched_party_type, party_id: line.matched_party_id,
      });
      const refreshed = await accountLedgerApi.getStatement(upload.id);
      setUpload(refreshed);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Failed to post this line");
    } finally {
      setBusy(false);
    }
  }

  async function ignoreLine(line) {
    setBusy(true);
    try {
      await accountLedgerApi.ignoreStatementLine(upload.id, line.id);
      const refreshed = await accountLedgerApi.getStatement(upload.id);
      setUpload(refreshed);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Failed to ignore this line");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Upload bank statement (CSV)</p>
          <p className="mt-0.5 text-xs text-slate-500">Each row is matched to a vendor or engineer by phone, code, or name. Nothing posts until you confirm it below.</p>
        </div>
        <label className="cursor-pointer rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700">
          {busy ? "Working…" : "Choose CSV"}
          <input type="file" accept=".csv" className="hidden" disabled={busy} onChange={onFile} />
        </label>
      </div>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}
      {upload && (
        <table className="mt-3 min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Match</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {upload.lines.map((line) => (
              <tr key={line.id}>
                <td className="px-3 py-2 text-xs">{fmtDate(line.line_date)}</td>
                <td className="px-3 py-2 text-xs">{line.description}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(line.amount)}</td>
                <td className="px-3 py-2 text-xs">
                  {line.matched_party_type ? (
                    <span>
                      {line.matched_party_type === "vendor" ? "Vendor" : "Engineer"} #{line.matched_party_id}
                      <span className="ml-1 text-slate-400">({Math.round((line.match_confidence || 0) * 100)}% — {line.match_reason})</span>
                    </span>
                  ) : (
                    <span className="text-slate-400">No match found</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs">{line.status === "pending_audit" ? "Pending audit" : line.status.charAt(0).toUpperCase() + line.status.slice(1)}</td>
                <td className="px-3 py-2 text-right">
                  {line.status === "unmatched" || line.status === "matched" ? (
                    <div className="flex justify-end gap-1">
                      {line.matched_party_type && (
                        <button type="button" disabled={busy} onClick={() => confirmLine(line)} className="rounded-md bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">Confirm</button>
                      )}
                      <button type="button" disabled={busy} onClick={() => ignoreLine(line)} className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-50">Ignore</button>
                    </div>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function AccountsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    accountLedgerApi.dashboard()
      .then(setData)
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4 text-sm text-slate-500">Loading…</div>;
  if (err) return <div className="p-4 text-sm text-rose-700">{err}</div>;
  if (!data) return null;

  const maxBar = Math.max(1, ...data.month_wise.flatMap((m) => [m.due, m.paid]));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Accounts Dashboard</h1>
        <p className="text-sm text-slate-500">What's owed, what's been paid, and who's overdue — across every vendor and engineer.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Total due (all parties)</div>
          <div className="mt-1 text-xl font-bold text-rose-700">{fmtMoney(data.total_due)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Paid this month</div>
          <div className="mt-1 text-xl font-bold text-emerald-700">{fmtMoney(data.paid_this_month)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Overdue amount</div>
          <div className="mt-1 text-xl font-bold text-rose-700">{fmtMoney(data.overdue_amount)}</div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Overdue parties</div>
          <div className="mt-1 text-xl font-bold">{data.overdue_count}</div>
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Due vs Paid — month wise</p>
        <div className="mt-3 flex items-end gap-4" style={{ height: 140 }}>
          {data.month_wise.map((m) => (
            <div key={m.month} className="flex flex-1 flex-col items-center justify-end gap-1" style={{ height: "100%" }}>
              <div className="flex items-end gap-1" style={{ height: 100 }}>
                <div className="w-3 rounded-t bg-rose-500/80" style={{ height: `${Math.max(2, (m.due / maxBar) * 100)}px` }} title={`Due: ${fmtMoney(m.due)}`} />
                <div className="w-3 rounded-t bg-emerald-600/80" style={{ height: `${Math.max(2, (m.paid / maxBar) * 100)}px` }} title={`Paid: ${fmtMoney(m.paid)}`} />
              </div>
              <div className="text-[10px] text-slate-500">{monthLabel(m.month)}</div>
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-4 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-rose-500" /> Due</span>
          <span className="inline-flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-sm bg-emerald-600" /> Paid</span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <div className="px-4 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Overdue — sorted worst first</p>
        </div>
        <table className="mt-2 min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Party</th>
              <th className="px-3 py-2">Cycle</th>
              <th className="px-3 py-2">Oldest unpaid since</th>
              <th className="px-3 py-2">Overdue by</th>
              <th className="px-3 py-2 text-right">Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.overdue.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">Nothing overdue.</td></tr>
            ) : data.overdue.map((r) => (
              <tr key={`${r.party_type}-${r.party_id}`} className="cursor-pointer hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/ledger/${r.party_type}/${r.party_id}`} className="font-medium text-brand-700 hover:underline">{r.name}</Link>
                  <span className="ml-1 text-xs text-slate-500">({r.party_type})</span>
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{r.cycle_days} days</td>
                <td className="px-3 py-2 text-xs">{fmtDate(r.oldest_unpaid_since)}</td>
                <td className="px-3 py-2">
                  <span className="inline-flex rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-700">{r.overdue_days}d</span>
                </td>
                <td className="px-3 py-2 text-right font-mono">{fmtMoney(r.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ReturnsPanel />
      <StatementUploadPanel />
      <VendorApprovalHistoryPanel />
    </div>
  );
}
