import { useEffect, useState } from "react";

import Modal from "../../components/Modal.jsx";
import { rolesApi } from "../../api/admin.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { moduleLabel, normalizePermissionModules } from "../../utils/permissionModules.js";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";
const FLAGS = ["can_view", "can_create", "can_edit", "can_delete", "can_export"];
const FLAG_LABELS = { can_view: "View", can_create: "Create", can_edit: "Edit", can_delete: "Delete", can_export: "Export" };

function permKey(module, sub_module) {
  return `${module}|${sub_module ?? ""}`;
}

function blankRow(module, sub_module) {
  return { module, sub_module, can_view: false, can_create: false, can_edit: false, can_delete: false, can_export: false };
}

function PermissionMatrix({ modules, subModulesByModule, permissions, onChange, readOnly = false }) {
  const byKey = Object.fromEntries(permissions.map((p) => [permKey(p.module, p.sub_module), p]));

  function update(module, sub_module, flag, value) {
    if (readOnly) return;
    const key = permKey(module, sub_module);
    const current = byKey[key] || blankRow(module, sub_module);
    const next = { ...current, [flag]: value };
    const updated = permissions.some((p) => permKey(p.module, p.sub_module) === key)
      ? permissions.map((p) => permKey(p.module, p.sub_module) === key ? next : p)
      : [...permissions, next];
    onChange(updated);
  }

  function toggleAll(module, sub_module, value) {
    if (readOnly) return;
    const key = permKey(module, sub_module);
    const next = { module, sub_module, can_view: value, can_create: value, can_edit: value, can_delete: value, can_export: value };
    const updated = permissions.some((p) => permKey(p.module, p.sub_module) === key)
      ? permissions.map((p) => permKey(p.module, p.sub_module) === key ? next : p)
      : [...permissions, next];
    onChange(updated);
  }

  function rowFor(module, sub_module) {
    return byKey[permKey(module, sub_module)] || blankRow(module, sub_module);
  }

  function renderRow(module, sub_module, label, isSub) {
    const row = rowFor(module, sub_module);
    return (
      <tr key={permKey(module, sub_module)} className={isSub ? "bg-slate-50/50" : ""}>
        <td className={`px-3 py-2 ${isSub ? "pl-8 text-slate-600" : "font-medium text-slate-700"}`}>
          {isSub ? <span className="text-slate-400">↳ </span> : null}
          {moduleLabel(label)}
        </td>
        {FLAGS.map((f) => (
          <td key={f} className="px-3 py-2 text-center">
            <input
              type="checkbox"
              checked={!!row[f]}
              disabled={readOnly}
              onChange={(e) => update(module, sub_module, f, e.target.checked)}
              className="h-4 w-4"
            />
          </td>
        ))}
        {!readOnly && (
          <td className="px-3 py-2 text-center">
            <button type="button" onClick={() => toggleAll(module, sub_module, true)} className="rounded px-1.5 py-0.5 text-xs text-slate-600 hover:bg-slate-100">all</button>
            <button type="button" onClick={() => toggleAll(module, sub_module, false)} className="ml-1 rounded px-1.5 py-0.5 text-xs text-slate-600 hover:bg-slate-100">none</button>
          </td>
        )}
      </tr>
    );
  }

  return (
    <div className="crm-scroll">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100 text-left text-slate-700">
          <tr>
            <th className="px-3 py-2">Module</th>
            {FLAGS.map((f) => <th key={f} className="px-3 py-2 text-center">{FLAG_LABELS[f]}</th>)}
            {!readOnly && <th className="px-3 py-2 text-center">All</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {modules.map((m) => {
            const subs = subModulesByModule[m] || [];
            const rows = [renderRow(m, null, subs.length ? `${m} (all)` : m, false)];
            subs.forEach((sub) => rows.push(renderRow(m, sub, sub, true)));
            return rows;
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">
        Leave the parent row blank and tick a sub-module to scope this role to that query type only
        (e.g. complaints → Sales gives access to Sales complaints only).
      </p>
    </div>
  );
}

function RoleEditor({ role, modules, subModulesByModule, onClose, onSaved }) {
  const [name, setName] = useState(role?.name || "");
  const [description, setDescription] = useState(role?.description || "");
  const [permissions, setPermissions] = useState(role?.permissions || []);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    setBusy(true);
    setErr("");
    try {
      let saved = role;
      if (!role?.id) {
        saved = await rolesApi.create({ name, description: description || null });
      } else if (name !== role.name || description !== role.description) {
        saved = await rolesApi.update(role.id, { name, description: description || null });
      }
      await rolesApi.setPermissions(saved.id, permissions);
      onSaved?.();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className={labelClass}>Role name *</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={fieldClass} />
        </div>
      </div>
      <div>
        <label className={labelClass}>Permissions</label>
        <PermissionMatrix
          modules={modules}
          subModulesByModule={subModulesByModule}
          permissions={permissions}
          onChange={setPermissions}
        />
      </div>
      <div className="flex justify-end gap-2">
        <button onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
        <button onClick={save} disabled={busy || !name} className="rounded-md bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50">
          {busy ? "Saving…" : role?.id ? "Save changes" : "Create role"}
        </button>
      </div>
    </div>
  );
}

export default function RoleList() {
  const { user: me } = useAuth();
  const [roles, setRoles] = useState([]);
  const [modules, setModules] = useState([]);
  const [subModulesByModule, setSubModulesByModule] = useState({});
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const list = await rolesApi.list();
      const detailed = await Promise.all(list.map((r) => rolesApi.get(r.id)));
      setRoles(detailed);
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load roles");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    rolesApi.modules()
      .then((m) => {
        setModules(normalizePermissionModules(m.modules || []));
        setSubModulesByModule(m.sub_modules || {});
      })
      .catch(() => {});
    load();
  }, []);

  const isAdmin = me?.role === "admin";

  async function doDelete() {
    try {
      await rolesApi.remove(deleting.id);
      setDeleting(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Roles</h1>
        {isAdmin && (
          <button onClick={() => setCreating(true)} className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">
            + New Role
          </button>
        )}
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {loading && <div className="text-sm text-slate-500">Loading…</div>}

      <div className="space-y-4">
        {roles.map((r) => (
          <div key={r.id} className="rounded-lg bg-white p-4 shadow-sm">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-slate-800">{r.name}</h2>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {r.user_count} user{r.user_count === 1 ? "" : "s"}
                  </span>
                </div>
                {r.description && <p className="text-sm text-slate-500">{r.description}</p>}
              </div>
              {isAdmin && (
                <div className="flex gap-2">
                  <button onClick={() => setEditing(r)} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">Edit</button>
                  <button
                    onClick={() => setDeleting(r)}
                    disabled={r.user_count > 0}
                    title={r.user_count > 0 ? "Cannot delete a role in use" : "Delete role"}
                    className="rounded-md border border-rose-300 px-3 py-1.5 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-40"
                  >Delete</button>
                </div>
              )}
            </div>
            <PermissionMatrix
              modules={modules}
              subModulesByModule={subModulesByModule}
              permissions={r.permissions}
              readOnly
              onChange={() => {}}
            />
          </div>
        ))}
      </div>

      <Modal open={creating} onClose={() => setCreating(false)} title="New role" maxWidth="max-w-5xl">
        {creating && (
          <RoleEditor
            role={{ name: "", description: "", permissions: [] }}
            modules={modules}
            subModulesByModule={subModulesByModule}
            onClose={() => setCreating(false)}
            onSaved={() => { setCreating(false); load(); }}
          />
        )}
      </Modal>

      <Modal open={!!editing} onClose={() => setEditing(null)} title={`Edit role — ${editing?.name || ""}`} maxWidth="max-w-5xl">
        {editing && (
          <RoleEditor
            role={editing}
            modules={modules}
            subModulesByModule={subModulesByModule}
            onClose={() => setEditing(null)}
            onSaved={() => { setEditing(null); load(); }}
          />
        )}
      </Modal>

      <Modal open={!!deleting} onClose={() => setDeleting(null)} title="Delete role?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will permanently delete the role <span className="font-medium">{deleting?.name}</span>.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setDeleting(null)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button onClick={doDelete} className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700">Delete</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
