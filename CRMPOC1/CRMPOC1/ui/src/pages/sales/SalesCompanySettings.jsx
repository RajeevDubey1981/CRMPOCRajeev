import { useEffect, useState } from "react";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, SalesTabs, btn, errText, fieldClass, useSales } from "./salesUi.jsx";

const FIELDS = [
  ["company_name", "Company name"],
  ["company_address", "Company address"],
  ["company_gstin", "Company GSTIN"],
];

const BANK_FIELDS = [
  ["bank_account_name", "Account name"],
  ["bank_name", "Bank name"],
  ["bank_account_no", "Account number"],
  ["bank_ifsc", "IFSC code"],
  ["bank_branch", "Branch (optional)"],
];

export default function SalesCompanySettings() {
  const { status, reload } = useSales();
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    if (status?.settings) setForm({ ...status.settings });
  }, [status]);

  if (!form) return <div><SalesTabs /><p className="text-sm text-slate-500">Loading...</p></div>;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function save() {
    setBusy(true); setMsg(""); setOk("");
    try {
      await salesApi.updateSettings({
        company_name: form.company_name, company_address: form.company_address, company_gstin: form.company_gstin,
        bank_name: form.bank_name, bank_account_name: form.bank_account_name, bank_account_no: form.bank_account_no,
        bank_ifsc: form.bank_ifsc, bank_branch: form.bank_branch,
      });
      setOk("Saved. New quotations (and reopened ones) will show these details.");
      reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div>
      <PageTitle title="Company details" sub="Shown on every quotation — your GSTIN and bank details, so the customer can pay without asking." />
      <SalesTabs />
      {msg && <Notice tone="bad">{msg}</Notice>}
      {ok && <Notice tone="good">{ok}</Notice>}

      <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-slate-800">Seller details</h3>
        <div className="grid gap-3 md:grid-cols-2">
          {FIELDS.map(([k, label]) => (
            <label key={k} className={`text-sm text-slate-600 ${k === "company_address" ? "md:col-span-2" : ""}`}>
              {label}
              <input className={fieldClass} value={form[k] || ""} onChange={set(k)} />
            </label>
          ))}
        </div>
      </div>

      <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-1 text-sm font-semibold text-slate-800">Bank details for payment</h3>
        <p className="mb-3 text-xs text-slate-500">Shown on the quotation only once an account number is filled in here.</p>
        <div className="grid gap-3 md:grid-cols-2">
          {BANK_FIELDS.map(([k, label]) => (
            <label key={k} className="text-sm text-slate-600">
              {label}
              <input className={fieldClass} value={form[k] || ""} onChange={set(k)} />
            </label>
          ))}
        </div>
      </div>

      <button type="button" className={btn.primary} disabled={busy} onClick={save}>{busy ? "Saving..." : "Save"}</button>
    </div>
  );
}
