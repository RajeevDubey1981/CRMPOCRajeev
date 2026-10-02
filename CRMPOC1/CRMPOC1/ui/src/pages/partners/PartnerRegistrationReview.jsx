import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../../api/client.js";
import { partnerRegistrationsApi } from "../../api/partnerRegistrations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import PartnerOnboardingStepper from "../../components/partners/PartnerOnboardingStepper.jsx";
import { PARTNER_DOCUMENTS, buildShopPhotoDocuments } from "./partnerFormConstants.js";

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

function EditableReviewField({ label, fieldKey, value, onChange }) {
  if (fieldKey === "declaration_accepted") {
    return (
      <label className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(fieldKey, event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-sky-700"
        />
        {label}
      </label>
    );
  }

  if (SELECT_OPTIONS[fieldKey]) {
    return (
      <label className="block">
        <span className="text-xs uppercase text-slate-500">{label}</span>
        <select
          value={value || ""}
          onChange={(event) => onChange(fieldKey, event.target.value)}
          className={`${fieldClass} mt-1 bg-white`}
        >
          {SELECT_OPTIONS[fieldKey].map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </label>
    );
  }

  if (TEXTAREA_FIELDS.has(fieldKey)) {
    return (
      <label className="block md:col-span-2">
        <span className="text-xs uppercase text-slate-500">{label}</span>
        <textarea
          rows={3}
          value={value || ""}
          onChange={(event) => onChange(fieldKey, event.target.value)}
          className={`${fieldClass} mt-1`}
        />
      </label>
    );
  }

  return (
    <label className="block">
      <span className="text-xs uppercase text-slate-500">{label}</span>
      <input
        type={inputTypeForField(fieldKey)}
        value={value || ""}
        step={fieldKey === "annual_turnover" ? "0.01" : undefined}
        onChange={(event) => onChange(fieldKey, event.target.value)}
        className={`${fieldClass} mt-1`}
      />
    </label>
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

const REVIEW_STEPS = [
  { title: "Partner Category", fields: [["Partner Type", "partner_type"], ["Business Type", "business_type"]] },
  { title: "Firm Details", fields: [["Firm / Company Name", "name"], ["Date of Establishment", "year_of_establishment"], ["Annual Turnover", "annual_turnover"], ["GeM Seller ID", "gem_seller_id"]] },
  { title: "Contact Person", fields: [["Contact Person", "contact_person_name"], ["Designation", "contact_designation"], ["Mobile", "mobile"], ["Alternate Mobile", "alternate_mobile"], ["Email", "email"], ["Website", "website"]] },
  { title: "Address", fields: [["Complete Address", "firm_address"], ["City", "city"], ["District", "district"], ["State", "state"], ["Pincode", "pincode"]] },
  { title: "Tax Registration", fields: [["GSTIN", "gst_no"], ["PAN", "pan_no"], ["Aadhaar", "aadhaar_no"], ["Udyam / MSME No.", "udyam_no"], ["CIN", "cin_no"]] },
  { title: "Bank Details", fields: [["Bank Name", "bank_name"], ["Branch", "bank_branch"], ["Account Holder", "account_holder_name"], ["Account Number", "account_number"], ["IFSC", "ifsc_code"]] },
  { title: "Operations", fields: [["Operating States", "operating_states"], ["Product Categories", "product_categories"], ["Remarks", "remarks"]] },
  { title: "Documents", fields: [] },
  { title: "Declaration", fields: [["Declaration Accepted", "declaration_accepted"]] },
];

const PARTNER_TYPE_OPTIONS = ["Gem Partner", "CSD Dealer", "Distributor", "Service Partner", "Retailer", "Partner"];
const BUSINESS_TYPE_OPTIONS = ["Proprietorship", "Partnership", "LLP", "Private Limited", "Public Limited", "Trust / Society", "Other"];
const SELECT_OPTIONS = {
  partner_type: PARTNER_TYPE_OPTIONS,
  business_type: BUSINESS_TYPE_OPTIONS,
};
const TEXTAREA_FIELDS = new Set(["firm_address", "operating_states", "product_categories", "remarks"]);
const NUMBER_FIELDS = new Set(["annual_turnover"]);

function gemSellerIdRequired(partnerType) {
  return (partnerType || "").trim() === "Gem Partner";
}

function reviewStepFields(step, detail) {
  if (step.title !== "Firm Details" || gemSellerIdRequired(detail?.partner_type)) {
    return step.fields;
  }
  return step.fields.filter(([, key]) => key !== "gem_seller_id");
}

function normalize(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function inputTypeForField(key) {
  if (key === "email") return "email";
  if (key === "website") return "url";
  if (key === "year_of_establishment") return "date";
  if (key.includes("mobile") || key === "pincode" || key === "account_number" || key === "aadhaar_no") return "tel";
  if (NUMBER_FIELDS.has(key)) return "number";
  return "text";
}

function toDraftValue(value) {
  if (value === null || value === undefined) return "";
  return value;
}

export default function PartnerRegistrationReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const permission = (Array.isArray(user?.permissions) ? user.permissions : [])
    .find((item) => item.module === "partner_registrations");
  const isSystemAdmin = ["admin", "incool"].includes((user?.role || "").trim().toLowerCase());
  const canEditPartnerRegistration = isSystemAdmin || Boolean(permission?.can_edit);

  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [gstBusy, setGstBusy] = useState(false);
  const [gstResult, setGstResult] = useState(null);
  const [gstError, setGstError] = useState("");

  const [adminRemark, setAdminRemark] = useState("");
  const [saving, setSaving] = useState(null);
  const [downloadingAgreement, setDownloadingAgreement] = useState(false);
  const [confirmReject, setConfirmReject] = useState(false);
  const [agreement, setAgreement] = useState(null);
  const [reviewStep, setReviewStep] = useState(0);
  const [editingReview, setEditingReview] = useState(false);
  const [reviewDraft, setReviewDraft] = useState({});
  const [reviewSaving, setReviewSaving] = useState(false);

  const shopPhotoDocs = useMemo(() => {
    if (!detail) return [];
    const count = detail.partner_type === "CSD Dealer" ? 5 : 1;
    return buildShopPhotoDocuments(count);
  }, [detail]);

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

  useEffect(() => {
    setEditingReview(false);
    setReviewDraft({});
  }, [reviewStep]);

  function startReviewEdit() {
    const draft = {};
    reviewStepFields(REVIEW_STEPS[reviewStep], detail).forEach(([, key]) => {
      draft[key] = toDraftValue(detail[key]);
    });
    setReviewDraft(draft);
    setEditingReview(true);
  }

  function updateReviewDraft(key, value) {
    setReviewDraft((current) => ({ ...current, [key]: value }));
  }

  function buildReviewPayload() {
    return reviewStepFields(REVIEW_STEPS[reviewStep], detail).reduce((payload, [, key]) => {
      const value = reviewDraft[key];
      if (key === "declaration_accepted") {
        payload[key] = Boolean(value);
      } else if (key === "email" || key === "partner_type") {
        payload[key] = String(value || "").trim();
      } else if (NUMBER_FIELDS.has(key)) {
        payload[key] = value === "" || value === null || value === undefined ? null : Number(value);
      } else {
        payload[key] = String(value || "").trim() || null;
      }
      return payload;
    }, {});
  }

  async function saveReviewStep() {
    setReviewSaving(true);
    setErr("");
    try {
      await partnerRegistrationsApi.update(id, buildReviewPayload());
      await load();
      setEditingReview(false);
      setReviewDraft({});
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to save registration changes");
    } finally {
      setReviewSaving(false);
    }
  }

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
      navigate("/partner-registrations");
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to reject registration");
    } finally {
      setSaving(null);
    }
  }

  async function downloadAgreement() {
    setDownloadingAgreement(true);
    setErr("");
    try {
      await partnerRegistrationsApi.downloadAgreement(id);
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to download agreement");
    } finally {
      setDownloadingAgreement(false);
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
            onClick={() => navigate("/partner-registrations")}
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
          {shopPhotoDocs.length > 0 ? (
            <div className="mt-3">
              <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">
                Shop photographs ({detail.partner_type === "CSD Dealer" ? "5 required for CSD Dealer" : "1 required"})
              </div>
              <div className="flex flex-wrap gap-2">
                {shopPhotoDocs.map((doc) => (
                  <DocumentLink key={doc.key} label={doc.label} path={detail[`${doc.key}_path`]} />
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <PartnerOnboardingStepper steps={detail.onboarding_steps} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">Form review</div>
            <div className="text-xs text-slate-500">Review the submitted information in the same order as the partner onboarding form.</div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <div className="text-sm font-medium text-slate-500">Step {reviewStep + 1} of {REVIEW_STEPS.length}</div>
            {canEditPartnerRegistration && reviewStep !== 7 && (
              editingReview ? (
                <>
                  <button
                    type="button"
                    disabled={reviewSaving}
                    onClick={() => {
                      setEditingReview(false);
                      setReviewDraft({});
                    }}
                    className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={reviewSaving}
                    onClick={saveReviewStep}
                    className="rounded-md bg-sky-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {reviewSaving ? "Saving..." : "Save changes"}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={startReviewEdit}
                  className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-medium text-sky-700 hover:bg-sky-100"
                >
                  Edit this step
                </button>
              )
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {REVIEW_STEPS.map((step, index) => (
            <button
              key={step.title}
              type="button"
              onClick={() => setReviewStep(index)}
              className={`rounded-md px-3 py-2 text-xs font-medium ${reviewStep === index ? "bg-sky-700 text-white" : "border border-slate-200 text-slate-600 hover:bg-slate-50"}`}
            >
              {index + 1}. {step.title}
            </button>
          ))}
        </div>

        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4">
          <h2 className="text-base font-semibold text-slate-900">{REVIEW_STEPS[reviewStep].title}</h2>
          {reviewStep === 7 ? (
            <div className="mt-3 space-y-3">
              <div>
                <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">Documents</div>
                <div className="flex flex-wrap gap-2">
                  {PARTNER_DOCUMENTS.map((doc) => (
                    <DocumentLink key={doc.key} label={doc.label} path={detail[`${doc.key}_path`]} />
                  ))}
                  {!PARTNER_DOCUMENTS.some((doc) => detail[`${doc.key}_path`]) && (
                    <span className="text-sm text-slate-500">No documents uploaded.</span>
                  )}
                </div>
              </div>
              <div>
                <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">
                  Shop photographs ({detail.partner_type === "CSD Dealer" ? "5 required for CSD Dealer" : "1 required"})
                </div>
                <div className="flex flex-wrap gap-2">
                  {shopPhotoDocs.map((doc) => (
                    <DocumentLink key={doc.key} label={doc.label} path={detail[`${doc.key}_path`]} />
                  ))}
                </div>
              </div>
            </div>
          ) : editingReview ? (
            <div className="mt-3 grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
              {reviewStepFields(REVIEW_STEPS[reviewStep], detail).map(([label, key]) => (
                <EditableReviewField
                  key={key}
                  label={label}
                  fieldKey={key}
                  value={reviewDraft[key]}
                  onChange={updateReviewDraft}
                />
              ))}
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
              {reviewStepFields(REVIEW_STEPS[reviewStep], detail).map(([label, key]) => (
                <DetailField
                  key={key}
                  label={label}
                  value={key === "declaration_accepted" ? (detail[key] ? "Accepted" : "Not accepted") : detail[key]}
                />
              ))}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-between gap-2">
          <button
            type="button"
            disabled={reviewStep === 0}
            onClick={() => setReviewStep((current) => current - 1)}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
          >
            Previous step
          </button>
          <button
            type="button"
            disabled={reviewStep === REVIEW_STEPS.length - 1}
            onClick={() => setReviewStep((current) => current + 1)}
            className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Next step
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">GST verification</div>
            <div className="text-xs text-slate-500">Looks up the GSTIN the vendor submitted ({detail.gst_no || "none"}) against the government registry.</div>
          </div>
          <button
            type="button"
            disabled={gstBusy || !detail.gst_no || !canEditPartnerRegistration}
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
              {agreement.signed_method ? ` Signed via ${agreement.signed_method}` : ""}
              {agreement.signed_destination ? ` to ${agreement.signed_destination}` : ""}.
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
            <DetailField label="Signed Method" value={agreement.signed_method} />
            <DetailField label="Verified Contact" value={agreement.signed_destination} />
          </div>
          <div className="mt-3">
            <button
              type="button"
              onClick={downloadAgreement}
              disabled={downloadingAgreement}
              className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {downloadingAgreement ? "Preparing..." : "Download full agreement"}
            </button>
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

      {canEditPartnerRegistration && canDecide && (
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
