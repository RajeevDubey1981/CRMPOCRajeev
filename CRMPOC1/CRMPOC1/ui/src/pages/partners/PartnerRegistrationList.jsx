import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { partnerRegistrationsApi } from "../../api/partnerRegistrations.js";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";

const PARTNER_TYPE_COLORS = {
  "Gem Partner": "bg-blue-100 text-blue-800",
  Partner: "bg-blue-100 text-blue-800",
  Distributor: "bg-purple-100 text-purple-800",
  "Service Partner": "bg-teal-100 text-teal-800",
  Retailer: "bg-amber-100 text-amber-800",
};

const FORM_STATUS_COLORS = {
  "Invite Sent": "bg-slate-100 text-slate-700",
  "In Progress": "bg-amber-100 text-amber-800",
  Submitted: "bg-emerald-100 text-emerald-800",
};

const ONBOARDING_COLORS = {
  "Invite Sent": "bg-slate-100 text-slate-600",
  "In Progress": "bg-amber-50 text-amber-700",
  "Registration Submitted": "bg-slate-100 text-slate-700",
  "Documents Verification": "bg-blue-100 text-blue-800",
  "Admin Review": "bg-indigo-100 text-indigo-800",
  "Onboarding Approved": "bg-emerald-100 text-emerald-800",
  "Partner Active": "bg-green-100 text-green-800",
  Rejected: "bg-rose-100 text-rose-800",
  Cancelled: "bg-slate-200 text-slate-700",
};

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

function fmtDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN");
  } catch {
    return value;
  }
}

function TypeBadge({ value }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${PARTNER_TYPE_COLORS[value] || "bg-slate-100 text-slate-700"}`}>
      {value}
    </span>
  );
}

function FormStatusBadge({ value }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${FORM_STATUS_COLORS[value] || "bg-slate-100 text-slate-700"}`}>
      {value}
    </span>
  );
}

