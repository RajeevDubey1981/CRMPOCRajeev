import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { historicalInstallationsApi } from "../../api/historicalInstallations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";

function money(value) {
  return Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function HistoricalInstallation() {
  const { user } = useAuth();
  const canComplete = hasPermission(user, "historical_installations", "can_edit");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({ installation_date: "", reason: "", payment_total: "0.00", payment_type: "Cash" });
  const [proof, setProof] = useState(null);
  const [operationKey, setOperationKey] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    if (query.trim().length < 2 || preview) {
      setSuggestions([]);
      return undefined;
    }
    timer.current = setTimeout(async () => {
      setSearching(true);
      try { setSuggestions(await historicalInstallationsApi.search(query.trim())); }
      catch { setSuggestions([]); }
      finally { setSearching(false); }
    }, 300);
    return () => clearTimeout(timer.current);
  }, [query, preview]);

  async function chooseOrder(row) {
    setQuery(row.order_no || "");
    setSuggestions([]);
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await historicalInstallationsApi.preview(row.order_id);
      setPreview(data);
      setOperationKey(crypto.randomUUID());
      setForm((current) => ({ ...current, payment_total: Number(data.summary.suggested_payment_total || 0).toFixed(2) }));
    } catch (e) {
      setError(e.response?.data?.detail || "Could not load the order preview.");
    } finally { setLoading(false); }
  }

  function reset() {
    setQuery(""); setSuggestions([]); setPreview(null); setReviewing(false); setResult(null); setError(""); setProof(null); setOperationKey("");
    setForm({ installation_date: "", reason: "", payment_total: "0.00", payment_type: "Cash" });
  }

  function validate() {
    if (!form.installation_date) return "Installation date is required.";
    if (!form.reason.trim()) return "Completion reason is required.";
    if (form.payment_total === "" || Number(form.payment_total) < 0) return "Enter a valid payment total.";
    if (preview?.blocking_errors?.length) return preview.blocking_errors[0];
    return "";
  }

  function openReview() {
    const message = validate();
    if (message) { setError(message); return; }
    setError(""); setReviewing(true);
  }

  async function submit() {
    setSubmitting(true); setError("");
    try {
      const data = await historicalInstallationsApi.complete({
        order_id: preview.order.id,
        preview_token: preview.preview_token,
        operation_key: operationKey,
        ...form,
        payment_total: Number(form.payment_total),
      }, proof);
      setResult(data); setReviewing(false);
    } catch (e) {
      setError(e.response?.data?.detail || "Historical completion failed. No changes were saved.");
      setReviewing(false);
    } finally { setSubmitting(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Historical Installation</h1>
          <p className="mt-1 text-sm text-slate-500">Complete an old GeM order with an auditable installation and payment record.</p>
        </div>
        <Link to="/serials/history" className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700">Serial History</Link>
      </div>

      <section className="rounded-xl bg-white p-5 shadow-sm">
        <label className="mb-2 block text-sm font-medium text-slate-700">GeM order number</label>
        <div className="relative">
          <input value={query} disabled={!!preview} onChange={(e) => setQuery(e.target.value)} placeholder="Enter GeM order number..."
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none" />
          {!preview && (suggestions.length > 0 || searching) && (
            <div className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-white shadow-lg">
              {searching && <div className="px-3 py-2 text-sm text-slate-400">Searching...</div>}
              {suggestions.map((row) => <button type="button" key={row.order_id} onClick={() => chooseOrder(row)} className="block w-full px-3 py-2 text-left hover:bg-brand-50">
                <div className="font-medium text-slate-800">{row.order_no}</div><div className="text-xs text-slate-500">{row.customer_name || "No customer"} · {row.status}</div>
              </button>)}
            </div>
          )}
        </div>
        {preview && <button type="button" onClick={reset} className="mt-3 text-sm font-medium text-brand-700">Choose another order</button>}
      </section>

      {error && <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      {loading && <div className="rounded-xl bg-white p-6 text-center text-slate-500 shadow-sm">Loading order...</div>}

      {result && <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
        <h2 className="font-semibold text-emerald-900">Historical installation completed</h2>
        <p className="mt-1 text-sm text-emerald-800">Audit #{result.audit_id} · {result.created_count} requests created · {result.completed_count} completed · {result.skipped_count} already completed.</p>
        {result.incomplete_count > 0 && <p className="mt-2 text-sm font-medium text-amber-800">{result.incomplete_count} item rows without serials remain unchanged.</p>}
        <div className="mt-3 flex gap-4 text-sm"><Link className="font-medium text-brand-700" to={`/orders/${result.order_id}`}>Open order</Link><button type="button" onClick={reset} className="font-medium text-brand-700">Complete another order</button></div>
      </section>}

      {preview && !result && <>
        {!canComplete && <div className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-800">You have view access. Edit permission is required to complete a historical installation.</div>}
        {canComplete && <section className="rounded-xl bg-white p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div><div className="text-xs uppercase text-slate-500">Order</div><div className="font-semibold">{preview.order.order_no}</div></div>
            <div><div className="text-xs uppercase text-slate-500">Customer</div><div className="font-semibold">{preview.order.customer_name || "Missing"}</div><div className="text-xs text-slate-500">{preview.order.customer_contact || "Missing contact"}</div></div>
            <div><div className="text-xs uppercase text-slate-500">Current status</div><div className="font-semibold">{preview.order.status}</div></div>
            <div><div className="text-xs uppercase text-slate-500">Order date</div><div className="font-semibold">{preview.order.order_date}</div></div>
          </div>
          {preview.summary.missing_serial_items > 0 && <div className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">Warning: {preview.summary.missing_serial_items} rows have no serial and will remain unchanged, although the order will become Completed.</div>}
          {preview.blocking_errors.map((message) => <div key={message} className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{message}</div>)}
        </section>}

        <section className="overflow-hidden rounded-xl bg-white shadow-sm">
          <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead className="bg-slate-100 text-left text-slate-600"><tr>
            <th className="px-3 py-2">Item</th><th className="px-3 py-2">Serial 1</th><th className="px-3 py-2">Serial 2</th><th className="px-3 py-2">Item status</th><th className="px-3 py-2">Installation requests</th>
          </tr></thead><tbody className="divide-y">
            {preview.items.map((item) => <tr key={item.id} className={item.missing_serial ? "bg-amber-50" : ""}>
              <td className="px-3 py-3"><div className="font-medium">{item.item_name || "Unknown item"}</div><div className="text-xs text-slate-500">{item.item_code || "-"}</div></td>
              <td className="px-3 py-3 font-mono text-xs">{item.serial_no || "Missing"}</td><td className="px-3 py-3 font-mono text-xs">{item.serial_no_2 || "-"}</td><td className="px-3 py-3">{item.installation_status}</td>
              <td className="px-3 py-3">{item.installation_requests.length ? item.installation_requests.map((request) => <div key={request.id}>#{request.id} · {request.status}{request.engineer_name ? ` · ${request.engineer_name}` : ""}</div>) : (item.missing_serial ? "None" : "Will create historical request")}</td>
            </tr>)}
          </tbody></table></div>
        </section>

        <section className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Completion details</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">Installation date *<input type="date" value={form.installation_date} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setForm({ ...form, installation_date: e.target.value })} className="mt-1 block w-full rounded-md border px-3 py-2" /></label>
            <label className="text-sm font-medium text-slate-700">Payment type *<select value={form.payment_type} onChange={(e) => setForm({ ...form, payment_type: e.target.value })} className="mt-1 block w-full rounded-md border px-3 py-2"><option>Cash</option><option>UPI</option></select></label>
            <label className="text-sm font-medium text-slate-700">Total payment amount *<input type="number" min="0" step="0.01" value={form.payment_total} onChange={(e) => setForm({ ...form, payment_total: e.target.value })} className="mt-1 block w-full rounded-md border px-3 py-2" /></label>
            <label className="text-sm font-medium text-slate-700">Payment proof (optional)<input type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={(e) => setProof(e.target.files?.[0] || null)} className="mt-1 block w-full text-sm" /></label>
            <label className="text-sm font-medium text-slate-700 md:col-span-2">Reason *<textarea rows="3" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="mt-1 block w-full rounded-md border px-3 py-2" placeholder="Explain why this historical completion is being recorded." /></label>
          </div>
          <div className="mt-5 flex justify-end"><button type="button" onClick={openReview} className="rounded-md bg-brand-600 px-5 py-2 text-sm font-semibold text-white">Review completion</button></div>
        </section>
      </>}

      {reviewing && preview && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"><div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Confirm historical completion</h2>
        <p className="mt-2 text-sm text-slate-600">Order <b>{preview.order.order_no}</b> will become Completed. This creates a permanent audit record.</p>
        <dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-4 text-sm"><div><dt className="text-slate-500">Serial items</dt><dd className="font-semibold">{preview.summary.serial_items}</dd></div><div><dt className="text-slate-500">Requests to create</dt><dd className="font-semibold">{preview.summary.requests_to_create}</dd></div><div><dt className="text-slate-500">Requests to complete</dt><dd className="font-semibold">{preview.summary.requests_to_complete}</dd></div><div><dt className="text-slate-500">Already completed</dt><dd className="font-semibold">{preview.summary.requests_already_completed}</dd></div><div><dt className="text-slate-500">Payment</dt><dd className="font-semibold">₹{money(form.payment_total)} {form.payment_type}</dd></div><div><dt className="text-slate-500">Missing serial rows</dt><dd className="font-semibold">{preview.summary.missing_serial_items}</dd></div></dl>
        <div className="mt-5 flex justify-end gap-3"><button type="button" disabled={submitting} onClick={() => setReviewing(false)} className="rounded-md border px-4 py-2 text-sm">Back</button><button type="button" disabled={submitting} onClick={submit} className="rounded-md bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{submitting ? "Completing..." : "Confirm and complete"}</button></div>
      </div></div>}
    </div>
  );
}
