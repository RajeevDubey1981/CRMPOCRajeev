import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { claimsApi } from "../../api/claims.js";
import { couriersApi } from "../../api/couriers.js";
import { manufacturersApi } from "../../api/manufacturers.js";
import { insuranceApi } from "../../api/insurance.js";

const ROUTED_TO_OPTIONS = [
  { value: "manufacturer", label: "Manufacturer" },
  { value: "courier", label: "Courier" },
  { value: "insurance", label: "Insurance" },
  { value: "company", label: "Company (no external party)" },
];

const ROUTED_TO_API = {
  manufacturer: { api: manufacturersApi, nameField: "name" },
  courier: { api: couriersApi, nameField: "courier_name" },
  insurance: { api: insuranceApi, nameField: "name" },
};

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

export default function ClaimCreate() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    order_no: "",
    serial_number: "",
    customer_name: "",
    customer_contact: "",
    customer_email: "",
    notes: "",
    bank_name: "",
    account_holder_name: "",
    account_number: "",
    ifsc_code: "",
    routed_to: "",
    manufacturer_id: "",
    courier_id: "",
    insurance_id: "",
  });
  const [partyOptions, setPartyOptions] = useState([]);
  const [partyLoading, setPartyLoading] = useState(false);
  const [newPartyName, setNewPartyName] = useState("");
  const [addingParty, setAddingParty] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  const routedConfig = ROUTED_TO_API[form.routed_to];
  const partyIdField = form.routed_to ? `${form.routed_to}_id` : null;

  useEffect(() => {
    setNewPartyName("");
    if (!routedConfig) {
      setPartyOptions([]);
      return;
    }
    setPartyLoading(true);
    routedConfig.api.list({ per_page: 200 })
      .then((r) => setPartyOptions(r.items || []))
      .catch(() => setPartyOptions([]))
      .finally(() => setPartyLoading(false));
  }, [form.routed_to]);

  async function addParty() {
    if (!routedConfig || !newPartyName.trim()) return;
    setAddingParty(true);
    try {
      const body = { [routedConfig.nameField]: newPartyName.trim() };
      const created = await routedConfig.api.create(body);
      setPartyOptions((list) => [created, ...list]);
      set(partyIdField, String(created.id));
      setNewPartyName("");
    } catch (e) {
      setErr(e.response?.data?.detail || `Failed to add this ${form.routed_to}`);
    } finally {
      setAddingParty(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSubmitting(true);
    try {
      const body = {
        order_no: form.order_no || null,
        serial_number: form.serial_number || null,
        customer_name: form.customer_name || null,
        customer_contact: form.customer_contact || null,
        customer_email: form.customer_email || null,
        notes: form.notes || null,
        bank_name: form.bank_name || null,
        account_holder_name: form.account_holder_name || null,
        account_number: form.account_number || null,
        ifsc_code: form.ifsc_code || null,
        routed_to: form.routed_to || null,
        manufacturer_id: form.routed_to === "manufacturer" && form.manufacturer_id ? Number(form.manufacturer_id) : null,
        courier_id: form.routed_to === "courier" && form.courier_id ? Number(form.courier_id) : null,
        insurance_id: form.routed_to === "insurance" && form.insurance_id ? Number(form.insurance_id) : null,
      };
      const created = await claimsApi.create(body);
      navigate(`/claims/${created.id}`);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || "Failed to create claim"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800">New Claim</h1>

      {err && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      <form onSubmit={submit} className="space-y-6 rounded-lg bg-white p-6 shadow-sm">
        {/* Claim / Order details */}
        <div>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Claim Details
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Order No</label>
              <input
                type="text"
                value={form.order_no}
                onChange={(e) => set("order_no", e.target.value)}
                placeholder="e.g. ORD-2026-001"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Serial No</label>
              <input
                type="text"
                value={form.serial_number}
                onChange={(e) => set("serial_number", e.target.value)}
                placeholder="Product serial number"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Name</label>
              <input
                type="text"
                value={form.customer_name}
                onChange={(e) => set("customer_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Contact</label>
              <input
                type="text"
                value={form.customer_contact}
                onChange={(e) => set("customer_contact", e.target.value)}
                placeholder="Phone number"
                className={fieldClass}
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass}>Email</label>
              <input
                type="email"
                value={form.customer_email}
                onChange={(e) => set("customer_email", e.target.value)}
                className={fieldClass}
              />
            </div>
          </div>
          <div className="mt-4">
            <label className={labelClass}>Issue Description</label>
            <textarea
              rows={3}
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              placeholder="Describe the issue or reason for the claim"
              className={fieldClass}
            />
          </div>
        </div>

        {/* Routed to */}
        <div>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Claim Routing
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Routed To</label>
              <select
                value={form.routed_to}
                onChange={(e) => set("routed_to", e.target.value)}
                className={fieldClass}
              >
                <option value="">— Select —</option>
                {ROUTED_TO_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            {routedConfig && (
              <div>
                <label className={labelClass}>
                  {ROUTED_TO_OPTIONS.find((o) => o.value === form.routed_to)?.label}
                </label>
                <select
                  value={form[partyIdField]}
                  onChange={(e) => set(partyIdField, e.target.value)}
                  disabled={partyLoading}
                  className={fieldClass}
                >
                  <option value="">{partyLoading ? "Loading…" : "— Select —"}</option>
                  {partyOptions.map((p) => (
                    <option key={p.id} value={p.id}>{p[routedConfig.nameField]}</option>
                  ))}
                </select>
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={newPartyName}
                    onChange={(e) => setNewPartyName(e.target.value)}
                    placeholder={`Add a new ${form.routed_to}…`}
                    className={`${fieldClass} text-xs`}
                  />
                  <button
                    type="button"
                    onClick={addParty}
                    disabled={addingParty || !newPartyName.trim()}
                    className="shrink-0 rounded-md border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
                  >
                    {addingParty ? "Adding…" : "+ Add"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bank / Settlement details */}
        <div>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Bank &amp; Settlement Details
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Bank Name</label>
              <input
                type="text"
                value={form.bank_name}
                onChange={(e) => set("bank_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Account Holder Name</label>
              <input
                type="text"
                value={form.account_holder_name}
                onChange={(e) => set("account_holder_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Account Number</label>
              <input
                type="text"
                value={form.account_number}
                onChange={(e) => set("account_number", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>IFSC Code</label>
              <input
                type="text"
                value={form.ifsc_code}
                onChange={(e) => set("ifsc_code", e.target.value)}
                placeholder="e.g. SBIN0001234"
                className={fieldClass}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate("/claims")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Create Claim"}
          </button>
        </div>
      </form>
    </div>
  );
}
