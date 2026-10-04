import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../auth/AuthContext.jsx";
import { hasPermission } from "../../utils/permissions.js";
import { accountsApi, accError, fieldClass, labelClass } from "../../api/accounts.js";

const BLANK = {
  name: "", gstin: "", state: "", address: "", city: "", pincode: "", contact_name: "", phone: "", email: "",
  is_msme: false, msme_no: "", payment_terms_days: 30, bank_name: "", bank_account: "", bank_ifsc: "", is_active: true,
};

export default function SupplierList() {
  const { user } = useAuth();
  const canCreate = hasPermission(user, "acc_purchase", "can_create");
  const canEdit = hasPermission(user, "acc_purchase", "can_edit");
  const [data, setData] = useState({ items: [], total: 0 });
  const [states, setStates] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(null);
  const [editId, setEditId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");

  const load = () => accountsApi.suppliers({ search: search || undefined, per_page: 200 }).then(setData).catch((e) => setErr(accError(e, "Could not load suppliers")));
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [search]);
  useEffect(() => { accountsApi.meta().then((m) => setStates(m.states || [])).catch(() => {}); }, []);

  const hasGstin = useMemo(() => (form?.gstin || "").trim().length > 0, [form?.gstin]);

  function open(s) {
    setErr(""); setNote("");
    if (s) {
      setEditId(s.id);
      setForm({ ...BLANK, ...Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v ?? (typeof BLANK[k] === "boolean" ? false : "")])) });
    } else { setEditId(null); setForm({ ...BLANK }); }
  }

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function save(e) {
    e.preventDefault();
    setBusy(true); setErr(""); setNote("");
    const body = {
      name: form.name, gstin: form.gstin.trim() || null, state: hasGstin ? null : form.state || null,
      address: form.address || null, city: form.city || null, pincode: form.pincode || null, contact_name: form.contact_name || null,
      phone: form.phone || null, email: form.email || null, is_msme: !!form.is_msme, msme_no: form.is_msme ? form.msme_no || null : null,
      payment_terms_days: Number(form.payment_terms_days) || 0, bank_name: form.bank_name || null, bank_account: form.bank_account || null,
      bank_ifsc: form.bank_ifsc || null, is_active: !!form.is_active,
    };
    try {
      if (editId) await accountsApi.updateSupplier(editId, body); else await accountsApi.createSupplier(body);
      setNote(editId ? "Supplier updated." : "Supplier added.");
      setForm(null); setEditId(null);
      load();
    } catch (e2) { setErr(accError(e2, "Could not save the supplier")); }
    finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Suppliers</h1>
          <p className="text-sm text-slate-500">OEMs, component makers and contract manufacturers we buy from. The GSTIN decides CGST+SGST or IGST on a purchase order.</p>
        </div>
        {canCreate && !form && <button type="button" onClick={() => open(null)} className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">+ Add supplier</button>}
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {note && <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{note}</div>}

      {form && (
        <form onSubmit={save} className="space-y-4 rounded-lg bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800">{editId ? "Edit supplier" : "New supplier"}</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="md:col-span-2"><label className={labelClass}>Name *</label><input required value={form.name} onChange={(e) => set("name", e.target.value)} className={fieldClass} /></div>
            <div>
              <label className={labelClass}>GSTIN</label>
              <input value={form.gstin} onChange={(e) => set("gstin", e.target.value.toUpperCase())} maxLength={15} className={`${fieldClass} font-mono`} placeholder="Leave empty if unregistered" />
            </div>
            {!hasGstin && (
              <div>
                <label className={labelClass}>State * <span className="font-normal text-slate-500">(from the GSTIN when there is one)</span></label>
                <select value={form.state} onChange={(e) => set("state", e.target.value)} className={fieldClass}>
                  <option value="">Choose state</option>
                  {states.map((s) => <option key={s.code} value={s.name}>{s.name}</option>)}
                </select>
              </div>
            )}
            <div><label className={labelClass}>City</label><input value={form.city} onChange={(e) => set("city", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Pincode</label><input value={form.pincode} onChange={(e) => set("pincode", e.target.value)} className={fieldClass} /></div>
            <div className="md:col-span-3"><label className={labelClass}>Address</label><input value={form.address} onChange={(e) => set("address", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Contact person</label><input value={form.contact_name} onChange={(e) => set("contact_name", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Phone</label><input value={form.phone} onChange={(e) => set("phone", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Email</label><input value={form.email} onChange={(e) => set("email", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Payment terms (days)</label><input type="number" min="0" value={form.payment_terms_days} onChange={(e) => set("payment_terms_days", e.target.value)} className={fieldClass} /></div>
            <div className="flex items-center gap-2 pt-6">
              <input id="msme" type="checkbox" checked={form.is_msme} onChange={(e) => set("is_msme", e.target.checked)} className="h-4 w-4" />
              <label htmlFor="msme" className="text-sm font-medium text-slate-700">MSME supplier (pay within 45 days)</label>
            </div>
            {form.is_msme && <div><label className={labelClass}>Udyam number</label><input value={form.msme_no} onChange={(e) => set("msme_no", e.target.value)} className={fieldClass} /></div>}
            <div><label className={labelClass}>Bank</label><input value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>Account number</label><input value={form.bank_account} onChange={(e) => set("bank_account", e.target.value)} className={fieldClass} /></div>
            <div><label className={labelClass}>IFSC</label><input value={form.bank_ifsc} onChange={(e) => set("bank_ifsc", e.target.value.toUpperCase())} maxLength={11} className={`${fieldClass} font-mono`} /></div>
            <div className="flex items-center gap-2 pt-6">
              <input id="sup_active" type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} className="h-4 w-4" />
              <label htmlFor="sup_active" className="text-sm font-medium text-slate-700">Active</label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => { setForm(null); setEditId(null); }} className="rounded-md border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={busy} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">{busy ? "Saving..." : "Save supplier"}</button>
          </div>
        </form>
      )}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, GSTIN or city" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-80" />
      </div>

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">GSTIN</th><th className="px-3 py-2">State</th><th className="px-3 py-2">Terms</th><th className="px-3 py-2">Flags</th><th className="px-3 py-2">Phone</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">No suppliers yet.</td></tr>}
            {data.items.map((s) => (
              <tr key={s.id} className={canEdit ? "cursor-pointer hover:bg-slate-50" : ""} onClick={() => canEdit && open(s)}>
                <td className="px-3 py-2 font-medium text-slate-800">{s.name}</td>
                <td className="px-3 py-2 font-mono text-xs">{s.gstin || <span className="text-amber-700">Unregistered</span>}</td>
                <td className="px-3 py-2 text-slate-600">{s.state || "-"}</td>
                <td className="px-3 py-2">{s.payment_terms_days} days</td>
                <td className="px-3 py-2 space-x-1">
                  {s.is_msme && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">MSME</span>}
                  {!s.is_active && <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600">Inactive</span>}
                </td>
                <td className="px-3 py-2 text-slate-600">{s.phone || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
