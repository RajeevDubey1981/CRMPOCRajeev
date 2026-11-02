import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import { claimsApi } from "../../api/claims.js";

const STATUSES = ["Processing", "Completed", "Rejected"];

const STATUS_COLORS = {
  Processing: "bg-blue-100 text-blue-800",
  Completed: "bg-green-100 text-green-800",
  Rejected: "bg-red-100 text-red-800",
};

function StatusBadge({ value }) {
  const cls = STATUS_COLORS[value] || "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {value}
    </span>
  );
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

function fmt(s) {
  if (!s) return null;
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

export default function ClaimDetail() {
  const { id } = useParams();
  const [claim, setClaim] = useState(null);
  const [err, setErr] = useState("");

  // Status modal
  const [statusOpen, setStatusOpen] = useState(false);
  const [statusForm, setStatusForm] = useState({ status: "Processing", admin_remark: "" });
  const [statusSaving, setStatusSaving] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editSaving, setEditSaving] = useState(false);
  const [editErr, setEditErr] = useState("");

  async function load() {
    try {
      const c = await claimsApi.get(id);
      setClaim(c);
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load claim");
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  function openStatus() {
    if (!claim) return;
    setStatusForm({ status: claim.status, admin_remark: claim.admin_remark || "" });
    setStatusOpen(true);
  }

  async function submitStatus() {
    setStatusSaving(true);
    try {
      const updated = await claimsApi.updateStatus(id, {
        status: statusForm.status,
        admin_remark: statusForm.admin_remark || null,
      });
      setClaim(updated);
      setStatusOpen(false);
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to update status");
    } finally {
      setStatusSaving(false);
    }
  }

  function openEdit() {
    if (!claim) return;
    setEditForm({
      order_no: claim.order_no || "",
      serial_number: claim.serial_number || "",
      customer_name: claim.customer_name || "",
      customer_contact: claim.customer_contact || "",
      customer_email: claim.customer_email || "",
      notes: claim.notes || "",
      bank_name: claim.bank_name || "",
      account_holder_name: claim.account_holder_name || "",
      account_number: claim.account_number || "",
      ifsc_code: claim.ifsc_code || "",
    });
    setEditErr("");
    setEditOpen(true);
  }

  async function submitEdit(e) {
    e.preventDefault();
    setEditErr("");
    setEditSaving(true);
    try {
      const body = {
        order_no: editForm.order_no || null,
        serial_number: editForm.serial_number || null,
        customer_name: editForm.customer_name || null,
        customer_contact: editForm.customer_contact || null,
        customer_email: editForm.customer_email || null,
        notes: editForm.notes || null,
        bank_name: editForm.bank_name || null,
        account_holder_name: editForm.account_holder_name || null,
        account_number: editForm.account_number || null,
        ifsc_code: editForm.ifsc_code || null,
      };
      const updated = await claimsApi.update(id, body);
      setClaim(updated);
      setEditOpen(false);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setEditErr(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || "Failed to save"
      );
    } finally {
      setEditSaving(false);
    }
  }

  if (err) {
    return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  }
  if (!claim) {
    return <div className="text-center text-slate-500">Loading…</div>;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/claims" className="text-sm text-brand-600 hover:underline">
            ← Back to Claims
          </Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-3 text-2xl font-bold text-slate-900">
            <span className="font-mono text-lg text-slate-600">{claim.claim_id}</span>
            <StatusBadge value={claim.status} />
          </h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={openStatus}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Update Status
          </button>
          <button
            onClick={openEdit}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Edit Details
          </button>
        </div>
      </div>

      {/* Claim Details section */}
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Claim Details
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Order No" value={claim.order_no} mono />
          <Field label="Serial No" value={claim.serial_number} mono />
          <Field label="Customer Name" value={claim.customer_name} />
          <Field label="Contact" value={claim.customer_contact} />
          <Field label="Email" value={claim.customer_email} />
          <Field label="Submitted At" value={fmt(claim.submitted_at)} />
          <Field label="Processed By" value={claim.processed_by_name} />
          <Field label="Last Updated" value={fmt(claim.updated_at)} />
          <Field
            label="Routed To"
            value={
              claim.routed_to
                ? `${claim.routed_to[0].toUpperCase()}${claim.routed_to.slice(1)}${
                    claim.manufacturer_name || claim.courier_name || claim.insurance_name
                      ? ` — ${claim.manufacturer_name || claim.courier_name || claim.insurance_name}`
                      : ""
                  }`
                : null
            }
          />
          <Field label="Issue Description" value={claim.notes} full />
        </div>
      </section>

      {/* Bank & Settlement section */}
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Bank &amp; Settlement
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Bank Name" value={claim.bank_name} />
          <Field label="Account Holder Name" value={claim.account_holder_name} />
          <Field label="Account Number" value={claim.account_number} mono />
          <Field label="IFSC Code" value={claim.ifsc_code} mono />
          <Field label="Admin Remark" value={claim.admin_remark} full />
        </div>
      </section>

      {/* Status update modal */}
      <Modal open={statusOpen} onClose={() => setStatusOpen(false)} title="Update Claim Status">
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Status</label>
            <select
              value={statusForm.status}
              onChange={(e) => setStatusForm((f) => ({ ...f, status: e.target.value }))}
              className={fieldClass}
            >
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Admin Remark</label>
            <textarea
              value={statusForm.admin_remark}
              onChange={(e) => setStatusForm((f) => ({ ...f, admin_remark: e.target.value }))}
              rows={3}
              placeholder="Optional remark for this status change"
              className={fieldClass}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setStatusOpen(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={submitStatus}
              disabled={statusSaving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {statusSaving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Edit details modal */}
      <Modal open={editOpen} onClose={() => setEditOpen(false)} title="Edit Claim Details">
        <form onSubmit={submitEdit} className="space-y-4">
          {editErr && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{editErr}</div>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className={labelClass}>Order No</label>
              <input
                type="text"
                value={editForm.order_no || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, order_no: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Serial No</label>
              <input
                type="text"
                value={editForm.serial_number || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, serial_number: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Name</label>
              <input
                type="text"
                value={editForm.customer_name || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, customer_name: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Contact</label>
              <input
                type="text"
                value={editForm.customer_contact || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, customer_contact: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass}>Email</label>
              <input
                type="email"
                value={editForm.customer_email || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, customer_email: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass}>Issue Description</label>
              <textarea
                rows={3}
                value={editForm.notes || ""}
                onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                className={fieldClass}
              />
            </div>
          </div>

          <div className="border-t border-slate-200 pt-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Bank &amp; Settlement
            </p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <label className={labelClass}>Bank Name</label>
                <input
                  type="text"
                  value={editForm.bank_name || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, bank_name: e.target.value }))}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>Account Holder Name</label>
                <input
                  type="text"
                  value={editForm.account_holder_name || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, account_holder_name: e.target.value }))}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>Account Number</label>
                <input
                  type="text"
                  value={editForm.account_number || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, account_number: e.target.value }))}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>IFSC Code</label>
                <input
                  type="text"
                  value={editForm.ifsc_code || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, ifsc_code: e.target.value }))}
                  placeholder="e.g. SBIN0001234"
                  className={fieldClass}
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditOpen(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={editSaving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {editSaving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