function OnboardingBadge({ value, onClick }) {
  const cls = ONBOARDING_COLORS[value] || "bg-slate-100 text-slate-700";
  if (!onClick) {
    return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>{value}</span>;
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium underline-offset-2 hover:underline ${cls}`}
    >
      {value}
    </button>
  );
}

function ProgressBar({ percent }) {
  return (
    <div className="min-w-[120px]">
      <div className="mb-1 text-xs text-slate-600">{percent}% filled</div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-sky-600" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function DetailField({ label, value }) {
  return (
    <div>
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="font-medium text-slate-800">{value || "—"}</div>
    </div>
  );
}

const EMPTY_INVITE = {
  partner_type: "Gem Partner",
  email: "",
  contact_person_name: "",
  mobile: "",
  name: "",
};

export default function PartnerRegistrationList() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState({ partner_types: [], onboarding_statuses: [], form_statuses: [] });
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({ partner_type: "", form_status: "", status: "", search: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionBusy, setActionBusy] = useState(null);
  const [pendingResend, setPendingResend] = useState(null);
  const [pendingCancel, setPendingCancel] = useState(null);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState(EMPTY_INVITE);
  const [inviteResult, setInviteResult] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    partner_type: filters.partner_type || undefined,
    form_status: filters.form_status || undefined,
    status: filters.status || undefined,
    search: filters.search || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await partnerRegistrationsApi.list(params));
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to load partner registrations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    partnerRegistrationsApi.meta().then(setMeta).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [params]);

  async function openDetail(row) {
    if (row.form_status === "Submitted") {
      navigate(`/admin/partner-registrations/${row.id}/review`);
      return;
    }
    setDetailLoading(true);
    setErr("");
    try {
      const full = await partnerRegistrationsApi.get(row.id);
      setDetail(full);
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to load partner details");
    } finally {
      setDetailLoading(false);
    }
  }

  async function sendInvite(event) {
    event.preventDefault();
    setSaving(true);
    setErr("");
    try {
      const result = await partnerRegistrationsApi.invite({
        partner_type: inviteForm.partner_type,
        email: inviteForm.email,
        contact_person_name: inviteForm.contact_person_name || null,
        mobile: inviteForm.mobile || null,
        name: inviteForm.name || null,
      });
      setInviteResult(result);
      setInviteForm(EMPTY_INVITE);
      await load();
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to send invitation");
    } finally {
      setSaving(false);
    }
  }

  async function resendEmail() {
    if (!pendingResend) return;
    const row = pendingResend;
    setActionBusy(`email-${row.id}`);
    setErr("");
    try {
      await partnerRegistrationsApi.resendEmail(row.id);
      setPendingResend(null);
      await load();
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to resend email");
    } finally {
      setActionBusy(null);
    }
  }

  async function cancelRegistration() {
    if (!pendingCancel) return;
    const row = pendingCancel;
    setActionBusy(`cancel-${row.id}`);
    setErr("");
    try {
      await partnerRegistrationsApi.update(row.id, { onboarding_status: "Cancelled" });
      setPendingCancel(null);
      await load();
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to cancel registration");
    } finally {
      setActionBusy(null);
    }
  }

  async function copyLink(url) {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // ignore clipboard errors
    }
  }

  function applyFilter(patch) {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Partner Registrations</h1>
          <p className="text-sm text-slate-600">
            Send onboarding invites to partners. Track how much of the form each partner has completed.
          </p>
        </div>
        <button
          type="button"
          onClick={() => { setInviteOpen(true); setInviteResult(null); }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Send onboarding invite
        </button>
      </div>

      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {err}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-5">
        <input
          type="search"
          placeholder="Search name, email, mobile..."
          value={filters.search}
          onChange={(e) => applyFilter({ search: e.target.value })}
          className={fieldClass}
        />
        <select
          value={filters.partner_type}
          onChange={(e) => applyFilter({ partner_type: e.target.value })}
          className={fieldClass}
        >
          <option value="">All partner types</option>
          {meta.partner_types.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <select
          value={filters.form_status}
          onChange={(e) => applyFilter({ form_status: e.target.value })}
          className={fieldClass}
        >
          <option value="">All form statuses</option>
          {(meta.form_statuses || []).map((status) => (
            <option key={status} value={status}>{status}</option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={(e) => applyFilter({ status: e.target.value })}
          className={fieldClass}
        >
          <option value="">All onboarding statuses</option>
          {meta.onboarding_statuses.map((status) => (
            <option key={status} value={status}>{status}</option>
          ))}
        </select>
        <div className="text-sm text-slate-600 self-center">
          {loading ? "Loading..." : `Showing ${data.items.length} of ${data.total} records`}
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Registration No</th>
              <th className="px-4 py-3">Partner Type</th>
              <th className="px-4 py-3">Name / Email</th>
              <th className="px-4 py-3">Contact</th>
              <th className="px-4 py-3">Form Progress</th>
              <th className="px-4 py-3">Form Status</th>
              <th className="px-4 py-3">Onboarding Status</th>
              <th className="px-4 py-3">Link</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-mono text-xs">{row.registration_no}</td>
                <td className="px-4 py-3"><TypeBadge value={row.partner_type} /></td>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{row.name || "—"}</div>
                  <div className="text-xs text-slate-500">{row.email}</div>
                </td>
                <td className="px-4 py-3">
                  <div>{row.contact_person_name || "—"}</div>
                  <div className="text-xs text-slate-500">{row.mobile || "—"}</div>
                </td>
                <td className="px-4 py-3">
                  <ProgressBar percent={row.completion_percent} />
                  <div className="mt-1 text-xs text-slate-500">Step {row.current_form_step} of 9</div>
                </td>
                <td className="px-4 py-3"><FormStatusBadge value={row.form_status} /></td>
                <td className="px-4 py-3">
                  <OnboardingBadge value={row.onboarding_status} onClick={() => openDetail(row)} />
                </td>
                <td className="px-4 py-3">
                  {row.registration_url && (
                    <button
                      type="button"
                      onClick={() => copyLink(row.registration_url)}
                      className="text-xs font-medium text-sky-700 underline"
                    >
                      Copy link
                    </button>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={Boolean(actionBusy) || row.onboarding_status === "Cancelled"}
                      onClick={() => setPendingResend(row)}
                      className="text-xs font-medium text-sky-700 underline disabled:text-slate-400 disabled:no-underline"
                    >
                      {actionBusy === `email-${row.id}` ? "Sending..." : "Resend email"}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(actionBusy)}
                      onClick={() => setPendingCancel(row)}
                      className="text-xs font-medium text-rose-700 underline disabled:text-slate-400 disabled:no-underline"
                    >
                      {actionBusy === `cancel-${row.id}` ? "Cancelling..." : "Cancel"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                  No partner registrations found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(value) => { setPerPage(value); setPage(1); }}
      />

      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Send partner onboarding invite"
        maxWidth="max-w-lg"
      >
        {inviteResult ? (
          <div className="space-y-4">
            <p className="text-sm text-emerald-700">
              Onboarding invite created for <strong>{inviteResult.email}</strong>. A custom onboarding link was sent to this email address.
            </p>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm break-all">
              {inviteResult.registration_url}
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => copyLink(inviteResult.registration_url)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm"
              >
                Copy link
              </button>
              <button
                type="button"
                onClick={() => setInviteOpen(false)}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form className="space-y-3" onSubmit={sendInvite}>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Partner type</label>
              <select
                value={inviteForm.partner_type}
                onChange={(e) => setInviteForm((f) => ({ ...f, partner_type: e.target.value }))}
                className={fieldClass}
              >
                {meta.partner_types.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Partner email *</label>
              <input
                type="email"
                required
                value={inviteForm.email}
                onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Firm name (optional)</label>
              <input
                value={inviteForm.name}
                onChange={(e) => setInviteForm((f) => ({ ...f, name: e.target.value }))}
                className={fieldClass}
              />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Contact person (optional)</label>
                <input
                  value={inviteForm.contact_person_name}
                  onChange={(e) => setInviteForm((f) => ({ ...f, contact_person_name: e.target.value }))}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Mobile (optional)</label>
                <input
                  value={inviteForm.mobile}
                  onChange={(e) => setInviteForm((f) => ({ ...f, mobile: e.target.value }))}
                  className={fieldClass}
                />
              </div>
            </div>
            <p className="text-xs text-slate-500">
              On submit, a custom onboarding link will be generated and sent to the partner by email. They can use the same link to complete the form in steps.
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setInviteOpen(false)} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
                Cancel
              </button>
              <button type="submit" disabled={saving} className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50">
                Send onboarding invite
              </button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(detail) || detailLoading}
        onClose={() => { if (!detailLoading) setDetail(null); }}
        title={detail ? `Registration ${detail.registration_no}` : "Partner details"}
        maxWidth="max-w-5xl"
      >
        {detailLoading && !detail ? (
          <p className="text-sm text-slate-600">Loading partner details...</p>
        ) : detail ? (
          <div className="space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Partner registration</div>
                  <div className="mt-1 text-lg font-semibold text-slate-900">{detail.name || detail.email}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <TypeBadge value={detail.partner_type} />
                    <FormStatusBadge value={detail.form_status} />
                    <OnboardingBadge value={detail.onboarding_status} />
                  </div>
                </div>
                <div className="text-right text-sm text-slate-600">
                  <div>Invited: {fmtDateTime(detail.invited_at)}</div>
                  <div>Started: {fmtDateTime(detail.form_started_at)}</div>
                  <div>Submitted: {fmtDateTime(detail.form_submitted_at)}</div>
                </div>
              </div>

              <div className="mt-4">
                <ProgressBar percent={detail.completion_percent} />
              </div>

              {detail.form_status !== "Submitted" ? (
                <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Partner has completed {detail.completion_percent}% of the form (step {detail.current_form_step} of 9).
                  Share the registration link if they have not started yet.
                </div>
              ) : null}

              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3 text-sm">
                <DetailField label="Contact person" value={`${detail.contact_person_name || "—"}${detail.contact_designation ? ` (${detail.contact_designation})` : ""}`} />
                <DetailField label="Mobile" value={detail.mobile} />
                <DetailField label="Email" value={detail.email} />
                <DetailField label="GST / PAN" value={`${detail.gst_no || "—"} / ${detail.pan_no || "—"}`} />
                <DetailField label="Bank" value={`${detail.bank_name || "—"} (${detail.ifsc_code || "—"})`} />
                <DetailField label="Operating states" value={detail.operating_states} />
                <div className="md:col-span-3">
                  <DetailField label="Address" value={detail.firm_address} />
                </div>
              </div>

            </div>

            {detail.registration_url && (
              <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
                <span className="flex-1 break-all text-slate-700">{detail.registration_url}</span>
                <button type="button" onClick={() => copyLink(detail.registration_url)} className="shrink-0 text-sky-700 underline">
                  Copy
                </button>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setDetail(null)} className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700">
                Close
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(pendingResend)}
        onClose={() => { if (!actionBusy) setPendingResend(null); }}
        title="Resend email?"
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Do you still want to resend the email to <strong>{pendingResend?.email}</strong>?
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              disabled={Boolean(actionBusy)}
              onClick={() => setPendingResend(null)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={actionBusy === `email-${pendingResend?.id}`}
              onClick={resendEmail}
              className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {actionBusy === `email-${pendingResend?.id}` ? "Sending..." : "Confirm resend"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={Boolean(pendingCancel)}
        onClose={() => { if (!actionBusy) setPendingCancel(null); }}
        title="Cancel registration?"
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Cancel registration <strong>{pendingCancel?.registration_no}</strong>? The partner link will stop working.
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              disabled={Boolean(actionBusy)}
              onClick={() => setPendingCancel(null)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm"
            >
              Keep registration
            </button>
            <button
              type="button"
              disabled={actionBusy === `cancel-${pendingCancel?.id}`}
              onClick={cancelRegistration}
              className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {actionBusy === `cancel-${pendingCancel?.id}` ? "Cancelling..." : "Confirm cancellation"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
