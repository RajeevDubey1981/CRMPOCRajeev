import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

import { accountLedgerApi } from "../../api/accountLedger.js";
import { ordersApi } from "../../api/orders.js";
import { useAuth } from "../../auth/AuthContext.jsx";

function inputClass() {
  return "mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500";
}

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

// "Credit" = owed to the party (an OEM bill, a payout). "Debit" = already paid to them. Plain English
// in the UI on purpose -- Sales/Service aren't accountants, so the page says "Owed"/"Paid", not Dr/Cr.
const ENTRY_LABEL = { credit: "Owed", debit: "Paid" };
const ENTRY_STYLE = { credit: "bg-rose-100 text-rose-700", debit: "bg-emerald-100 text-emerald-700" };

function canCoordinateWithVendor(user) {
  const role = (user?.role || "").toLowerCase();
  if (role === "vendor" || role === "engineer") return false;
  return (Array.isArray(user?.permissions) ? user.permissions : []).some((p) => p.module === "orders" && p.can_view);
}

/** Sales/Service raise an extra delivery/installation expense for this vendor to approve on their own
 * portal -- the same action as the one on an Order's own page, but reachable straight from the vendor's
 * ledger so you don't have to already know which order to open first. */
function VendorExpenseRaisePanel({ vendorId }) {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [orderId, setOrderId] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    ordersApi.list({ vendor_id: vendorId, per_page: 100 }).then((r) => setOrders(r.items || [])).catch(() => {});
    accountLedgerApi.listVendorExpenses({ vendor_id: vendorId }).then(setExpenses).catch(() => {});
  }, [vendorId]);

  if (!canCoordinateWithVendor(user)) return null;

  async function raise() {
    if (!orderId || !amount || !reason.trim()) { setErr("Pick an order, an amount, and a reason"); return; }
    setBusy(true); setErr("");
    try {
      const created = await accountLedgerApi.raiseVendorExpense({ order_id: Number(orderId), amount: Number(amount), reason: reason.trim() });
      setExpenses((prev) => [created, ...prev]);
      setOrderId(""); setAmount(""); setReason("");
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to raise this");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Raise an extra delivery/installation expense for this vendor</p>
      <p className="mt-0.5 text-xs text-slate-500">Nothing debits the vendor until they approve this themselves, on their own portal.</p>
      {err && <p className="mt-2 text-xs text-rose-700">{err}</p>}
      <div className="mt-2 grid gap-2 sm:grid-cols-4">
        <select value={orderId} onChange={(e) => setOrderId(e.target.value)} className={`${inputClass()} sm:col-span-1`}>
          <option value="">Order…</option>
          {orders.map((o) => <option key={o.id} value={o.id}>{o.order_no || `#${o.id}`} ({o.status})</option>)}
        </select>
        <input type="number" placeholder="Amount (₹)" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClass()} />
        <input placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} className={`${inputClass()} sm:col-span-2`} />
      </div>
      <div className="mt-2 flex justify-end">
        <button type="button" disabled={busy} onClick={raise} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
          {busy ? "Sending…" : "Send to vendor for approval"}
        </button>
      </div>
      {expenses.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-200 pt-2 text-xs">
          {expenses.map((exp) => (
            <li key={exp.id} className="flex items-center justify-between">
              <span>{exp.order_no || `#${exp.order_id}`} — {exp.reason} — {fmtMoney(exp.amount)}</span>
              <span className={
                exp.status === "Approved" ? "font-semibold text-emerald-700"
                : exp.status === "Rejected" ? "font-semibold text-rose-700"
                : "font-semibold text-amber-700"
              }>{exp.status}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function LedgerDetail() {
  const { partyType, id } = useParams();
  const partyId = Number(id);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const [openingAmount, setOpeningAmount] = useState("");
  const [openingType, setOpeningType] = useState("credit");
  const [cycleDays, setCycleDays] = useState("");
  const [entryType, setEntryType] = useState("debit");
  const [entryAmount, setEntryAmount] = useState("");
  const [entryDesc, setEntryDesc] = useState("");

  function load() {
    setLoading(true);
    setErr("");
    accountLedgerApi.get(partyType, partyId)
      .then((d) => {
        setData(d);
        setOpeningAmount(d.opening_balance != null ? String(d.opening_balance) : "");
        setOpeningType(d.opening_balance_type || "credit");
        setCycleDays(d.payment_cycle_days != null ? String(d.payment_cycle_days) : "");
      })
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [partyType, partyId]);

  async function saveOpening() {
    if (openingAmount === "" || Number(openingAmount) < 0) { setErr("Enter an opening balance amount"); return; }
    setBusy(true); setErr("");
    try {
      await accountLedgerApi.setOpeningBalance(partyType, partyId, { amount: Number(openingAmount), entry_type: openingType });
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not save opening balance");
    } finally { setBusy(false); }
  }

  async function saveCycle() {
    setBusy(true); setErr("");
    try {
      await accountLedgerApi.setCycle(partyType, partyId, { payment_cycle_days: cycleDays === "" ? null : Number(cycleDays) });
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not save payment cycle");
    } finally { setBusy(false); }
  }

  async function addEntry() {
    if (!entryAmount || Number(entryAmount) <= 0) { setErr("Enter an amount"); return; }
    if (!entryDesc.trim()) { setErr("Describe this entry"); return; }
    setBusy(true); setErr("");
    try {
      await accountLedgerApi.addEntry(partyType, partyId, { entry_type: entryType, amount: Number(entryAmount), description: entryDesc.trim() });
      setEntryAmount(""); setEntryDesc("");
      load();
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not add entry");
    } finally { setBusy(false); }
  }

  if (loading) return <div className="p-4 text-sm text-slate-500">Loading…</div>;
  if (!data) return <div className="p-4 text-sm text-rose-700">{err || "Not found"}</div>;

  const canEdit = data.can_edit;
  const overdue = data.overdue_days > 0 && data.balance > 0;

  return (
    <div className="space-y-4">
      <Link to={partyType === "vendor" ? "/ledger/vendors" : "/ledger/engineers"} className="text-sm text-brand-700 hover:underline">
        ← Back to {partyType === "vendor" ? "vendor" : "engineer"} search
      </Link>

      <div className="rounded-lg bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-lg font-semibold text-slate-800">
              {data.name}
              {overdue && (
                <span className="ml-2 inline-flex items-center rounded-full border border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-700">
                  ⚠ Overdue {data.overdue_days} day{data.overdue_days === 1 ? "" : "s"}
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-500">{partyType === "vendor" ? "Vendor" : "Engineer"} account</p>
          </div>
        </div>

        {err && <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-[10px] uppercase tracking-wide text-slate-500">Opening balance</div>
            <div className="text-lg font-bold">{data.opening_balance != null ? fmtMoney(data.opening_balance) : "—"}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-[10px] uppercase tracking-wide text-slate-500">Total owed</div>
            <div className="text-lg font-bold text-rose-700">{fmtMoney(data.total_credit)}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-[10px] uppercase tracking-wide text-slate-500">Total paid</div>
            <div className="text-lg font-bold text-emerald-700">{fmtMoney(data.total_debit)}</div>
          </div>
          <div className="rounded-md border border-brand-300 bg-brand-50 p-3">
            <div className="text-[10px] uppercase tracking-wide text-slate-500">Balance — we owe</div>
            <div className="text-lg font-bold">{fmtMoney(data.balance)}</div>
          </div>
        </div>

        {canEdit && (
          <>
            <div className="mt-5 flex flex-wrap items-end gap-2">
              <div className="flex-1 min-w-[160px]">
                <label className="text-xs uppercase tracking-wide text-slate-500">Opening balance — set once</label>
                <input type="number" min="0" value={openingAmount} onChange={(e) => setOpeningAmount(e.target.value)} className={inputClass()} />
              </div>
              <div className="w-40">
                <label className="text-xs uppercase tracking-wide text-slate-500">Type</label>
                <select value={openingType} onChange={(e) => setOpeningType(e.target.value)} className={inputClass()}>
                  <option value="credit">Owed (we owe them)</option>
                  <option value="debit">Paid (they owe us)</option>
                </select>
              </div>
              <button type="button" disabled={busy} onClick={saveOpening} className="mb-0.5 rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50">Save</button>
            </div>

            <div className="mt-4 flex flex-wrap items-end gap-2">
              <div className="flex-1 min-w-[160px]">
                <label className="text-xs uppercase tracking-wide text-slate-500">Payment cycle — pay within this many days</label>
                <input type="number" min="1" placeholder="e.g. 15" value={cycleDays} onChange={(e) => setCycleDays(e.target.value)} className={inputClass()} />
              </div>
              <button type="button" disabled={busy} onClick={saveCycle} className="mb-0.5 rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50">Save</button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {data.oldest_unpaid_since
                ? `Oldest unpaid amount is from ${fmtDate(data.oldest_unpaid_since)}${data.payment_cycle_days ? ` — against a ${data.payment_cycle_days}-day cycle` : ""}.`
                : "Nothing currently outstanding."}
            </p>

            <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Add an entry</p>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                <select value={entryType} onChange={(e) => setEntryType(e.target.value)} className={inputClass()}>
                  <option value="debit">Paid (reduces balance)</option>
                  <option value="credit">Owed (increases balance)</option>
                </select>
                <input type="number" min="0" placeholder="Amount (₹)" value={entryAmount} onChange={(e) => setEntryAmount(e.target.value)} className={inputClass()} />
                <input placeholder="Description" value={entryDesc} onChange={(e) => setEntryDesc(e.target.value)} className={`${inputClass()} sm:col-span-2`} />
              </div>
              <div className="mt-2 flex justify-end">
                <button type="button" disabled={busy} onClick={addEntry} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
                  {busy ? "Saving…" : "Add entry"}
                </button>
              </div>
            </div>
          </>
        )}

        {partyType === "vendor" && <VendorExpenseRaisePanel vendorId={partyId} />}

        <p className="mt-6 text-xs font-semibold uppercase tracking-wide text-slate-500">Ledger</p>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.entries.length === 0 ? (
                <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No entries yet.</td></tr>
              ) : [...data.entries].reverse().map((e) => (
                <tr key={e.id}>
                  <td className="px-3 py-2 text-xs">{fmtDate(e.entry_date)}</td>
                  <td className="px-3 py-2">{e.description}</td>
                  <td className="px-3 py-2 text-xs text-slate-500">{e.source_type.replace(/_/g, " ")}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ENTRY_STYLE[e.entry_type]}`}>{ENTRY_LABEL[e.entry_type]}</span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(e.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
