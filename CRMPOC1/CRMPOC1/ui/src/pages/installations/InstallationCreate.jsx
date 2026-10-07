import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { installationsApi } from "../../api/installations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import PlaceFields, { placeProblem } from "../../components/PlaceFields.jsx";
import NearbyEngineers from "../../components/NearbyEngineers.jsx";
import { fillPlaceFromAddress } from "../../utils/place.js";

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function InstallationCreate() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = (user?.role || "").toLowerCase();
  const isCallcenter = role === "callcenter";
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [orderSearch, setOrderSearch] = useState("");
  const [orderOptions, setOrderOptions] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [form, setForm] = useState({
    request_date: todayStr(),
    customer_name: "",
    contact_number: "",
    customer_email: "",
    address: "",
    pincode: "",
    state: "",
    district: "",
    product_name: "",
  });

  useEffect(() => {
    if (!isCallcenter) return undefined;
    const query = orderSearch.trim();
    if (query.length < 2) {
      setOrderOptions([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      installationsApi.searchOrders({ mobile: query, name: query, order_no: query })
        .then(setOrderOptions)
        .catch(() => setOrderOptions([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [orderSearch, isCallcenter]);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  function applyOrder(option) {
    setSelectedOrder(option);
    setForm((f) => ({
      ...f,
      customer_name: option.customer_name || f.customer_name,
      contact_number: option.customer_mobile || f.contact_number,
      customer_email: option.customer_email || f.customer_email,
      address: option.customer_address || f.address,
      ...fillPlaceFromAddress(f, option.customer_address),
    }));
    setOrderSearch("");
    setOrderOptions([]);
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!/^\d{10,}$/.test(form.contact_number.replace(/\D/g, ""))) {
      setErr("Phone number must contain at least 10 digits");
      return;
    }
    const placeErr = placeProblem(form);
    if (placeErr) {
      setErr(placeErr);
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        ...form,
        request_date: form.request_date || null,
        address: form.address || null,
        customer_email: form.customer_email || null,
        product_name: form.product_name || null,
        source: isCallcenter ? "callcenter" : undefined,
        order_id: selectedOrder?.order_id || null,
      };
      const created = await installationsApi.create(body);
      navigate(`/installations/${created.id}`);
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
      <h1 className="text-2xl font-semibold text-slate-800">New Installation Request</h1>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <form onSubmit={submit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm">
        {isCallcenter && (
          <div className="rounded-md border border-sky-200 bg-sky-50 p-4 text-sm">
            <div className="font-medium text-sky-900">Identify customer order (optional)</div>
            <p className="mt-1 text-xs text-sky-800">
              Search by mobile, customer name, or order number. Serial number is not required at this stage.
            </p>
            <input
              type="text"
              value={orderSearch}
              onChange={(e) => setOrderSearch(e.target.value)}
              placeholder="Search order..."
              className={`${fieldClass} mt-3`}
            />
            {orderOptions.length > 0 && (
              <div className="mt-2 max-h-48 space-y-2 overflow-auto">
                {orderOptions.map((option) => (
                  <button
                    key={option.order_id}
                    type="button"
                    onClick={() => applyOrder(option)}
                    className="block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:bg-sky-100"
                  >
                    <div className="font-medium">Order {option.order_no || `#${option.order_id}`}</div>
                    <div className="text-xs text-slate-500">{[option.customer_name, option.customer_mobile].filter(Boolean).join(" • ")}</div>
                  </button>
                ))}
              </div>
            )}
            {selectedOrder && (
              <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
                Linked order: <span className="font-mono">{selectedOrder.order_no || `#${selectedOrder.order_id}`}</span>
                <button type="button" onClick={() => setSelectedOrder(null)} className="ml-3 text-emerald-700 underline">Clear</button>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Request Date</label>
            <input type="date" value={form.request_date} onChange={(e) => set("request_date", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Product Name</label>
            <input value={form.product_name} onChange={(e) => set("product_name", e.target.value)} className={fieldClass} placeholder="e.g., Split AC 1.5 Ton" />
          </div>
          <div>
            <label className={labelClass}>Customer Name *</label>
            <input required value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Phone *</label>
            <input
              required
              value={form.contact_number}
              onChange={(e) => set("contact_number", e.target.value)}
              pattern="[0-9\s\-+()]{10,}"
              className={fieldClass}
              placeholder="10-digit"
            />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={form.customer_email} onChange={(e) => set("customer_email", e.target.value)} className={fieldClass} />
          </div>
        </div>

        <div>
          <label className={labelClass}>Address</label>
          <textarea
            rows={3}
            value={form.address}
            onChange={(e) => set("address", e.target.value)}
            onBlur={() => setForm((f) => ({ ...f, ...fillPlaceFromAddress(f, f.address) }))}
            className={fieldClass}
          />
        </div>

        <div className="space-y-3 rounded-md border border-sky-200 bg-sky-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-sky-800">Customer location</div>
          <PlaceFields value={form} onChange={(patch) => setForm((f) => ({ ...f, ...patch }))} />
          <NearbyEngineers place={form} address={form.address} />
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate("/installations")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >Cancel</button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Create request"}
          </button>
        </div>
      </form>
    </div>
  );
}
