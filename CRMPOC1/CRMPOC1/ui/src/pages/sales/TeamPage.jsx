import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import Modal from "../../components/Modal.jsx";
import { Footer } from "./LeadModals.jsx";
import { Field, Notice, PageTitle, SalesTabs, TYPE_COLOR, btn, errText, fieldClass, useAsync, useSales } from "./salesUi.jsx";

const STATES = ["Uttar Pradesh", "Delhi", "Haryana", "Rajasthan", "Gujarat", "Maharashtra", "Madhya Pradesh", "Bihar", "West Bengal", "Punjab", "Uttarakhand", "Karnataka", "Tamil Nadu", "Telangana", "Kerala", "Odisha", "Jharkhand", "Chhattisgarh", "Assam"];

function ProfileModal({ person, onClose, onDone }) {
  const { status, has } = useSales();
  const { user } = useAuth();
  const own = person.crm_user_id === user?.id;
  const canTypes = has("types_edit");
  const canTarget = has("targets");
  const [f, setF] = useState({
    phone: person.phone || "", pincode: person.pincode || "", state: person.state || "", district: person.district || "",
    extra_pincodes: (person.extra_pincodes || []).join(", "), areas: (person.areas || []).join(", "),
    types: new Set(person.types_handled || []), target_lakh: person.target_lakh ?? "", is_active: person.is_active,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  async function save() {
    setBusy(true);
    setError("");
    try {
      const body = { phone: f.phone, pincode: f.pincode, state: f.state, district: f.district, extra_pincodes: f.extra_pincodes.split(/[,\s]+/).filter(Boolean).join(",") };
      if (canTypes) { body.types_handled = [...f.types].join(","); body.areas = f.areas; }
      if (canTarget && f.target_lakh !== "") body.target_lakh = Number(f.target_lakh);
      if (!own && has("others_profile")) body.is_active = f.is_active;
      await salesApi.updateProfile(person.crm_user_id, body);
      onDone();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open onClose={onClose} title={`Profile: ${person.name}`} maxWidth="max-w-xl">
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="grid gap-x-3 sm:grid-cols-2">
        <Field label="Phone"><input className={fieldClass} value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Pin code *"><input className={fieldClass} inputMode="numeric" maxLength={6} value={f.pincode} onChange={(e) => setF((s) => ({ ...s, pincode: e.target.value.replace(/\D/g, "") }))} /></Field>
        <Field label="State *"><select className={fieldClass} value={f.state} onChange={set("state")}><option value="">Choose</option>{STATES.map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label="District *"><input className={fieldClass} value={f.district} onChange={set("district")} /></Field>
      </div>
      <Field label="Also covers these pin codes (optional)"><input className={fieldClass} value={f.extra_pincodes} onChange={set("extra_pincodes")} placeholder="110001, 122001" /></Field>
      <Field label="States or countries covered" hint={canTypes ? "Comma separated. A new lead goes first to a member who covers its state." : "Set by your manager"}>
        <input className={fieldClass} value={f.areas} disabled={!canTypes} onChange={set("areas")} placeholder="Uttar Pradesh, Delhi" />
      </Field>
      <div className="mb-3">
        <div className="mb-1 text-sm font-medium text-slate-700">Lead types handled {!canTypes && <span className="font-normal text-slate-500">(set by your manager)</span>}</div>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {(status?.lead_types || []).map((t) => (
            <label key={t.key} className="flex items-center gap-1.5 text-sm"><input type="checkbox" disabled={!canTypes} checked={f.types.has(t.key)} onChange={(e) => setF((s) => { const n = new Set(s.types); if (e.target.checked) n.add(t.key); else n.delete(t.key); return { ...s, types: n }; })} />{t.label}</label>
          ))}
        </div>
      </div>
      {canTarget && <Field label="Monthly target (lakh rupees)"><input className={fieldClass} type="number" min="0" step="0.5" value={f.target_lakh} onChange={set("target_lakh")} /></Field>}
      {!own && has("others_profile") && <label className="mb-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={(e) => setF((s) => ({ ...s, is_active: e.target.checked }))} /> Gets new leads</label>}
      <Footer onClose={onClose}><button type="button" className={btn.go} disabled={busy} onClick={save}>Save profile</button></Footer>
    </Modal>
  );
}

export default function TeamPage() {
  const { has, status } = useSales();
  const typeInfo = Object.fromEntries((status?.lead_types || []).map((t) => [t.key, t]));
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(() => salesApi.team(), []);
  const [edit, setEdit] = useState(null);
  return (
    <div>
      <PageTitle title="Team and profiles" sub="Where each person works, which lead types they handle, and their target. A new lead goes first to a member who handles its type and covers its place." />
      <SalesTabs />
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Member</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">Pin code</th><th className="px-3 py-2">State</th><th className="px-3 py-2">District</th><th className="px-3 py-2">Also covers</th><th className="px-3 py-2">Handles</th><th className="px-3 py-2">Target</th><th className="px-3 py-2" /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {(data || []).map((p) => (
              <tr key={p.crm_user_id}>
                <td className="px-3 py-2"><b>{p.name}</b><div className="text-xs text-slate-500">{p.phone}</div>{!p.is_active && <span className="text-[11px] text-rose-600">not getting leads</span>}</td>
                <td className="px-3 py-2">{p.role === "sales_manager" ? "Sales Manager" : "Sales Team"}</td>
                <td className="px-3 py-2">{p.pincode || "—"}</td><td className="px-3 py-2">{p.state || "—"}</td><td className="px-3 py-2">{p.district || "—"}</td>
                <td className="px-3 py-2">{p.extra_pincodes.join(", ") || "—"}{p.areas.length > 0 && <div className="text-xs text-slate-500">Areas: {p.areas.join(", ")}</div>}</td>
                <td className="px-3 py-2">{p.types_handled.length ? p.types_handled.map((t) => { const info = typeInfo[t] || {}; const c = info.color || TYPE_COLOR[t] || "#64748b"; return <span key={t} className="mr-1 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: `${c}1f`, color: c }}>{info.label || t}</span>; }) : "All types"}</td>
                <td className="px-3 py-2">{p.target_lakh != null ? `₹${p.target_lakh} L` : "—"}</td>
                <td className="px-3 py-2">{(has("others_profile") || (p.crm_user_id === user?.id && has("own_profile"))) && <button type="button" className={btn.plain} onClick={() => setEdit(p)}>Edit profile</button>}</td>
              </tr>
            ))}
            {!loading && (data || []).length === 0 && <tr><td colSpan={9} className="px-3 py-8 text-center text-slate-500">No Sales user yet. Make a user with the role Sales or Sales Manager in Admin, Users.</td></tr>}
          </tbody>
        </table>
      </div>
      {edit && <ProfileModal person={edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); reload(); }} />}
    </div>
  );
}
