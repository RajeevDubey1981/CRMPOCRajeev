import { useEffect, useMemo, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { rolesApi, usersAdminApi } from "../../api/admin.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { INDIAN_STATES } from "../../constants/indianStates.js";
import { districtsOf } from "../../constants/indianDistricts.js";
import PlaceFields from "../../components/PlaceFields.jsx";
import CoveragePicker, { coverageProblem, coverageText, startCoverage } from "../../components/CoveragePicker.jsx";
import { DEFAULT_ITEM_CATEGORIES } from "../../data/itemCategories.js";
import { itemsApi } from "../../api/items.js";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

const BID_TICK_EXCLUDED = ["admin", "incool", "sub_admin", "vendor"];

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function UserForm({ initial, roles, busy, onCancel, onSubmit }) {
  const isEdit = !!initial?.id;
  const [form, setForm] = useState({
    name: initial?.name || "",
    email: initial?.email || "",
    role: initial?.role || roles[0]?.name || "callcenter",
    phone: initial?.phone || "",
    password: "",
    is_active: initial?.is_active ?? true,
    can_manage_bids: initial?.can_manage_bids ?? false,
    pincode: initial?.pincode || "",
    extra_pincodes: initial?.extra_pincodes || [],
    state: initial?.state || "",
    district: initial?.district || "",
    skills: initial?.skills || [],
    coverage: (() => { const c = startCoverage(initial || {}); return { mode: c.mode, states: c.states }; })(),
  });
  const [categories, setCategories] = useState(DEFAULT_ITEM_CATEGORIES);
  useEffect(() => {
    let live = true;
    itemsApi.categories().then((list) => { if (live && Array.isArray(list)) setCategories([...new Set([...DEFAULT_ITEM_CATEGORIES, ...list])]); }).catch(() => {});
    return () => { live = false; };
  }, []);
  const [err, setErr] = useState("");

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }
  // Admin, Sub Admin and Vendor never need the tick: admins already manage bids and vendors have their own side.
  const bidTickApplies = !BID_TICK_EXCLUDED.includes((form.role || "").toLowerCase());

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!isEdit && form.password.length < 6) {
      setErr("Password must be at least 6 characters");
      return;
    }
    // where an engineer works: sent for engineers only, an empty box clears it
    const placeBody = form.role === "engineer"
      ? { pincode: form.pincode.trim(), state: form.state, district: form.district.trim(), extra_pincodes: form.state ? [] : form.extra_pincodes, coverage: form.coverage, skills: form.skills }
      : {};
    const problem = form.role === "engineer" ? coverageProblem(form.coverage) : "";
    if (problem) { setErr(problem); return; }
    if (placeBody.pincode && !/^[1-9]\d{5}$/.test(placeBody.pincode.replace(/\s+/g, ""))) {
      setErr("Pin code must be 6 digits");
      return;
    }
    try {
      const body = isEdit
        ? {
            name: form.name,
            email: form.email,
            role: form.role,
            phone: form.phone || null,
            is_active: form.is_active,
            can_manage_bids: bidTickApplies && form.can_manage_bids,
            ...placeBody,
          }
        : {
            name: form.name,
            email: form.email,
            password: form.password,
            role: form.role,
            phone: form.phone || null,
            is_active: form.is_active,
            can_manage_bids: bidTickApplies && form.can_manage_bids,
            ...placeBody,
          };
      await onSubmit(body);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to save");
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className={labelClass}>Name *</label>
          <input required value={form.name} onChange={(e) => set("name", e.target.value)} className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Email *</label>
          <input type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Role</label>
          <select value={form.role} onChange={(e) => set("role", e.target.value)} className={fieldClass}>
            {roles.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
          </select>
        </div>
        {form.role === "vendor" && isEdit && (
          <div>
            <label className={labelClass}>Vendor code</label>
            <input
              readOnly
              disabled
              value={initial?.vendor_code || "—"}
              className={`${fieldClass} bg-slate-50 text-slate-700`}
              title={initial?.vendor_id ? `Vendor master id ${initial.vendor_id}` : "No vendor master linked for this email"}
            />
            {!initial?.vendor_code && (
              <p className="mt-1 text-xs text-amber-700">
                No vendor master row matches this user&apos;s email yet.
              </p>
            )}
          </div>
        )}
        <div>
          <label className={labelClass}>Phone</label>
          <input value={form.phone} onChange={(e) => set("phone", e.target.value)} className={fieldClass} />
        </div>
        {form.role === "engineer" && (
          <div className="grid grid-cols-1 gap-3 rounded-md border border-sky-200 bg-sky-50 p-3 md:col-span-2 md:grid-cols-3">
            <div className="md:col-span-3 text-xs font-semibold uppercase tracking-wide text-sky-800">Where this engineer works</div>
            <PlaceFields className="md:col-span-3" value={form} onChange={(patch) => setForm((f) => ({ ...f, ...patch }))} />
            <div className="md:col-span-3 border-t border-sky-200 pt-3">
              <div className="text-sm font-semibold text-slate-800">Which jobs does this engineer get?</div>
              <p className="mb-2 text-xs text-slate-600">New jobs are offered first to engineers who cover the customer place. The place above is where the engineer lives.</p>
              <CoveragePicker value={form.coverage} onChange={(coverage) => set("coverage", coverage)} noun="job" person="engineer" />
            </div>
            <div className="md:col-span-3 border-t border-sky-200 pt-3">
              <div className="text-sm font-semibold text-slate-800">Skills: item categories this engineer works on</div>
              <p className="mb-2 text-xs text-slate-600">Leave all unticked if the engineer works on any category. When a job has a category, engineers who work on it come first.</p>
              <div className="flex flex-wrap gap-2">
                {categories.map((c) => {
                  const on = form.skills.includes(c);
                  return (
                    <button key={c} type="button" onClick={() => set("skills", on ? form.skills.filter((x) => x !== c) : [...form.skills, c])}
                      className={`s-press rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${on ? "border-indcool-blue bg-indcool-blue text-white" : "border-slate-300 bg-white text-slate-600 hover:border-indcool-blue"}`}>
                      {on ? "✓ " : ""}{c}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
        {!isEdit && (
          <div className="md:col-span-2">
            <label className={labelClass}>Password *</label>
            <input
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              className={fieldClass}
              placeholder="min 6 characters"
            />
          </div>
        )}
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} className="h-4 w-4" />
        Active
      </label>
      {bidTickApplies && (
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={form.can_manage_bids} onChange={(e) => set("can_manage_bids", e.target.checked)} className="mt-0.5 h-4 w-4" />
          <span>
            Can manage bids
            <span className="block text-xs text-slate-500">Shows the Bids menu: enter bids, allocate them to vendors and answer vendor requests. Only an Admin or Sub Admin can override a locked bid.</span>
          </span>
        </label>
      )}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
        <button type="submit" disabled={busy} className="rounded-md bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50">
          {busy ? "Saving…" : isEdit ? "Save changes" : "Create user"}
        </button>
      </div>
    </form>
  );
}

function ResetPasswordForm({ onCancel, onSubmit, busy }) {
  const [pwd, setPwd] = useState("");
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (pwd.length < 6) {
      setErr("Password must be at least 6 characters");
      return;
    }
    try { await onSubmit(pwd); } catch (e) {
      setErr(e.response?.data?.detail || "Failed");
    }
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <div>
        <label className={labelClass}>New password</label>
        <input type="password" required minLength={6} value={pwd} onChange={(e) => setPwd(e.target.value)} className={fieldClass} />
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
        <button type="submit" disabled={busy} className="rounded-md bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50">
          {busy ? "Resetting…" : "Reset password"}
        </button>
      </div>
    </form>
  );
}

export default function UserList() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [filters, setFilters] = useState({ search: "", role: "", active: "", pincode: "", state: "", district: "" });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [deactivating, setDeactivating] = useState(null);
  const [busy, setBusy] = useState(false);

  const params = useMemo(() => ({
    search: filters.search || undefined,
    role: filters.role || undefined,
    active: filters.active === "" ? undefined : filters.active === "true",
    pincode: filters.pincode || undefined,
    state: filters.state || undefined,
    district: filters.district || undefined,
  }), [filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setUsers(await usersAdminApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { rolesApi.list().then(setRoles).catch(() => {}); }, []);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [params]);

  const isAdmin = me?.role === "admin";
  const isSubAdmin = (me?.role || "").toLowerCase() === "sub_admin";
  const canManageUsers = isAdmin || isSubAdmin;
  // A Sub Admin works with normal users only: Admin / Sub Admin accounts and roles are Admin-only (the server checks too).
  const PROTECTED_ROLES = ["admin", "incool", "sub_admin"];
  const assignableRoles = isAdmin ? roles : roles.filter((r) => !PROTECTED_ROLES.includes((r.name || "").toLowerCase()));
  const canTouch = (u) => isAdmin || (isSubAdmin && !PROTECTED_ROLES.includes((u.role || "").toLowerCase()));

  async function doCreate(body) {
    setBusy(true);
    try { await usersAdminApi.create(body); setCreating(false); load(); }
    finally { setBusy(false); }
  }
  async function doEdit(body) {
    setBusy(true);
    try { await usersAdminApi.update(editing.id, body); setEditing(null); load(); }
    finally { setBusy(false); }
  }
  async function doReset(pwd) {
    setBusy(true);
    try { await usersAdminApi.resetPassword(resetting.id, pwd); setResetting(null); }
    finally { setBusy(false); }
  }
  async function doDeactivate() {
    setBusy(true);
    try {
      await usersAdminApi.deactivate(deactivating.id);
      setDeactivating(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  }
  async function reactivate(u) {
    await usersAdminApi.update(u.id, { is_active: true });
    load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Users</h1>
        {canManageUsers && (
          <button
            onClick={() => setCreating(true)}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + New User
          </button>
        )}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input
            placeholder="Search name, email, pin code or district"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className={fieldClass}
          />
          <select
            value={filters.role}
            onChange={(e) => setFilters({ ...filters, role: e.target.value })}
            className={fieldClass}
          >
            <option value="">All roles</option>
            {roles.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
          </select>
          <select
            value={filters.active}
            onChange={(e) => setFilters({ ...filters, active: e.target.value })}
            className={fieldClass}
          >
            <option value="">Active and inactive</option>
            <option value="true">Active only</option>
            <option value="false">Inactive only</option>
          </select>
          <input
            inputMode="numeric"
            placeholder="Pin code (or its first digits)"
            value={filters.pincode}
            onChange={(e) => setFilters({ ...filters, pincode: e.target.value.replace(/\D/g, "") })}
            className={fieldClass}
          />
          <select value={filters.state} onChange={(e) => setFilters({ ...filters, state: e.target.value, district: "" })} className={fieldClass}>
            <option value="">All states</option>
            {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {districtsOf(filters.state).length > 0 ? (
            <select value={filters.district} onChange={(e) => setFilters({ ...filters, district: e.target.value })} className={fieldClass}>
              <option value="">All districts of {filters.state}</option>
              {districtsOf(filters.state).map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          ) : (
            <input
              placeholder="District"
              value={filters.district}
              onChange={(e) => setFilters({ ...filters, district: e.target.value })}
              className={fieldClass}
            />
          )}
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Phone</th>
              <th className="px-3 py-2">Area</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={9} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>}
            {!loading && users.length === 0 && <tr><td colSpan={9} className="px-3 py-6 text-center text-slate-500">No users.</td></tr>}
            {!loading && users.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{u.id}</td>
                <td className="px-3 py-2">{u.name}</td>
                <td className="px-3 py-2">{u.email}</td>
                <td className="px-3 py-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{u.role}</span>
                  {u.can_manage_bids && <span className="ml-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700" title="Can manage bids">Bids</span>}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{u.phone || "—"}</td>
                <td className="px-3 py-2 text-xs text-slate-700">
                  {u.pincode || u.district || u.state || (u.extra_pincodes || []).length ? (
                    <>
                      <div>{[u.district, u.state].filter(Boolean).join(", ") || "—"}</div>
                      {(u.pincode || (u.extra_pincodes || []).length > 0) && <div className="font-mono text-slate-500">{[u.pincode, ...(u.extra_pincodes || [])].filter(Boolean).join(", ")}</div>}
                    </>
                  ) : "—"}
                  {u.coverage && <div className="mt-0.5 text-[11px] text-sky-800" title="Which jobs this engineer gets">Covers: {coverageText(u)}</div>}
                  {(u.skills || []).length > 0 && <div className="mt-0.5 flex flex-wrap gap-1">{u.skills.map((s) => <span key={s} className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">{s}</span>)}</div>}
                </td>
                <td className="px-3 py-2">
                  {u.is_active ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">Active</span>
                  ) : (
                    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700">Inactive</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(u.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  {canManageUsers && canTouch(u) && (
                    <div className="flex justify-end gap-1">
                      <button onClick={() => setEditing(u)} className="rounded p-1 text-slate-600 hover:bg-slate-100" title="Edit">✏️</button>
                      <button onClick={() => setResetting(u)} className="rounded p-1 text-slate-600 hover:bg-slate-100" title="Reset password">🔑</button>
                      {u.is_active ? (
                        <button
                          disabled={u.id === me?.id}
                          onClick={() => setDeactivating(u)}
                          className="rounded p-1 text-rose-600 hover:bg-rose-50 disabled:opacity-30"
                          title={u.id === me?.id ? "Can't deactivate yourself" : "Deactivate"}
                        >🚫</button>
                      ) : (
                        <button onClick={() => reactivate(u)} className="rounded p-1 text-emerald-600 hover:bg-emerald-50" title="Reactivate">✓</button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={creating} onClose={() => setCreating(false)} title="New user" maxWidth="max-w-2xl">
        <UserForm
          roles={assignableRoles}
          busy={busy}
          onCancel={() => setCreating(false)}
          onSubmit={doCreate}
        />
      </Modal>

      <Modal open={!!editing} onClose={() => setEditing(null)} title={`Edit ${editing?.name || ""}`} maxWidth="max-w-2xl">
        {editing && (
          <UserForm
            initial={editing}
            roles={assignableRoles}
            busy={busy}
            onCancel={() => setEditing(null)}
            onSubmit={doEdit}
          />
        )}
      </Modal>

      <Modal open={!!resetting} onClose={() => setResetting(null)} title={`Reset password — ${resetting?.email || ""}`}>
        {resetting && (
          <ResetPasswordForm
            busy={busy}
            onCancel={() => setResetting(null)}
            onSubmit={doReset}
          />
        )}
      </Modal>

      <Modal open={!!deactivating} onClose={() => setDeactivating(null)} title="Deactivate user?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            User <span className="font-medium">{deactivating?.name}</span> ({deactivating?.email}) will no longer
            be able to sign in. You can reactivate from this page later.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setDeactivating(null)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button onClick={doDeactivate} disabled={busy} className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50">
              {busy ? "…" : "Deactivate"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
