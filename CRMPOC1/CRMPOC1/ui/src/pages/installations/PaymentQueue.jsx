import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client.js";
import { installationsApi } from "../../api/installations.js";
import { servicesApi } from "../../api/services.js";
import { formatApiError } from "../../utils/apiError.js";

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

const URGENCY = {
  urgent: { label: "7+ days", cls: "bg-rose-100 text-rose-700", icon: "⚠ " },
  soon: { label: "3–6 days", cls: "bg-amber-100 text-amber-700", icon: "" },
  ontime: { label: "On time", cls: "bg-emerald-100 text-emerald-700", icon: "" },
};

function ReturnBox({ onCancel, onConfirm, busy }) {
  const [remarks, setRemarks] = useState("");
  return (
    <div className="mt-2 flex items-center gap-2 rounded-md border border-rose-200 bg-rose-50 p-2">
      <input
        value={remarks}
        onChange={(e) => setRemarks(e.target.value)}
        placeholder="Why it's being returned (required)"
        className="flex-1 rounded-md border border-rose-300 px-2 py-1 text-xs"
      />
      <button
        type="button"
        disabled={busy || !remarks.trim()}
        onClick={() => onConfirm(remarks.trim())}
        className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
      >
        Confirm return
      </button>
      <button type="button" onClick={onCancel} className="text-xs text-slate-500 underline">
        Cancel
      </button>
    </div>
  );
}

async function sendForward(item, { amount, paymentType }) {
  if (item.module === "installation") {
    const fd = new FormData();
    fd.append("new_status", "Completed");
    fd.append("payment_amount", amount);
    fd.append("payment_type", paymentType);
    return installationsApi.updateStatus(item.entity_id, fd);
  }
  return servicesApi.approvePayment(item.entity_id, {
    approved_amount: amount,
    payment_type: paymentType,
    decision: "Approved",
  });
}

async function sendReturn(item, remarks) {
  if (item.module === "installation") {
    const fd = new FormData();
    fd.append("new_status", "Returned");
    fd.append("work_report", remarks);
    return installationsApi.updateStatus(item.entity_id, fd);
  }
  return servicesApi.approvePayment(item.entity_id, { approved_amount: item.amount, decision: "Rejected", remarks });
}

