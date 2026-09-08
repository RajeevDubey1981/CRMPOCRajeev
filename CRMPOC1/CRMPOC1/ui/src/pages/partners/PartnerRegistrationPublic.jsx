import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { partnerRegistrationPublicApi } from "../../api/partnerRegistrationPublic.js";
import {
  EMPTY_PARTNER_FORM,
  INDIAN_STATES,
  PARTNER_DOCUMENTS,
} from "./partnerFormConstants.js";

const fieldClass =
  "w-full rounded-xl border border-slate-300 px-3 py-3 text-base sm:text-sm focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function toFileUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const configured = (import.meta.env.VITE_API_BASE_URL || "").trim();
  const base = configured || (import.meta.env.DEV ? "http://localhost:8010" : window.location.origin);
  return `${base.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

function Field({ label, required, children }) {
  return (
    <div>
      <label className={labelClass}>
        {label}
        {required ? <span className="text-rose-600"> *</span> : null}
      </label>
      {children}
    </div>
  );
}

function mapApiToForm(data) {
  if (!data) return { ...EMPTY_PARTNER_FORM };
  return {
    ...EMPTY_PARTNER_FORM,
    partner_type: data.partner_type || "Partner",
    business_type: data.business_type || "Proprietorship",
    name: data.name || "",
    mobile: data.mobile || "",
    alternate_mobile: data.alternate_mobile || "",
    email: data.email || "",
    website: data.website || "",
    contact_person_name: data.contact_person_name || "",
    contact_designation: data.contact_designation || "",
    firm_address: data.firm_address || "",
    city: data.city || "",
    district: data.district || "",
    state: data.state || "",
    pincode: data.pincode || "",
    gst_no: data.gst_no || "",
    pan_no: data.pan_no || "",
    udyam_no: data.udyam_no || "",
    cin_no: data.cin_no || "",
    aadhaar_no: data.aadhaar_no || "",
    gem_seller_id: data.gem_seller_id || "",
    year_of_establishment: data.year_of_establishment ?? "",
    annual_turnover: data.annual_turnover ?? "",
    operating_states: data.operating_states || "",
    product_categories: data.product_categories || "",
    bank_name: data.bank_name || "",
    bank_branch: data.bank_branch || "",
    account_holder_name: data.account_holder_name || "",
    account_number: data.account_number || "",
    ifsc_code: data.ifsc_code || "",
    remarks: data.remarks || "",
    declaration_accepted: Boolean(data.declaration_accepted),
  };
}

function stepPayload(step, form) {
  const numeric = {
    year_of_establishment: form.year_of_establishment ? Number(form.year_of_establishment) : null,
    annual_turnover: form.annual_turnover ? Number(form.annual_turnover) : null,
  };
  switch (step) {
    case 1:
      return { partner_type: form.partner_type, business_type: form.business_type };
    case 2:
      return {
        name: form.name,
        year_of_establishment: numeric.year_of_establishment,
        annual_turnover: numeric.annual_turnover,
        gem_seller_id: form.gem_seller_id || null,
      };
    case 3:
      return {
        contact_person_name: form.contact_person_name,
        contact_designation: form.contact_designation,
        mobile: form.mobile,
        alternate_mobile: form.alternate_mobile || null,
        email: form.email,
        website: form.website || null,
      };
    case 4:
      return {
        firm_address: form.firm_address,
        city: form.city,
        district: form.district || null,
        state: form.state,
        pincode: form.pincode,
      };
    case 5:
      return {
        gst_no: form.gst_no,
        pan_no: form.pan_no,
        aadhaar_no: form.aadhaar_no,
        udyam_no: form.udyam_no || null,
        cin_no: form.cin_no || null,
      };
    case 6:
      return {
        bank_name: form.bank_name,
        bank_branch: form.bank_branch || null,
        account_holder_name: form.account_holder_name,
        account_number: form.account_number,
        ifsc_code: form.ifsc_code,
      };
    case 7:
      return {
        operating_states: form.operating_states,
        product_categories: form.product_categories,
        remarks: form.remarks || null,
      };
    default:
      return {};
  }
}

export default function PartnerRegistrationPublic() {
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [form, setForm] = useState(EMPTY_PARTNER_FORM);
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [success, setSuccess] = useState("");
  const totalSteps = 9;
  const isSubmitted = context?.is_submitted;

  const needsIncorporation = useMemo(
    () => ["Private Limited", "Public Limited", "LLP", "Partnership"].includes(form.business_type),
    [form.business_type],
  );

  function applyContext(result) {
    setContext(result);
    setForm(mapApiToForm(result.data));
    setStep(Math.min(result.current_form_step || 1, totalSteps));
  }

  useEffect(() => {
    partnerRegistrationPublicApi
      .get(token)
      .then(applyContext)
      .catch((error) => setErr(error.response?.data?.detail || "Registration link is invalid"));
  }, [token]);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function saveCurrentStep(nextStep) {
    setBusy(true);
    setErr("");
    try {
      let result = context;
      if (step <= 7) {
        result = await partnerRegistrationPublicApi.saveStep(token, step, stepPayload(step, form));
      }
      applyContext(result);
      setStep(nextStep);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setErr(typeof detail === "string" ? detail : "Failed to save step");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(documentKey, file) {
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const result = await partnerRegistrationPublicApi.uploadDocument(token, documentKey, file);
      applyContext(result);
    } catch (error) {
      setErr(error.response?.data?.detail || "Document upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitForm() {
    if (!form.declaration_accepted) {
      setErr("Please accept the declaration before submitting");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const result = await partnerRegistrationPublicApi.submit(token);
      applyContext(result);
      setSuccess("Your partner registration has been submitted successfully. Our team will review it shortly.");
    } catch (error) {
      setErr(error.response?.data?.detail || "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  if (!context && !err) {
    return <div className="flex min-h-screen items-center justify-center text-slate-600">Loading registration form...</div>;
  }

  if (err && !context) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="max-w-md rounded-xl bg-white p-6 text-center shadow">
          <h1 className="text-lg font-semibold text-slate-900">Link unavailable</h1>
          <p className="mt-2 text-sm text-rose-700">{err}</p>
        </div>
      </div>
    );
  }

  const progress = context?.completion_percent ?? 0;

  return (
    <div className="min-h-screen bg-slate-100 py-6 sm:py-10">
      <div className="mx-auto max-w-3xl space-y-5 px-4">
        <div className="rounded-2xl border border-sky-200 bg-white p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-widest text-sky-700">Indcool Partner Registration</div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">GeM Partner Onboarding Form</h1>
          <p className="mt-1 text-sm text-slate-600">
            Registration No: <span className="font-mono">{context.registration_no}</span>
          </p>
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-slate-600">
              <span>Step {step} of {totalSteps}</span>
              <span>{progress}% complete</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-sky-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(context.form_steps || []).map((item) => (
              <span
                key={item.step}
                className={`rounded-full px-2.5 py-0.5 text-xs ${
                  item.step === step
                    ? "bg-sky-700 text-white"
                    : item.step < step
                      ? "bg-sky-100 text-sky-800"
                      : "bg-slate-100 text-slate-500"
                }`}
              >
                {item.step}. {item.title}
              </span>
            ))}
          </div>
        </div>

        {success && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {success}
          </div>
        )}
        {err && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {err}
          </div>
        )}

        {!isSubmitted && !success && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {step === 1 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Partner Type" required>
                  <select value={form.partner_type} onChange={(e) => setField("partner_type", e.target.value)} className={fieldClass}>
                    {context.partner_types.map((type) => <option key={type} value={type}>{type}</option>)}
                  </select>
                </Field>
                <Field label="Business Type" required>
                  <select value={form.business_type} onChange={(e) => setField("business_type", e.target.value)} className={fieldClass}>
                    {context.business_types.map((type) => <option key={type} value={type}>{type}</option>)}
                  </select>
                </Field>
              </div>
            )}

            {step === 2 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Firm / Company Name" required>
                  <input value={form.name} onChange={(e) => setField("name", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Year of Establishment">
                  <input type="number" value={form.year_of_establishment} onChange={(e) => setField("year_of_establishment", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Annual Turnover (₹)">
                  <input type="number" value={form.annual_turnover} onChange={(e) => setField("annual_turnover", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="GeM Seller ID">
                  <input value={form.gem_seller_id} onChange={(e) => setField("gem_seller_id", e.target.value)} className={fieldClass} />
                </Field>
              </div>
            )}

            {step === 3 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Contact Person Name" required>
                  <input value={form.contact_person_name} onChange={(e) => setField("contact_person_name", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Designation" required>
                  <input value={form.contact_designation} onChange={(e) => setField("contact_designation", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Mobile" required>
                  <input value={form.mobile} onChange={(e) => setField("mobile", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Alternate Mobile">
                  <input value={form.alternate_mobile} onChange={(e) => setField("alternate_mobile", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Email" required>
                  <input type="email" value={form.email} onChange={(e) => setField("email", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Website">
                  <input value={form.website} onChange={(e) => setField("website", e.target.value)} className={fieldClass} />
                </Field>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <Field label="Complete Address" required>
                  <textarea rows={3} value={form.firm_address} onChange={(e) => setField("firm_address", e.target.value)} className={fieldClass} />
                </Field>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label="City" required>
                    <input value={form.city} onChange={(e) => setField("city", e.target.value)} className={fieldClass} />
                  </Field>
                  <Field label="District">
                    <input value={form.district} onChange={(e) => setField("district", e.target.value)} className={fieldClass} />
                  </Field>
                  <Field label="State" required>
                    <select value={form.state} onChange={(e) => setField("state", e.target.value)} className={fieldClass}>
                      <option value="">Select state</option>
                      {INDIAN_STATES.map((state) => <option key={state} value={state}>{state}</option>)}
                    </select>
                  </Field>
                  <Field label="Pincode" required>
                    <input value={form.pincode} onChange={(e) => setField("pincode", e.target.value)} className={fieldClass} />
                  </Field>
                </div>
              </div>
            )}

            {step === 5 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label="GSTIN" required>
                    <input value={form.gst_no} onChange={(e) => setField("gst_no", e.target.value.toUpperCase())} className={fieldClass} />
                  </Field>
                  <Field label="PAN" required>
                    <input value={form.pan_no} onChange={(e) => setField("pan_no", e.target.value)} className={fieldClass} />
                  </Field>
                  <Field label="Aadhaar" required>
                    <input value={form.aadhaar_no} onChange={(e) => setField("aadhaar_no", e.target.value)} className={fieldClass} />
                  </Field>
                  <Field label="Udyam / MSME">
                    <input value={form.udyam_no} onChange={(e) => setField("udyam_no", e.target.value)} className={fieldClass} />
                  </Field>
                  <Field label="CIN">
                    <input value={form.cin_no} onChange={(e) => setField("cin_no", e.target.value)} className={fieldClass} />
                  </Field>
                </div>
              </div>
            )}

            {step === 6 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Bank Name" required>
                  <input value={form.bank_name} onChange={(e) => setField("bank_name", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Branch">
                  <input value={form.bank_branch} onChange={(e) => setField("bank_branch", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Account Holder Name" required>
                  <input value={form.account_holder_name} onChange={(e) => setField("account_holder_name", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Account Number" required>
                  <input value={form.account_number} onChange={(e) => setField("account_number", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="IFSC Code" required>
                  <input value={form.ifsc_code} onChange={(e) => setField("ifsc_code", e.target.value)} className={fieldClass} />
                </Field>
              </div>
            )}

            {step === 7 && (
              <div className="space-y-4">
                <Field label="Operating States / Territory" required>
                  <textarea rows={2} value={form.operating_states} onChange={(e) => setField("operating_states", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Product Categories" required>
                  <textarea rows={2} value={form.product_categories} onChange={(e) => setField("product_categories", e.target.value)} className={fieldClass} />
                </Field>
                <Field label="Remarks">
                  <textarea rows={2} value={form.remarks} onChange={(e) => setField("remarks", e.target.value)} className={fieldClass} />
                </Field>
              </div>
            )}

            {step === 8 && (
              <div className="space-y-3">
                {PARTNER_DOCUMENTS.map((doc) => {
                  const isRequired = doc.required || (doc.key === "incorporation_certificate" && needsIncorporation);
                  const uploaded = context.data?.[`${doc.key}_path`];
                  return (
                    <div key={doc.key} className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
                      <div className="text-sm font-medium text-slate-800">
                        {doc.label}
                        {isRequired ? <span className="text-rose-600"> *</span> : null}
                      </div>
                      {uploaded && (
                        <a href={toFileUrl(uploaded)} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-sky-700 underline">
                          View uploaded file
                        </a>
                      )}
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                        disabled={busy}
                        onChange={(e) => uploadDocument(doc.key, e.target.files?.[0] || null)}
                        className="mt-2 block w-full text-sm"
                      />
                    </div>
                  );
                })}
              </div>
            )}

            {step === 9 && (
              <div className="space-y-4">
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.declaration_accepted}
                    onChange={(e) => setField("declaration_accepted", e.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    I declare that all information and documents provided are true and correct. I authorize Indcool
                    to verify these details for GeM partner onboarding.
                  </span>
                </label>
              </div>
            )}

            <div className="mt-6 flex flex-wrap justify-between gap-3">
              <button
                type="button"
                disabled={busy || step === 1}
                onClick={() => setStep((current) => Math.max(1, current - 1))}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
              >
                Back
              </button>
              {step < 8 && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => saveCurrentStep(step + 1)}
                  className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Save & Continue
                </button>
              )}
              {step === 8 && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setStep(9)}
                  className="rounded-md bg-sky-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Continue to Declaration
                </button>
              )}
              {step === 9 && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={submitForm}
                  className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Submit Registration
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
