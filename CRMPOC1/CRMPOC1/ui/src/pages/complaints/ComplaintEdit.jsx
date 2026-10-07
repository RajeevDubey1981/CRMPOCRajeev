import { useEffect, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { complaintsApi } from "../../api/complaints.js";
import { mergeComplaintModelOptions } from "../../constants/complaintModels.js";
import PlaceFields, { placeProblem } from "../../components/PlaceFields.jsx";
import NearbyEngineers from "../../components/NearbyEngineers.jsx";
import { fillPlaceFromAddress } from "../../utils/place.js";

const QUERY_TYPES = ["Service", "Installation", "Sales", "Others"];
const STATUSES = ["Pending", "Under Process", "In Process", "Resolved", "Rejected"];

export default function ComplaintEdit({ complaint, onClose, onSaved }) {
  const [modelOptions, setModelOptions] = useState([]);
  const [form, setForm] = useState({
    customer_name: complaint.customer_name || "",
    customer_mobile: complaint.customer_mobile || "",
    customer_email: complaint.customer_email || "",
    customer_address: complaint.customer_address || "",
    pincode: complaint.pincode || "",
    state: complaint.state || "",
    district: complaint.district || "",
    query_type: complaint.query_type || "Service",
    model_details: complaint.model_details || "",
    problem_description: complaint.problem_description || "",
    remark: complaint.remark || "",
    status: complaint.status || "Pending",
    priority: complaint.priority || "Normal",
  });
  const [busy, setBusy] = useState(false);
  const [submitErr, setSubmitErr] = useState("");

  useEffect(() => {
    complaintsApi.modelOptions()
      .then((rows) => setModelOptions(mergeComplaintModelOptions(rows)))
      .catch(() => setModelOptions(mergeComplaintModelOptions([])));
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit() {
    setSubmitErr("");
    const digits = form.customer_mobile.replace(/\D/g, "");
    if (digits.length < 10) {
      setSubmitErr("Mobile number must contain at least 10 digits");
      return;
    }
    const placeErr = placeProblem(form);
    if (placeErr) {
      setSubmitErr(placeErr);
      return;
    }
    setBusy(true);
    try {
      const body = {
        customer_name: form.customer_name.trim(),
        customer_mobile: digits,
        customer_email: form.customer_email.trim() || null,
        customer_address: form.customer_address.trim() || null,
        pincode: form.pincode.trim(),
        state: form.state,
        district: form.district.trim(),
        query_type: form.query_type,
        model_details: form.model_details || null,
        problem_description: form.problem_description.trim() || null,
        remark: form.remark.trim() || null,
        status: form.status,
        priority: form.priority,
      };
      await complaintsApi.update(complaint.id, body);
      onSaved?.();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setSubmitErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to update");
    } finally {
      setBusy(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  return (
    <Modal open={true} onClose={onClose} title={`Edit complaint — ${complaint.comp_no}`} maxWidth="max-w-3xl">
      <div className="space-y-4">
        {submitErr && (
          <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>Customer name *</label>
            <input
              required
              value={form.customer_name}
              onChange={(e) => set("customer_name", e.target.value)}
              className={fieldClass}
            />
          </div>
          <div>
            <label className={labelClass}>Mobile *</label>
            <input
              required
              value={form.customer_mobile}
              onChange={(e) => set("customer_mobile", e.target.value)}
              className={fieldClass}
            />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input
              type="email"
              value={form.customer_email}
              onChange={(e) => set("customer_email", e.target.value)}
              className={fieldClass}
            />
          </div>
          <div>
            <label className={labelClass}>Query type</label>
            <select value={form.query_type} onChange={(e) => set("query_type", e.target.value)} className={fieldClass}>
              {QUERY_TYPES.map((q) => <option key={q} value={q}>{q}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Model</label>
            <select value={form.model_details} onChange={(e) => set("model_details", e.target.value)} className={fieldClass}>
              <option value="">Select model</option>
              {modelOptions.map((model) => (
                <option key={model.id} value={model.item_name}>{model.item_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Status</label>
            <select value={form.status} onChange={(e) => set("status", e.target.value)} className={fieldClass}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Priority</label>
            <select
              value={form.priority}
              onChange={(e) => set("priority", e.target.value)}
              className={`${fieldClass} ${form.priority === "High" ? "border-orange-500 bg-orange-50 font-semibold text-orange-800" : ""}`}
            >
              <option value="Normal">Normal</option>
              <option value="High">HIGH priority (blinks and is shown first)</option>
            </select>
          </div>
        </div>

        <div>
          <label className={labelClass}>Address</label>
          <textarea
            rows={2}
            value={form.customer_address}
            onChange={(e) => set("customer_address", e.target.value)}
            className={fieldClass}
          />
        </div>

        <div className="space-y-3 rounded-md border border-sky-200 bg-sky-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-sky-800">Customer location</div>
          <PlaceFields value={form} onChange={(patch) => setForm((f) => ({ ...f, ...patch }))} />
          <NearbyEngineers place={form} address={form.customer_address} />
        </div>

        <div>
          <label className={labelClass}>Problem description</label>
          <textarea
            rows={3}
            value={form.problem_description}
            onChange={(e) => set("problem_description", e.target.value)}
            className={fieldClass}
          />
        </div>

        <div>
          <label className={labelClass}>Remark</label>
          <textarea
            rows={2}
            value={form.remark}
            onChange={(e) => set("remark", e.target.value)}
            className={fieldClass}
          />
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
