import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../../api/client.js";
import { partnerRegistrationsApi } from "../../api/partnerRegistrations.js";
import PartnerOnboardingStepper from "../../components/partners/PartnerOnboardingStepper.jsx";
import { PARTNER_DOCUMENTS } from "./partnerFormConstants.js";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

function fmtDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN");
  } catch {
    return value;
  }
}

function toDownloadUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const base = (api.defaults.baseURL || "").replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

function DetailField({ label, value, highlight }) {
  return (
    <div>
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className={`font-medium ${highlight ? "text-amber-700" : "text-slate-800"}`}>{value || "—"}</div>
    </div>
  );
}

function DocumentLink({ label, path }) {
  if (!path) return null;
  return (
    <a
      href={toDownloadUrl(path)}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-sky-700 hover:bg-sky-50"
    >
      {label}
    </a>
  );
}

// Fields the vendor submitted vs. what the GST registry says for that GSTIN.
// Shown side-by-side so the admin can spot mismatches before approving.
const COMPARISON_ROWS = [
  { label: "Firm / Trade Name", vendorField: "name", gstField: (g) => g.trade_name || g.legal_name },
  { label: "PAN", vendorField: "pan_no", gstField: (g) => g.pan },
  { label: "Address", vendorField: "firm_address", gstField: (g) => g.address },
  { label: "City", vendorField: "city", gstField: (g) => g.city },
  { label: "District", vendorField: "district", gstField: (g) => g.district },
  { label: "State", vendorField: "state", gstField: (g) => g.state },
  { label: "Business Type", vendorField: "business_type", gstField: (g) => g.business_type_mapped },
];

