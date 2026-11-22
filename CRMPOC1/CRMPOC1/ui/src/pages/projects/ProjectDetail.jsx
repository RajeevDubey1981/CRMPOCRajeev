import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { projectsApi } from "../../api/projects.js";
import { fmtIST } from "../../utils/time.js";

const TASK_TYPES = [
  "Add Advisor",
  "Fetch Advisor List",
  "Send Rubric Request",
  "Rubric Validation",
  "Send Survey",
  "Gather Responses",
];

const STATUS_COLORS = {
  Draft:     "bg-slate-100 text-slate-700",
  Active:    "bg-blue-100 text-blue-700",
  Completed: "bg-green-100 text-green-700",
  Cancelled: "bg-rose-100 text-rose-700",
};

const TASK_STATUS_STYLE = {
  Pending:   { dot: "bg-slate-400",  text: "text-slate-600"  },
  Running:   { dot: "bg-blue-500 animate-pulse", text: "text-blue-600" },
  Completed: { dot: "bg-green-500",  text: "text-green-700"  },
  Failed:    { dot: "bg-rose-500",   text: "text-rose-700"   },
  Skipped:   { dot: "bg-slate-300",  text: "text-slate-400"  },
};

function fmt(s) {
  if (!s) return null;
  try { return fmtIST(s, "String"); } catch { return s; }
}

