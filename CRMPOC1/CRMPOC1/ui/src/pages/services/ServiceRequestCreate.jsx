import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { complaintsApi } from "../../api/complaints.js";
import { servicesApi } from "../../api/services.js";
import { mergeComplaintModelOptions } from "../../constants/complaintModels.js";

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function ServiceRequestCreate() {
  const navigate = useNavigate();
  const [modelOptions, setModelOptions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    request_date: todayStr(),
    query_type: "Service",
    customer_name: "",
    customer_mobile: "",
    customer_email: "",
    model_details: "",
    customer_address: "",
    problem_description: "",
    additional_remarks: "",
    send_request_number: true,
  });

  useEffect(() => {
    complaintsApi.modelOptions()
      .then((rows) => setModelOptions(mergeComplaintModelOptions(rows)))
      .catch(() => setModelOptions(mergeComplaintModelOptions([])));
  }, []);

  function set(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSubmitting(true);
    try {
      const created = await servicesApi.create({
        ...form,
        customer_email: form.customer_email || null,
        model_details: form.model_details || null,
        customer_address: form.customer_address || null,
        problem_description: form.problem_description || null,
        additional_remarks: form.additional_remarks || null,
      });
      navigate(`/services/${created.id}`);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((row) => row.msg).join("; ") : detail || "Failed to create service request");
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800">New Service Request</h1>
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <form onSubmit={submit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Complaint / Request Date</label>
            <input type="date" value={form.request_date} onChange={(e) => set("request_date", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Query Type</label>
            <input value={form.query_type} readOnly className={`${fieldClass} bg-slate-50`} />
          </div>
          <div>
            <label className={labelClass}>Customer Name *</label>
            <input required value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Customer Mobile *</label>
            <input required value={form.customer_mobile} onChange={(e) => set("customer_mobile", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={form.customer_email} onChange={(e) => set("customer_email", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Model Details</label>
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
          <textarea rows={2} value={form.additional_remarks} onChange={(e) => set("additional_remarks", e.target.value)} className={fieldClass} />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={form.send_request_number} onChange={(e) => set("send_request_number", e.target.checked)} className="h-4 w-4" />
          Send request number to customer
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={() => navigate("/services")} className="rounded-md border border-slate-300 px-4 py-2 text-sm">Cancel</button>
          <button type="submit" disabled={submitting} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
            {submitting ? "Saving..." : "Create Service Request"}
          </button>
        </div>
      </form>
    </div>
  );
}
