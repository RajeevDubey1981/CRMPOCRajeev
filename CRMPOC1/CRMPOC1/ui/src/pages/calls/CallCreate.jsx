import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { callsApi } from "../../api/calls.js";

const CALL_TYPES = ["Inbound", "Outbound", "Callback"];
const PRIORITIES = ["Low", "Medium", "High"];

function nowStr() {
  return new Date().toISOString().slice(0, 16);
}

export default function CallCreate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const complaintId = searchParams.get("complaint_id");

  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const errRef = useRef(null);
  const [form, setForm] = useState({
    call_datetime: nowStr(),
    customer_name: "",
    customer_email: "",
    phone: "",
    call_type: "Outbound",
    priority: "Medium",
    duration_secs: "",
    followup_date: "",
    notes: "",
    follow_up_notes: "",
    complaint_id: complaintId ? parseInt(complaintId, 10) : "",
  });

  useEffect(() => {
    if (complaintId) {
      setForm((f) => ({ ...f, complaint_id: parseInt(complaintId, 10) }));
    }
  }, [complaintId]);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSubmitting(true);
    try {
      const body = {
        call_datetime: new Date(form.call_datetime).toISOString(),
        customer_name: form.customer_name || null,
        customer_email: form.customer_email || null,
        phone: form.phone || null,
        call_type: form.call_type,
        priority: form.priority,
        status: "Completed",
        duration_secs: form.duration_secs ? parseInt(form.duration_secs, 10) : null,
        followup_date: form.followup_date ? new Date(form.followup_date).toISOString() : null,
        notes: form.notes || null,
        follow_up_notes: form.follow_up_notes || null,
        complaint_id: form.complaint_id ? parseInt(form.complaint_id, 10) : null,
      };
      const created = await callsApi.create(body);
      if (complaintId) {
        navigate(`/complaints/${complaintId}`);
      } else {
        navigate(`/calls/${created.id}`);
      }
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to create");
      setTimeout(() => errRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Log Call</h1>
        {complaintId && (
          <button
            onClick={() => navigate(`/complaints/${complaintId}`)}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
          >
            ← Back to complaint
          </button>
        )}
      </div>

      {err && <div ref={errRef} className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>}

      <form onSubmit={submit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Call Date & Time *</label>
            <input required type="datetime-local" value={form.call_datetime} onChange={(e) => set("call_datetime", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Call Type</label>
            <select value={form.call_type} onChange={(e) => set("call_type", e.target.value)} className={fieldClass}>
              {CALL_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Priority</label>
            <select value={form.priority} onChange={(e) => set("priority", e.target.value)} className={fieldClass}>
              {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Customer Name</label>
            <input value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Phone</label>
            <input value={form.phone} onChange={(e) => set("phone", e.target.value)} className={fieldClass} placeholder="10-digit" />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={form.customer_email} onChange={(e) => set("customer_email", e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Duration (seconds)</label>
            <input type="number" value={form.duration_secs} onChange={(e) => set("duration_secs", e.target.value)} className={fieldClass} placeholder="e.g., 300" />
          </div>
          <div>
            <label className={labelClass}>Complaint ID (if related)</label>
            <input
              type="text"
              value={form.complaint_id || ""}
              disabled
              className={fieldClass + " bg-slate-100 cursor-not-allowed text-slate-500"}
              placeholder="Auto-linked from complaint"
            />
          </div>
          <div>
            <label className={labelClass}>Follow-up Date</label>
            <input type="datetime-local" value={form.followup_date} onChange={(e) => set("followup_date", e.target.value)} className={fieldClass} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>Call Notes</label>
            <textarea rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} className={fieldClass} placeholder="Call summary, what was discussed, etc." />
          </div>
          <div>
            <label className={labelClass}>Follow-up Notes</label>
            <textarea rows={3} value={form.follow_up_notes} onChange={(e) => set("follow_up_notes", e.target.value)} className={fieldClass} placeholder="What needs to be done in follow-up" />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => complaintId ? navigate(`/complaints/${complaintId}`) : navigate("/calls")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >Cancel</button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Log call"}
          </button>
        </div>
      </form>
    </div>
  );
}
