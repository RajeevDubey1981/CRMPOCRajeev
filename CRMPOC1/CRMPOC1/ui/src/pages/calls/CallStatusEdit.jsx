import { CALL_PURPOSES } from "../../utils/callPurposes.js";
import { useEffect, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { callsApi } from "../../api/calls.js";
import { usersApi } from "../../api/complaints.js";

const STATUSES = ["Completed", "Busy", "No Answer", "Call Back", "Not Interested"];
const PRIORITIES = ["Low", "Medium", "High"];
const FOLLOWUP_STATUSES = ["Pending", "Completed"];

export default function CallStatusEdit({ call, onClose, onSaved }) {
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState({
    status: call.status || "Completed",
    priority: call.priority || "Medium",
    purpose: call.purpose || "",
    assigned_to: call.assigned_to || "",
    duration_secs: call.duration_secs || "",
    followup_date: call.followup_date ? new Date(call.followup_date).toISOString().slice(0, 16) : "",
    follow_up_status: call.follow_up_status || "",
    notes: call.notes || "",
    follow_up_notes: call.follow_up_notes || "",
  });
  const [busy, setBusy] = useState(false);
  const [submitErr, setSubmitErr] = useState("");

  useEffect(() => {
    usersApi.list()
      .then(setStaff)
      .catch(() => setStaff([]));
  }, []);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  async function submit() {
    setSubmitErr("");
    setBusy(true);
    try {
      const body = {
        status: form.status,
        priority: form.priority,
        purpose: form.purpose || null,
        assigned_to: form.assigned_to ? parseInt(form.assigned_to, 10) : null,
        duration_secs: form.duration_secs ? parseInt(form.duration_secs, 10) : null,
        followup_date: form.followup_date ? new Date(form.followup_date).toISOString() : null,
        follow_up_status: form.follow_up_status || null,
        notes: form.notes || null,
        follow_up_notes: form.follow_up_notes || null,
      };
      await callsApi.update(call.id, body);
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
    <Modal open={true} onClose={onClose} title={`Edit call — ${call.ref_no}`} maxWidth="max-w-2xl">
      <div className="space-y-4">
        {submitErr && (
          <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>Status</label>
            <select value={form.status} onChange={(e) => set("status", e.target.value)} className={fieldClass}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className={labelClass}>Purpose</label>
            <select value={form.purpose} onChange={(e) => set("purpose", e.target.value)} className={fieldClass}>
              <option value="">Not set</option>
              {CALL_PURPOSES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Priority</label>
            <select value={form.priority} onChange={(e) => set("priority", e.target.value)} className={fieldClass}>
              {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div>
            <label className={labelClass}>Duration (seconds)</label>
            <input
              type="number"
              value={form.duration_secs}
              onChange={(e) => set("duration_secs", e.target.value)}
              className={fieldClass}
              placeholder="e.g., 300"
            />
          </div>

          <div>
            <label className={labelClass}>Assign To</label>
            <select
              value={form.assigned_to}
              onChange={(e) => set("assigned_to", e.target.value ? parseInt(e.target.value, 10) : "")}
              className={fieldClass}
            >
              <option value="">— Unassigned —</option>
              {staff.map((u) => (
                <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass}>Follow-up Date</label>
            <input
              type="datetime-local"
              value={form.followup_date}
              onChange={(e) => set("followup_date", e.target.value)}
              className={fieldClass}
            />
          </div>

          <div>
            <label className={labelClass}>Follow-up Status</label>
            <select value={form.follow_up_status} onChange={(e) => set("follow_up_status", e.target.value)} className={fieldClass}>
              <option value="">— None —</option>
              {FOLLOWUP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>Call Notes</label>
            <textarea
              rows={3}
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              className={fieldClass}
              placeholder="Call summary, action items, etc."
            />
          </div>

          <div>
            <label className={labelClass}>Follow-up Notes</label>
            <textarea
              rows={3}
              value={form.follow_up_notes}
              onChange={(e) => set("follow_up_notes", e.target.value)}
              className={fieldClass}
              placeholder="What needs to be done in follow-up"
            />
          </div>
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