function JsonBlock({ label, data }) {
  if (!data || (typeof data === "object" && Object.keys(data).length === 0)) return null;
  return (
    <div className="mt-2">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <pre className="overflow-auto rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-700 max-h-40 border border-slate-200">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function TaskCard({ task, projectId, onRefresh }) {
  const [expanded, setExpanded] = useState(task.status === "Failed");
  const [running, setRunning] = useState(false);
  const style = TASK_STATUS_STYLE[task.status] ?? TASK_STATUS_STYLE.Pending;
  const borderLeft =
    task.status === "Completed" ? "border-l-green-400"
    : task.status === "Failed"  ? "border-l-rose-400"
    : task.status === "Running" ? "border-l-blue-400"
    : "border-l-slate-200";

  async function handleRun() {
    setRunning(true);
    try {
      await projectsApi.runTask(projectId, task.id);
      onRefresh();
    } catch (e) {
      alert(e.response?.data?.detail || "Task execution failed");
    } finally {
      setRunning(false);
    }
  }

  async function handleReset() {
    try {
      await projectsApi.resetTask(projectId, task.id);
      onRefresh();
    } catch (e) {
      alert(e.response?.data?.detail || "Reset failed");
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete task "${task.task_name}"?`)) return;
    try {
      await projectsApi.deleteTask(projectId, task.id);
      onRefresh();
    } catch (e) {
      alert(e.response?.data?.detail || "Delete failed");
    }
  }

  const hasDetails = task.error_message || task.output_data || task.input_data || task.started_at;

  return (
    <div className={`rounded-lg bg-white shadow-sm ring-1 ring-slate-200 border-l-4 ${borderLeft}`}>
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Sequence */}
        <span className="w-6 shrink-0 text-center text-sm font-mono text-slate-400">{task.sequence}</span>

        {/* Status dot + name */}
        <button
          type="button"
          className="flex flex-1 items-center gap-2 text-left min-w-0"
          onClick={() => hasDetails && setExpanded((v) => !v)}
        >
          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} />
          <span className="font-medium text-slate-800 truncate">{task.task_name}</span>
          {hasDetails && (
            <span className="ml-1 text-slate-400 text-xs">{expanded ? "▾" : "▸"}</span>
          )}
        </button>

        {/* Type badge */}
        <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
          {task.task_type}
        </span>

        {/* Status label */}
        <span className={`shrink-0 text-xs font-medium ${style.text}`}>{task.status}</span>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-1">
          {(task.status === "Pending" || task.status === "Failed") && (
            <button
              onClick={handleRun}
              disabled={running}
              title="Run task"
              className="rounded-md bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {running ? "…" : "▶ Run"}
            </button>
          )}
          {task.status === "Completed" && (
            <button
              onClick={handleReset}
              title="Reset to Pending"
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              ↺ Reset
            </button>
          )}
          <button
            onClick={handleDelete}
            title="Delete task"
            className="rounded-md p-1 text-rose-400 hover:bg-rose-50"
          >
            🗑
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && hasDetails && (
        <div className="border-t border-slate-100 px-4 py-3 space-y-2">
          {task.advisor_id && (
            <p className="text-sm text-slate-600">
              <span className="text-slate-400">Advisor ID: </span>
              <span className="font-mono">{task.advisor_id}</span>
            </p>
          )}
          {task.error_message && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {task.error_message}
            </div>
          )}
          <JsonBlock label="Output" data={task.output_data} />
          <JsonBlock label="Input" data={task.input_data} />
          {(task.started_at || task.completed_at) && (
            <div className="flex gap-4 text-xs text-slate-400">
              {task.started_at && <span>Started: {fmt(task.started_at)}</span>}
              {task.completed_at && <span>Completed: {fmt(task.completed_at)}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AddTaskForm({ projectId, nextSeq, onAdded, onCancel }) {
  const [form, setForm] = useState({
    task_name: "", task_type: "", sequence: nextSeq,
    advisor_id: "", input_data: "",
  });
  const [jsonErr, setJsonErr] = useState("");
  const [saving, setSaving] = useState(false);

  function validateJson(v) {
    if (!v.trim()) { setJsonErr(""); return true; }
    try { JSON.parse(v); setJsonErr(""); return true; }
    catch { setJsonErr("Must be valid JSON"); return false; }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validateJson(form.input_data)) return;
    setSaving(true);
    try {
      await projectsApi.addTask(projectId, {
        task_name: form.task_name,
        task_type: form.task_type,
        sequence: Number(form.sequence),
        advisor_id: form.advisor_id || undefined,
        input_data: form.input_data ? JSON.parse(form.input_data) : undefined,
      });
      onAdded();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to add task");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
      <h3 className="font-medium text-slate-800">Add Task</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Task Name *</label>
          <input
            required autoFocus
            value={form.task_name}
            onChange={(e) => setForm((f) => ({ ...f, task_name: e.target.value }))}
            placeholder="e.g. Fetch advisors for Q3"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Task Type *</label>
          <select
            required
            value={form.task_type}
            onChange={(e) => setForm((f) => ({ ...f, task_type: e.target.value }))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Select type…</option>
            {TASK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Advisor ID (optional)</label>
          <input
            value={form.advisor_id}
            onChange={(e) => setForm((f) => ({ ...f, advisor_id: e.target.value }))}
            placeholder="e.g. ADV-00123"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Sequence</label>
          <input
            type="number" min={1}
            value={form.sequence}
            onChange={(e) => setForm((f) => ({ ...f, sequence: e.target.value }))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Input Data (JSON, optional)</label>
        <textarea
          rows={3}
          value={form.input_data}
          onChange={(e) => { setForm((f) => ({ ...f, input_data: e.target.value })); validateJson(e.target.value); }}
          placeholder='{ "advisor_email": "john@example.com" }'
          className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        {jsonErr && <p className="mt-1 text-xs text-rose-600">{jsonErr}</p>}
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-white">Cancel</button>
        <button
          type="submit"
          disabled={saving || !form.task_name.trim() || !form.task_type}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "Adding…" : "Add Task"}
        </button>
      </div>
    </form>
  );
}

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [addingTask, setAddingTask] = useState(false);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setErr("");
    try {
      setProject(await projectsApi.get(id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function handleRunAll(resume = false) {
    setRunning(true);
    try {
      const result = await projectsApi.runProject(id, resume);
      if (result.status === "Completed") alert("All tasks completed successfully.");
      else if (result.status === "Failed") alert(`Workflow stopped at: "${result.failed_at}"`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Execution error");
    } finally {
      setRunning(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete project "${project?.title}"?`)) return;
    await projectsApi.remove(id);
    navigate("/projects");
  }

  if (loading) return <div className="py-12 text-center text-slate-500">Loading…</div>;
  if (err) return <div className="rounded-md bg-rose-50 px-4 py-3 text-rose-700">{err}</div>;
  if (!project) return null;

  const hasFailed = project.summary?.failed > 0;
  const hasRunning = project.summary?.running > 0;
  const nextSeq = (project.tasks?.reduce((m, t) => Math.max(m, t.sequence), 0) ?? 0) + 1;

  return (
    <div className="space-y-5">
      {/* Back */}
      <button
        type="button"
        onClick={() => navigate("/projects")}
        className="text-sm text-slate-500 hover:text-slate-800"
      >
        ← Projects
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold text-slate-800">{project.title}</h1>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[project.status] ?? "bg-slate-100 text-slate-700"}`}>
              {project.status}
            </span>
          </div>
          {project.description && (
            <p className="mt-1 text-sm text-slate-500">{project.description}</p>
          )}
          <p className="mt-0.5 text-xs text-slate-400">Project #{project.id}</p>
        </div>

        <div className="flex gap-2 flex-wrap">
          {hasFailed && (
            <button
              onClick={() => handleRunAll(true)}
              disabled={running}
              className="rounded-md border border-brand-600 px-3 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 disabled:opacity-50"
            >
              {running ? "Running…" : "↻ Resume"}
            </button>
          )}
          <button
            onClick={() => handleRunAll(false)}
            disabled={running || hasRunning || project.tasks?.length === 0}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {running || hasRunning ? "Running…" : "▶ Run All"}
          </button>
          <button
            onClick={handleDelete}
            className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Summary bar */}
      {project.tasks?.length > 0 && (
        <div className="flex flex-wrap gap-4 rounded-lg bg-white px-5 py-3 shadow-sm ring-1 ring-slate-200 text-sm">
          <span className="text-slate-500">{project.summary.total} tasks</span>
          {project.summary.completed > 0 && <span className="text-green-600">✓ {project.summary.completed} completed</span>}
          {project.summary.pending > 0 && <span className="text-slate-500">◷ {project.summary.pending} pending</span>}
          {project.summary.running > 0 && <span className="text-blue-600">⟳ {project.summary.running} running</span>}
          {project.summary.failed > 0 && <span className="text-rose-600">✕ {project.summary.failed} failed</span>}
          {project.summary.skipped > 0 && <span className="text-slate-400">— {project.summary.skipped} skipped</span>}
        </div>
      )}

      {/* Task timeline */}
      <div className="space-y-2">
        {project.tasks?.length === 0 ? (
          <p className="py-4 text-sm text-slate-400">No tasks yet. Add a task below to build your workflow.</p>
        ) : (
          project.tasks.map((task) => (
            <TaskCard key={task.id} task={task} projectId={id} onRefresh={load} />
          ))
        )}
      </div>

      {/* Add task */}
      {addingTask ? (
        <AddTaskForm
          projectId={id}
          nextSeq={nextSeq}
          onAdded={() => { setAddingTask(false); load(); }}
          onCancel={() => setAddingTask(false)}
        />
      ) : (
        <button
          type="button"
          onClick={() => setAddingTask(true)}
          className="w-full rounded-lg border-2 border-dashed border-slate-200 py-3 text-sm text-slate-400 hover:border-brand-400 hover:text-brand-600 transition"
        >
          + Add Task
        </button>
      )}
    </div>
  );
}
