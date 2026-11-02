import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { servicesApi } from "../../api/services.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function fmtDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function StatusPill({ label }) {
  const styles = {
    "Payment received": "bg-emerald-50 text-emerald-700 border-emerald-200",
    "Awaiting approval": "bg-amber-50 text-amber-700 border-amber-200",
    "Rejected": "bg-rose-50 text-rose-700 border-rose-200",
  };
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[label] || "bg-slate-100 text-slate-600 border-slate-200"}`}>
      {label}
    </span>
  );
}

export default function MyPayments() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    setErr("");
    servicesApi.myPayments()
      .then(setData)
      .catch((error) => setErr(error.response?.data?.detail || "Failed to load payments"))
      .finally(() => setLoading(false));
  }, []);

  const items = data?.items || [];
  const summary = data?.summary;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Payment</h1>
        <p className="text-sm text-slate-500">Every payment you've raised, and where it stands.</p>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {loading && <div className="text-sm text-slate-500">Loading…</div>}

      {summary && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">Raised this month</div>
            <div className="mt-1 text-xl font-semibold text-slate-800 tabular-nums">{fmtMoney(summary.raised_this_month)}</div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">Awaiting approval</div>
            <div className="mt-1 text-xl font-semibold text-amber-700 tabular-nums">{fmtMoney(summary.awaiting_approval)}</div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">Received this month</div>
            <div className="mt-1 text-xl font-semibold text-emerald-700 tabular-nums">{fmtMoney(summary.received_this_month)}</div>
          </div>
        </div>
      )}

      {!loading && items.length === 0 && (
        <div className="rounded-lg bg-white p-6 text-sm text-slate-500 shadow-sm">You haven't raised any payments yet.</div>
      )}

      {items.length > 0 && (
        <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-700">
              <tr>
                <th className="px-3 py-2">Request</th>
                <th className="px-3 py-2">Customer</th>
                <th className="px-3 py-2">Amount</th>
                <th className="px-3 py-2">Raised</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.payment_request_id}>
                  <td className="px-3 py-2 font-mono text-xs">{item.request_no}</td>
                  <td className="px-3 py-2">{item.customer_name}</td>
                  <td className="px-3 py-2 tabular-nums">{fmtMoney(item.amount)}</td>
                  <td className="px-3 py-2 text-slate-500">{fmtDate(item.requested_at)}</td>
                  <td className="px-3 py-2">
                    <StatusPill label={item.status_label} />
                    {item.status_label === "Awaiting approval" && item.stage_label && (
                      <div className="mt-0.5 text-xs text-slate-400">with {item.stage_label}</div>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/services/${item.service_request_id}`} className="text-brand-600 hover:underline">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
