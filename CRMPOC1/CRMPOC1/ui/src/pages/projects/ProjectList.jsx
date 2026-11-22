import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { projectsApi } from "../../api/projects.js";
import { fmtIST } from "../../utils/time.js";

const STATUS_COLORS = {
  Draft: "bg-slate-100 text-slate-700",
  Active: "bg-blue-100 text-blue-700",
  Completed: "bg-green-100 text-green-700",
  Cancelled: "bg-rose-100 text-rose-700",
};

function fmt(s) {
  if (!s) return "—";
  try { return fmtIST(s, "Date"); } catch { return s; }
}

export default function ProjectList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", status: "Draft" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setProjects(await projectsApi.list());
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const created = await projectsApi.create(form);
      setShowCreate(false);
      setForm({ title: "", description: "", status: "Draft" });
      navigate(`/projects/${created.id}`);
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to create project");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Projects</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage advisor workflow projects</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New Project
        </button>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">Create Project</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Title *</label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Q3 Advisor Outreach"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Optional description…"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  {["Draft", "Active", "Completed", "Cancelled"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !form.title.trim()}
                  className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
                >
                  {saving ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Project cards */}
      {loading ? (
        <div className="py-12 text-center text-slate-500">Loading…</div>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-slate-200 py-16 text-center text-slate-400">
          <p className="text-lg">No projects yet</p>
          <p className="mt-1 text-sm">Create a project to start building your advisor workflow.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/projects/${p.id}`)}
              className="flex cursor-pointer items-center justify-between rounded-lg bg-white px-5 py-4 shadow-sm ring-1 ring-slate-200 hover:ring-brand-400 transition"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-slate-800 truncate">{p.title}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[p.status] ?? "bg-slate-100 text-slate-700"}`}>
                    {p.status}
                  </span>
                </div>
                {p.description && (
                  <p className="mt-0.5 text-sm text-slate-500 truncate">{p.description}</p>
                )}
              </div>
              <div className="ml-4 shrink-0 text-right text-xs text-slate-400">
                <div>ID #{p.id}</div>
                <div>Updated {fmt(p.updated_at)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
