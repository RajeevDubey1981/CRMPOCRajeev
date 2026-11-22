import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import StatusBadge from "../../components/StatusBadge.jsx";
import { callsApi } from "../../api/calls.js";
import CallStatusEdit from "./CallStatusEdit.jsx";
import CallRecordingPlayer from "../../components/CallRecordingPlayer.jsx";
import { fmtIST } from "../../utils/time.js";

function fmt(s) { return s ? fmtIST(s, "String") : "—"; }

function fmtDuration(secs) {
  if (!secs) return "—";
  const mins = Math.floor(secs / 60);
  const secsRem = secs % 60;
  return `${mins}m ${secsRem}s`;
}

function Field({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>
        {value ?? <span className="text-slate-400">—</span>}
      </div>
    </div>
  );
}

export default function CallDetail() {
  const { id } = useParams();
  const [call, setCall] = useState(null);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(false);
  const [completing, setCompleting] = useState(false);

  async function load() {
    try {
      setCall(await callsApi.get(id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load");
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function markComplete() {
    setCompleting(true);
    try {
      await callsApi.completeFollowup(id);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to mark complete");
    } finally {
      setCompleting(false);
    }
  }

  if (err) return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  if (!call) return <div className="text-center text-slate-500">Loading…</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/calls" className="text-sm text-brand-600 hover:underline">← Back to calls</Link>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold text-slate-800">
            Call <span className="font-mono text-lg text-slate-500">{call.ref_no}</span>
            <StatusBadge value={call.status} />
          </h1>
        </div>
        <div className="flex gap-2">
          {call.followup_date && call.follow_up_status !== "Completed" && (
            <button
              onClick={markComplete}
              disabled={completing}
              className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {completing ? "Marking…" : "✓ Mark Follow-up Complete"}
            </button>
          )}
          <button
            onClick={() => setEditing(true)}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Edit
          </button>
        </div>
      </div>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Call Details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Call Type" value={call.call_type} />
          <Field label="Status" value={call.status} />
          <Field label="Purpose" value={call.purpose} />
          <Field label="Priority" value={call.priority} />
          <Field label="Customer Name" value={call.customer_name} />
          <Field label="Phone" value={call.phone} mono />
          <Field label="Email" value={call.customer_email} />
          <Field label="Assigned To" value={call.assigned_to_name} />
          {call.is_transferred && (
            <Field label="Transferred To" value={call.transferred_to_name} />
          )}
          <Field label="Duration" value={fmtDuration(call.duration_secs)} />
          <Field label="Call Date/Time" value={fmt(call.call_datetime)} />
          <Field label="Follow-up Date" value={fmt(call.followup_date)} />
          {call.followup_date && (
            <Field label="Follow-up Status" value={call.follow_up_status} />
          )}
          {call.complaint_id && (
            <Field label="Related Complaint" value={`#${call.complaint_id}`} />
          )}
          {call.notes && (
            <Field label="Call Notes" value={call.notes} full />
          )}
          {call.has_recording && (
            <div className="md:col-span-2">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Call Recording</p>
              <CallRecordingPlayer callId={call.id} />
            </div>
          )}
          {call.follow_up_notes && (
            <Field label="Follow-up Notes" value={call.follow_up_notes} full />
          )}
          <Field label="Created At" value={fmt(call.created_at)} />
          <Field label="Updated At" value={fmt(call.updated_at)} />
        </div>
      </section>

      {editing && (
        <CallStatusEdit
          call={call}
          onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); load(); }}
        />
      )}
    </div>
  );
}
