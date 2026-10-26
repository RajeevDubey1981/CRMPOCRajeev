import { useEffect, useState } from "react";

import { accountLedgerApi } from "../../api/accountLedger.js";
import { useAuth } from "../../auth/AuthContext.jsx";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function canEditOrders(user) {
  return (Array.isArray(user?.permissions) ? user.permissions : []).some((p) => p.module === "orders" && p.can_edit);
}

/** Sales/Service actions tied to an order's vendor: confirming a return's material receipt, and raising
 * an extra delivery/installation expense for the vendor to approve on their own portal. */
export default function OrderVendorActions({ order, onOrderChanged }) {
  const { user } = useAuth();
  const [expenses, setExpenses] = useState([]);
  const [showRaise, setShowRaise] = useState(false);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [confirming, setConfirming] = useState(false);

  const canAct = canEditOrders(user);

  useEffect(() => {
    if (!order?.vendor_id) return;
    accountLedgerApi.listVendorExpenses({ order_id: order.id }).then(setExpenses).catch(() => {});
  }, [order?.id, order?.vendor_id]);

  if (!order?.vendor_id || !canAct) return null;

  const isReturnOrCancel = order.status === "Returned" || order.status === "Cancelled";

  async function confirmReceipt() {
    setConfirming(true);
    setErr("");
    try {
      await accountLedgerApi.confirmMaterialReceipt(order.id);
      onOrderChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to confirm");
    } finally {
      setConfirming(false);
    }
  }

  async function raiseExpense() {
    setBusy(true);
    setErr("");
    try {
      const created = await accountLedgerApi.raiseVendorExpense({ order_id: order.id, amount: Number(amount), reason });
      setExpenses((prev) => [created, ...prev]);
      setShowRaise(false);
      setAmount("");
      setReason("");
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to raise this");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
      {isReturnOrCancel && (
        <div>
          {order.material_receipt_confirmed_at ? (
            <p className="text-xs text-emerald-700">Material receipt confirmed by {order.material_receipt_confirmed_by || "you"}.</p>
          ) : (
            <button type="button" onClick={confirmReceipt} disabled={confirming}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50">
              {confirming ? "Confirming…" : "Confirm material receipt (returned goods back in hand)"}
            </button>
          )}
          <p className="mt-1 text-[11px] text-slate-500">Accounts cannot debit the vendor for this return until this is confirmed.</p>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Extra delivery/installation expense</p>
          <button type="button" onClick={() => setShowRaise((v) => !v)} className="text-xs font-semibold text-brand-700 hover:underline">
            {showRaise ? "Cancel" : "+ Raise for vendor approval"}
          </button>
        </div>
        {err && <p className="mt-1 text-xs text-rose-700">{err}</p>}
        {showRaise && (
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            <input type="number" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm" />
            <input type="text" placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm sm:col-span-2" />
            <button type="button" disabled={busy || !amount || !reason} onClick={raiseExpense}
              className="rounded-md bg-brand-600 px-3 py-1 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50 sm:col-span-3">
              {busy ? "Sending…" : "Send to vendor for approval"}
            </button>
            <p className="text-[11px] text-slate-500 sm:col-span-3">Nothing debits the vendor until they approve this on their own portal.</p>
          </div>
        )}
        {expenses.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs">
            {expenses.map((exp) => (
              <li key={exp.id} className="flex items-center justify-between">
                <span>{exp.reason} — {fmtMoney(exp.amount)}</span>
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
    </div>
  );
}
