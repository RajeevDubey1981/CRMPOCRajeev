import { useEffect, useState } from "react";

import { rolesApi } from "../../api/admin.js";
import { moduleLabel, normalizePermissionModules } from "../../utils/permissionModules.js";

const FLAGS = ["can_view", "can_create", "can_edit", "can_delete", "can_export"];
const FLAG_LABELS = { can_view: "V", can_create: "C", can_edit: "E", can_delete: "D", can_export: "X" };

function dot(active) {
  return active ? (
    <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500" title="granted" />
  ) : (
    <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-200" title="denied" />
  );
}

function findPerm(perms, module, sub_module) {
  return perms.find((p) => p.module === module && (p.sub_module ?? null) === (sub_module ?? null)) || {};
}

export default function Permissions() {
  const [modules, setModules] = useState([]);
  const [subModulesByModule, setSubModulesByModule] = useState({});
  const [matrix, setMatrix] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([rolesApi.modules(), rolesApi.matrix()])
      .then(([m, x]) => {
        setModules(normalizePermissionModules(m.modules || []));
        setSubModulesByModule(m.sub_modules || {});
        setMatrix(x);
      })
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load permissions"));
  }, []);

  function renderRow(module, sub_module, label, isSub) {
    return (
      <tr key={`${module}|${sub_module ?? ""}`} className={isSub ? "bg-slate-50/40" : ""}>
        <td className={`px-3 py-2 ${isSub ? "pl-8 text-slate-600" : "font-medium text-slate-700"}`}>
          {isSub ? <span className="text-slate-400">↳ </span> : null}
          {moduleLabel(label)}
        </td>
        {matrix.map((row) => {
          const perm = findPerm(row.permissions, module, sub_module);
          return FLAGS.map((f) => (
            <td key={`${row.role_id}-${module}-${sub_module ?? ""}-${f}`} className="border-l border-slate-200 px-2 py-2 text-center">
              {dot(!!perm[f])}
            </td>
          ));
        })}
      </tr>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Permissions matrix</h1>
        <p className="text-sm text-slate-500">
          Consolidated view of every role × module × sub-module permission. Sub-module rows scope a
          role to specific values (e.g. complaints → Sales). Edit on the Roles page.
        </p>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left text-slate-700">Module</th>
              {matrix.map((row) => (
                <th key={row.role_id} colSpan={FLAGS.length} className="border-l border-slate-200 px-3 py-2 text-center text-slate-700">
                  {row.role}
                </th>
              ))}
            </tr>
            <tr className="bg-slate-50 text-xs text-slate-600">
              <th className="px-3 py-1"></th>
              {matrix.map((row) =>
                FLAGS.map((f) => (
                  <th key={`${row.role_id}-${f}`} className="border-l border-slate-200 px-2 py-1 text-center" title={f.replace("can_", "")}>
                    {FLAG_LABELS[f]}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {modules.flatMap((m) => {
              const subs = subModulesByModule[m] || [];
              const rows = [renderRow(m, null, subs.length ? `${m} (all)` : m, false)];
              subs.forEach((sub) => rows.push(renderRow(m, sub, sub, true)));
              return rows;
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        Legend: <span className="font-mono">V</span> view · <span className="font-mono">C</span> create ·
        <span className="font-mono"> E</span> edit · <span className="font-mono">D</span> delete ·
        <span className="font-mono"> X</span> export
      </p>
    </div>
  );
}