function normalize(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

export default function PartnerRegistrationReview() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [gstBusy, setGstBusy] = useState(false);
  const [gstResult, setGstResult] = useState(null);
  const [gstError, setGstError] = useState("");

  const [adminRemark, setAdminRemark] = useState("");
  const [saving, setSaving] = useState(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [agreement, setAgreement] = useState(null);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const full = await partnerRegistrationsApi.get(id);
      setDetail(full);
      setAdminRemark(full.admin_remark || "");
      // Present only once the registration has been approved.
      setAgreement(await partnerRegistrationsApi.agreement(id).catch(() => null));
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to load partner details");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function validateGst() {
    setGstBusy(true);
    setGstError("");
    setGstResult(null);
    try {
      const result = await partnerRegistrationsApi.validateGst(id);
      setGstResult(result);
    } catch (error) {
      setGstError(error.response?.data?.detail || "GST validation failed");
    } finally {
      setGstBusy(false);
    }
  }

  async function approve() {
    setSaving("approve");
    setErr("");
    try {
      await partnerRegistrationsApi.update(id, {
        onboarding_status: "Onboarding Approved",
        admin_remark: adminRemark || null,
      });
      // Stay on the page so the admin can see the agreement signing status
      // that approval just triggered.
      await load();
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to approve registration");
    } finally {
      setSaving(null);
    }
  }

  async function reject() {
    setSaving("reject");
    setErr("");
    try {
      await partnerRegistrationsApi.reject(id, { admin_remark: adminRemark || null });
      setConfirmReject(false);
      navigate("/admin/partner-registrations");
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to reject registration");
    } finally {
      setSaving(null);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-600">Loading partner details...</p>;
  }

  if (err && !detail) {
    return (
      <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
    );
  }

  if (!detail) return null;

  const isSubmitted = detail.form_status === "Submitted";
  // Once approved the decision is made; the flow now waits on the partner's
  // signature rather than on another admin action.
  const canDecide = isSubmitted && !["Onboarding Approved", "Partner Active"].includes(detail.onboarding_status);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <button
            type="button"
            onClick={() => navigate("/admin/partner-registrations")}
            className="text-xs font-medium text-sky-700 underline"
          >
            &larr; Back to partner registrations
          </button>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">
            Review — {detail.registration_no}
          </h1>
        </div>
      </div>

      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">{detail.name || detail.email}</div>
            <div className="mt-1 text-sm text-slate-600">{detail.partner_type} · {detail.form_status} · {detail.onboarding_status}</div>
          </div>
          <div className="text-right text-sm text-slate-600">
            <div>Submitted: {fmtDateTime(detail.form_submitted_at)}</div>
            <div>Status updated: {fmtDateTime(detail.status_updated_at)}</div>
          </div>
        </div>

        {!isSubmitted && (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            This registration is not in a submitted state (currently "{detail.form_status}"). It must be submitted
            by the vendor before it can be approved or rejected.
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3 text-sm">
          <DetailField label="Contact person" value={`${detail.contact_person_name || "—"}${detail.contact_designation ? ` (${detail.contact_designation})` : ""}`} />
          <DetailField label="Mobile" value={detail.mobile} />
          <DetailField label="Email" value={detail.email} />
          <DetailField label="GSTIN" value={detail.gst_no} />
          <DetailField label="Aadhaar" value={detail.aadhaar_no} />
          <DetailField label="Bank" value={`${detail.bank_name || "—"} (${detail.ifsc_code || "—"})`} />
          <DetailField label="Operating states" value={detail.operating_states} />
          <DetailField label="Product categories" value={detail.product_categories} />
          <div className="md:col-span-3">
            <DetailField label="Address" value={detail.firm_address} />
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Submitted documents</div>
          <div className="flex flex-wrap gap-2">
            {PARTNER_DOCUMENTS.map((doc) => (
              <DocumentLink key={doc.key} label={doc.label} path={detail[`${doc.key}_path`]} />
            ))}
          </div>
        </div>

        <PartnerOnboardingStepper steps={detail.onboarding_steps} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">GST verification</div>
            <div className="text-xs text-slate-500">Looks up the GSTIN the vendor submitted ({detail.gst_no || "none"}) against the government registry.</div>
          </div>
          <button
            type="button"
            disabled={gstBusy || !detail.gst_no}
            onClick={validateGst}
            className="shrink-0 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {gstBusy ? "Checking..." : "Validate GSTIN"}
          </button>
        </div>

        {gstError && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{gstError}</div>
        )}

        {gstResult && !gstResult.valid && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {gstResult.error || "GSTIN could not be verified"}
          </div>
        )}

        {gstResult && gstResult.valid && (
          <div className="mt-4">
            <div className="mb-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              GST verified — {gstResult.trade_name || gstResult.legal_name}. Status: {gstResult.status} · Dealer: {gstResult.dealer_type || "—"}
            </div>
            <div className="overflow-hidden rounded-md border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Field</th>
                    <th className="px-3 py-2">Vendor submitted</th>
                    <th className="px-3 py-2">GST registry</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {COMPARISON_ROWS.map((row) => {
                    const vendorValue = detail[row.vendorField];
                    const gstValue = row.gstField(gstResult);
                    const mismatch = normalize(vendorValue) !== normalize(gstValue) && (vendorValue || gstValue);
                    return (
                      <tr key={row.label} className={mismatch ? "bg-amber-50" : undefined}>
                        <td className="px-3 py-2 font-medium text-slate-700">{row.label}</td>
                        <td className="px-3 py-2 text-slate-800">{vendorValue || "—"}</td>
                        <td className={`px-3 py-2 ${mismatch ? "font-semibold text-amber-800" : "text-slate-800"}`}>{gstValue || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {agreement && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-sm font-semibold text-slate-900">Service agreement</div>
          {agreement.is_signed ? (
            <div className="mt-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              Signed on {fmtDateTime(agreement.signed_at)} by {agreement.email}
              {agreement.ip_address ? ` (IP ${agreement.ip_address})` : ""}. Partner account and vendor code have been
              issued.
            </div>
          ) : (
            <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Awaiting signature. A signing link was emailed to {agreement.email}. The partner account and vendor code
              are created only once they sign.
            </div>
          )}
          <div className="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
            <DetailField label="Agreement No" value={agreement.agreement_no} />
            <DetailField label="Version" value={agreement.agreement_version} />
            <DetailField label="Issued" value={fmtDateTime(agreement.created_at)} />
          </div>
          {!agreement.is_signed && (
            <div className="mt-3 flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
              <span className="flex-1 break-all text-slate-700">{agreement.agreement_url}</span>
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(agreement.agreement_url).catch(() => {})}
                className="shrink-0 text-sky-700 underline"
              >
                Copy
              </button>
            </div>
          )}
        </div>
      )}

      {canDecide && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <label className="mb-1 block text-sm font-medium text-slate-700">Admin remark</label>
          <textarea
            rows={3}
            value={adminRemark}
            onChange={(e) => setAdminRemark(e.target.value)}
            className={fieldClass}
            placeholder="Optional note — shown to the vendor if you reject this registration"
          />
          <p className="mt-2 text-xs text-slate-500">
            Approving emails the partner a link to review and digitally sign the service agreement. Their account and
            vendor code are issued only after they sign.
          </p>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              disabled={Boolean(saving)}
              onClick={() => setConfirmReject(true)}
              className="rounded-md border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 disabled:opacity-50"
            >
              {saving === "reject" ? "Rejecting..." : "Reject"}
            </button>
            <button
              type="button"
              disabled={Boolean(saving)}
              onClick={approve}
              className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving === "approve" ? "Approving..." : "Approve"}
            </button>
          </div>
        </div>
      )}

      {confirmReject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-slate-900">Reject this registration?</h2>
            <p className="mt-2 text-sm text-slate-600">
              The vendor's form will reopen from step 1 so they can review and resubmit. They will receive an
              email with a link to restart the process{adminRemark ? " and your remark" : ""}.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                disabled={Boolean(saving)}
                onClick={() => setConfirmReject(false)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={Boolean(saving)}
                onClick={reject}
                className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {saving === "reject" ? "Rejecting..." : "Confirm reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