function QueueRow({ item, onActed }) {
  const navigate = useNavigate();
  const [amount, setAmount] = useState(String(item.amount ?? ""));
  const [paymentType, setPaymentType] = useState(item.payment_type || "Cash");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [showReturn, setShowReturn] = useState(false);
  const u = URGENCY[item.urgency] || URGENCY.ontime;

  async function send() {
    setBusy(true);
    setErr("");
    try {
      await sendForward(item, { amount, paymentType });
      window.dispatchEvent(new Event("payment-queue-changed"));
      onActed();
    } catch (e) {
      setErr(formatApiError(e, "Failed to forward this payment"));
    } finally {
      setBusy(false);
    }
  }

  async function returnIt(remarks) {
    setBusy(true);
    setErr("");
    try {
      await sendReturn(item, remarks);
      window.dispatchEvent(new Event("payment-queue-changed"));
      onActed();
    } catch (e) {
      setErr(formatApiError(e, "Failed to return this payment"));
      setShowReturn(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr className="border-b border-slate-100 align-top hover:bg-slate-50">
      <td className="px-3 py-2">
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase text-white ${item.module === "installation" ? "bg-sky-600" : "bg-violet-600"}`}>
          {item.module === "installation" ? "Install." : "Service"}
        </span>
      </td>
      <td className="px-3 py-2">
        <button type="button" onClick={() => navigate(item.href)} className="font-mono text-brand-700 underline decoration-dotted">
          {item.label}
        </button>
      </td>
      <td className="px-3 py-2">
        <div className="font-medium text-slate-800">{item.customer_name || "—"}</div>
        <div className="text-xs text-slate-500">{item.engineer_name ? `Engineer: ${item.engineer_name}` : ""}</div>
        {item.last_action && (
          <div className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
            ↩ {item.last_action}
          </div>
        )}
      </td>
      <td className="px-3 py-2">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${u.cls}`}>
          {u.icon}{item.days_waiting === 0 ? "Today" : `${item.days_waiting} day${item.days_waiting === 1 ? "" : "s"}`}
        </span>
        <div className="mt-0.5 text-[11px] text-slate-400">{fmtDate(item.requested_at)}</div>
      </td>
      {item.actionable ? (
        <>
          <td className="px-3 py-2">
            <input
              type="number" min="0" step="0.01" value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-24 rounded-md border border-slate-300 px-2 py-1 text-right text-sm"
            />
          </td>
          <td className="px-3 py-2">
            <select value={paymentType} onChange={(e) => setPaymentType(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1 text-xs">
              <option value="Cash">Cash</option>
              <option value="UPI">UPI</option>
            </select>
          </td>
        </>
      ) : (
        <td className="px-3 py-2 text-xs text-slate-400" colSpan={2}>
          Several serials on this one — open it to act per serial.
        </td>
      )}
      <td className="px-3 py-2">
        {item.next_stage_label ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-700">
            → {item.next_stage_label}
          </span>
        ) : (
          <span className="text-xs text-slate-400">Final stage</span>
        )}
      </td>
      <td className="px-3 py-2">
        <div className="flex items-center justify-end gap-2">
          {item.actionable && (
            <>
              <button
                type="button"
                disabled={busy || amount === ""}
                onClick={send}
                className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Send to {item.next_stage_label || "Admin"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowReturn((s) => !s)}
                className="rounded-md border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              >
                Return
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => navigate(item.href)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Open ↗
          </button>
        </div>
        {err && <div className="mt-1 text-right text-xs text-rose-600">{err}</div>}
        {showReturn && <ReturnBox busy={busy} onCancel={() => setShowReturn(false)} onConfirm={returnIt} />}
      </td>
    </tr>
  );
}

/** One stop: every installation and service payment sitting at the viewer's own stage of its
 * chain (installations: Service Role -> Service Manager -> [Sub Admin, over ₹2500] -> Accounts ->
 * Audit -> Admin; services: the shorter Service Role -> [Service Manager] -> Admin), with the
 * exact next stop shown per row, who last forwarded or returned it if anyone has, and an Open
 * link to jump straight into that record's own workflow wherever it's sitting. Admin's own final
 * stage lives in Ready to Pay instead -- this is every stage before that. */
export default function PaymentQueue() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    api.get("/api/dashboard/my-payment-queue")
      .then((r) => setItems(r.data))
      .catch((e) => setErr(formatApiError(e, "Failed to load your payment queue")))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const byStage = items.reduce((acc, i) => {
    (acc[i.stage_label] = acc[i.stage_label] || []).push(i);
    return acc;
  }, {});
  const stageLabels = Object.keys(byStage);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Payment Queue</h1>
        <p className="text-sm text-slate-500">
          Every installation and service payment waiting on your approval right now. Click the ID, or "Open", to jump straight into that record's own workflow. "Send to" forwards it on as raised; "Return" sends it back with a reason.
        </p>
      </div>

      {err && <div className="rounded bg-rose-50 p-3 text-sm text-rose-700">{err}</div>}

      {!loading && items.length === 0 && !err && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
          Nothing waiting on you right now.
        </div>
      )}

      {stageLabels.map((label) => (
        <div key={label} className="overflow-x-auto rounded-lg bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
            <span className="text-sm font-semibold text-slate-700">{label} approval</span>
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-bold text-slate-700">{byStage[label].length}</span>
          </div>
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Module</th>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Customer / Engineer</th>
                <th className="px-3 py-2">Waiting</th>
                <th className="px-3 py-2">Amount</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Next stop</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {byStage[label].map((item) => (
                <QueueRow key={`${item.module}-${item.entity_id}`} item={item} onActed={load} />
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {loading && <div className="rounded-lg bg-white p-6 text-center text-sm text-slate-500 shadow-sm">Loading…</div>}

      <p className="text-xs text-slate-500">
        Want to look at it another way?{" "}
        <button type="button" onClick={() => navigate("/installations")} className="text-brand-700 underline">
          Open Installation Requests
        </button>{" "}
        or{" "}
        <button type="button" onClick={() => navigate("/services")} className="text-brand-700 underline">
          Service Requests
        </button>.
      </p>
    </div>
  );
}
