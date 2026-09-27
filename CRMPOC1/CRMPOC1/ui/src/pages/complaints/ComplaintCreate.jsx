import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { complaintsApi } from "../../api/complaints.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { mergeComplaintModelOptions } from "../../constants/complaintModels.js";

const QUERY_TYPES = ["Service", "Installation", "Sales", "Others"];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function ComplaintCreate() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const isCallcenter = role === "callcenter";

  const [modelOptions, setModelOptions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerMatches, setCustomerMatches] = useState([]);
  const [customerSearchLoading, setCustomerSearchLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [form, setForm] = useState({
    comp_date: todayStr(),
    customer_name: "",
    customer_mobile: "",
    customer_email: "",
    customer_address: "",
    model_details: "",
    problem_description: "",
    query_type: "Service",
    remark: "",
    send_sms: true,
  });

  useEffect(() => {
    complaintsApi.modelOptions()
      .then((rows) => setModelOptions(mergeComplaintModelOptions(rows)))
      .catch(() => setModelOptions(mergeComplaintModelOptions([])));
  }, []);

  useEffect(() => {
    const search = customerSearch.trim();
    if (search.length < 2) {
      setCustomerMatches([]);
      return undefined;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      setCustomerSearchLoading(true);
      complaintsApi.searchCustomers({ search })
      .then((result) => {
        if (active) setCustomerMatches(result);
      })
      .catch(() => {
        if (active) setCustomerMatches([]);
      })
      .finally(() => {
        if (active) setCustomerSearchLoading(false);
      });
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [customerSearch]);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  function applyOrderToForm(order) {
    if (!order) return;
    setForm((f) => ({
      ...f,
      customer_name: order.customer_name || f.customer_name,
      customer_mobile: order.customer_contact || order.customer_mobile || f.customer_mobile,
      customer_email: order.customer_email || f.customer_email,
      customer_address: order.customer_address || f.customer_address,
    }));
    setSelectedOrder(order);
  }

  function selectCustomer(result) {
    applyOrderToForm(result);
    setCustomerSearch(result.order_no || result.customer_name || result.customer_mobile || "");
    setCustomerMatches([]);
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!/^\d{10,}$/.test(form.customer_mobile.replace(/\D/g, ""))) {
      setErr("Mobile number must contain at least 10 digits");
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        ...form,
        comp_date: form.comp_date || null,
        customer_email: form.customer_email || null,
        customer_address: form.customer_address || null,
        model_details: form.model_details || null,
        problem_description: form.problem_description || null,
        remark: form.remark || null,
      };
      const created = await complaintsApi.create(body);
      navigate(`/complaints/${created.id}`);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to create");
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800">New Complaint</h1>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <form onSubmit={submit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm">
        <div className="rounded-md border border-sky-200 bg-sky-50 p-4">
          <label className="block text-sm font-medium text-sky-900" htmlFor="customer-order-search">
            Search customer or order
          </label>
          <p className="mt-1 text-xs text-sky-800">
            Search by customer name, mobile, order number, OEM bill, or vendor to prefill customer details.
          </p>
          <div className="relative mt-3">
            <input
              id="customer-order-search"
              value={customerSearch}
              onChange={(e) => setCustomerSearch(e.target.value)}
              placeholder="Search customer name / mobile / order / OEM bill / vendor"
              className={fieldClass}
              autoComplete="off"
            />
            {(customerSearchLoading || customerMatches.length > 0) && (
              <div className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
                {customerSearchLoading && <div className="px-3 py-2 text-sm text-slate-500">Searching...</div>}
                {!customerSearchLoading && customerMatches.map((result, index) => (
                  <button
                    type="button"
                    key={`${result.source_type}-${result.order_id || "complaint"}-${index}`}
                    onClick={() => selectCustomer(result)}
                    className="block w-full border-b border-slate-100 px-3 py-2 text-left hover:bg-sky-50 last:border-b-0"
                  >
                    <div className="text-sm font-medium text-slate-800">{result.customer_name || "Unknown customer"}</div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {[result.customer_mobile, result.order_no, result.oem_bill_no, result.vendor_name].filter(Boolean).join(" · ") || "Customer record"}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          {selectedOrder && (
            <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
              Selected: <span className="font-mono">{selectedOrder.order_no || selectedOrder.customer_name}</span>
              <button type="button" onClick={() => setSelectedOrder(null)} className="ml-3 text-emerald-700 underline">Clear</button>
            </div>
          )}
        </div>
        {false && isCallcenter && (
          <div className="rounded-md border border-sky-200 bg-sky-50 p-4">
            <div className="text-sm font-medium text-sky-900">Search Orders</div>
            <p className="mt-1 text-xs text-sky-800">
              Search by customer name, mobile, order number, OEM bill, or vendor to prefill customer details.
            </p>
            <div className="mt-3">
              <OrderSearchBar
                value={orderSearchInput}
                onChange={setOrderSearchInput}
                onDebouncedSearch={setOrderSearchActive}
                onSelect={handleOrderSuggestionSelect}
              />
            </div>
            {orderSearchActive && (
              <div className="mt-4 overflow-x-auto rounded-md border border-slate-200 bg-white">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-100 text-left text-slate-700">
                    <tr>
                      <th className="px-3 py-2">Order No</th>
                      <th className="px-3 py-2">OEM Bill</th>
                      <th className="px-3 py-2">Customer</th>
                      <th className="px-3 py-2">Vendor</th>
                      <th className="px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {orderSearchLoading && (
                      <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-400">Loading orders…</td></tr>
                    )}
                    {!orderSearchLoading && orderMatches.items.length === 0 && (
                      <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-400">No orders found.</td></tr>
                    )}
                    {!orderSearchLoading && orderMatches.items.map((order) => (
                      <tr
                        key={order.id}
                        onClick={() => loadAndApplyOrder(order.id)}
                        className="cursor-pointer hover:bg-sky-50"
                      >
                        <td className="px-3 py-2 font-mono text-xs">{order.order_no || "—"}</td>
                        <td className="px-3 py-2">{order.oem_bill_no || "—"}</td>
                        <td className="px-3 py-2">{order.customer_name || "—"}</td>
                        <td className="px-3 py-2">{order.vendor_name || "—"}</td>
                        <td className="px-3 py-2">{order.status || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {selectedOrder && (
              <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
                Linked order: <span className="font-mono">{selectedOrder.order_no || `#${selectedOrder.id}`}</span>
                <button
                  type="button"
                  onClick={() => setSelectedOrder(null)}
                  className="ml-3 text-emerald-700 underline"
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Complaint Date</label>
            <input type="date" value={form.comp_date} onChange={(e) => set("comp_date", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Query Type</label>
            <select value={form.query_type} onChange={(e) => set("query_type", e.target.value)} className={fieldClass}>
              {QUERY_TYPES.map((q) => <option key={q} value={q}>{q}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Customer Name *</label>
            <input required value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Customer Mobile *</label>
            <input
              required
              value={form.customer_mobile}
              onChange={(e) => set("customer_mobile", e.target.value)}
              pattern="[0-9\s\-+()]{10,}"
              className={fieldClass}
              placeholder="10-digit"
            />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={form.customer_email} onChange={(e) => set("customer_email", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Product Details</label>
            <select
              value={form.model_details}
              onChange={(e) => set("model_details", e.target.value)}
              className={fieldClass}
            >
              <option value="">Select model</option>
              {modelOptions.map((model) => (
                <option key={model.id} value={model.item_name}>{model.item_name}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className={labelClass}>Address</label>
          <textarea rows={2} value={form.customer_address} onChange={(e) => set("customer_address", e.target.value)} className={fieldClass} />
        </div>

        <div>
          <label className={labelClass}>Problem Description</label>
          <textarea rows={3} value={form.problem_description} onChange={(e) => set("problem_description", e.target.value)} className={fieldClass} />
        </div>

        <div>
          <label className={labelClass}>Additional Remarks</label>
          <textarea rows={2} value={form.remark} onChange={(e) => set("remark", e.target.value)} className={fieldClass} />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={form.send_sms}
            onChange={(e) => set("send_sms", e.target.checked)}
            className="h-4 w-4"
          />
          Send Request No on mobile (SMS will be wired in sprint 6)
        </label>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate(isCallcenter ? "/dashboard" : "/complaints")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >Cancel</button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Create complaint"}
          </button>
        </div>
      </form>
    </div>
  );
}
