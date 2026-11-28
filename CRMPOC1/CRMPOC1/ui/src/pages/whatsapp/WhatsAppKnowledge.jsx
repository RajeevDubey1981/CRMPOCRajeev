import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { whatsappApi } from "../../api/whatsapp.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isSystemAdminRole } from "../../utils/roles.js";

const EMPTY = { id: null, title: "", category: "", body: "", always_send: false, active: true };

export default function WhatsAppKnowledge() {
  const { user } = useAuth();
  const isAdmin = isSystemAdminRole(user?.role);
  const [data, setData] = useState({ using: "", items: [] });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState({ kind: "", text: "" });
  const [busy, setBusy] = useState(false);
  const [question, setQuestion] = useState("");
  const [preview, setPreview] = useState(null);
  const [uploadCategory, setUploadCategory] = useState("");
  const [uploadGeneral, setUploadGeneral] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => whatsappApi.kList().then(setData).catch((e) => setMsg({ kind: "err", text: e.response?.data?.detail || "Could not load the knowledge" })), []);
  useEffect(() => { load(); }, [load]);

  const shown = useMemo(() => {
    const q = search.trim().toLowerCase();
    return data.items.filter((i) => {
      if (filter === "general" && !i.always_send) return false;
      if (filter === "off" && i.active) return false;
      if (filter === "lookup" && i.always_send) return false;
      return !q || `${i.title} ${i.category}`.toLowerCase().includes(q);
    });
  }, [data, search, filter]);

  async function open(item) {
    setMsg({ kind: "", text: "" });
    try { setForm(await whatsappApi.kGet(item.id)); } catch (e) { setMsg({ kind: "err", text: e.response?.data?.detail || "Could not open that entry" }); }
  }

  async function run(fn, okText) {
    setBusy(true);
    setMsg({ kind: "", text: "" });
    try {
      const r = await fn();
      await load();
      setMsg({ kind: "ok", text: typeof okText === "function" ? okText(r) : okText });
      return r;
    } catch (e) {
      setMsg({ kind: "err", text: e.response?.data?.detail || "That did not work" });
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function save(e) {
    e.preventDefault();
    const body = { title: form.title, category: form.category, body: form.body, always_send: form.always_send, active: form.active };
    const saved = await run(() => (form.id ? whatsappApi.kUpdate(form.id, body) : whatsappApi.kCreate(body)), "Saved. The assistant uses it from its next reply.");
    if (saved) setForm(saved);
  }

  async function toggle(item) {
    await run(() => whatsappApi.kUpdate(item.id, { active: !item.active }), item.active ? "Switched off" : "Switched on");
  }

  async function remove() {
    if (!form?.id || !window.confirm(`Delete "${form.title}"? This cannot be undone.`)) return;
    if (await run(() => whatsappApi.kDelete(form.id), "Deleted")) setForm(null);
  }

  async function upload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    await run(() => whatsappApi.kUpload(file, uploadCategory, uploadGeneral), (r) => `Added ${r.created} ${r.created === 1 ? "entry" : "entries"} from ${file.name}`);
  }

  async function runPreview(e) {
    e.preventDefault();
    if (!question.trim()) return;
    try { setPreview(await whatsappApi.kPreview(question.trim())); } catch (err) { setMsg({ kind: "err", text: err.response?.data?.detail || "Could not test that" }); }
  }

  if (!isAdmin) {
    return <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Only an administrator can change what the WhatsApp assistant knows.</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link to="/whatsapp" className="text-xs text-[#1e3a8a] hover:underline">&larr; WhatsApp Inbox</Link>
          <h1 className="text-2xl font-semibold text-slate-800">WhatsApp Knowledge</h1>
          <p className="text-sm text-slate-500">What the assistant may say. Changes apply to its very next reply. No deploy needed.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
            {data.using === "database" ? `${data.items.length} entries` : "Using the built-in files (nothing edited yet)"}
          </span>
          {data.using !== "database" && (
            <button type="button" disabled={busy} onClick={() => run(() => whatsappApi.kImport(), (r) => `Copied ${r.created} entries into the editor`)} className="rounded border border-slate-300 px-3 py-1.5 hover:bg-slate-50">
              Copy built-in knowledge into the editor
            </button>
          )}
          <button type="button" onClick={() => setForm({ ...EMPTY })} className="rounded bg-[#1e3a8a] px-3 py-1.5 font-medium text-white">+ New entry</button>
        </div>
      </div>

      {msg.text && <p className={`rounded px-3 py-2 text-sm ${msg.kind === "ok" ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-700"}`}>{msg.text}</p>}

      <div className="grid gap-3 md:grid-cols-[360px_1fr]">
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Upload a file</h2>
            <p className="mb-2 text-xs text-slate-500">Word (.docx), Markdown (.md) or text (.txt). A file with ### headings becomes one entry per heading; any other file is cut into parts. PDFs are not supported yet: save as Word, or paste the text into a new entry.</p>
            <input value={uploadCategory} onChange={(e) => setUploadCategory(e.target.value)} placeholder="Category (optional)" className="mb-2 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <label className="mb-2 flex items-center gap-2 text-xs text-slate-600">
              <input type="checkbox" checked={uploadGeneral} onChange={(e) => setUploadGeneral(e.target.checked)} /> Always send with every question (for short rules only)
            </label>
            <input ref={fileRef} type="file" accept=".docx,.md,.txt,.csv" onChange={upload} className="hidden" />
            <button type="button" disabled={busy} onClick={() => fileRef.current?.click()} className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-60">{busy ? "Working..." : "Choose a file"}</button>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Test a question</h2>
            <form onSubmit={runPreview} className="flex gap-2">
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. my AC shows E6" className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <button type="submit" className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">Test</button>
            </form>
            {preview && (
              <div className="mt-2 text-xs text-slate-600">
                <p>The assistant would get the general rules ({preview.general_chars.toLocaleString()} characters) and {preview.matched.length} matching {preview.matched.length === 1 ? "entry" : "entries"}:</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-4">{preview.matched.map((t, i) => <li key={i}>{t}</li>)}</ul>
                {preview.matched.length === 0 && <p className="mt-1 text-amber-700">Nothing matched, so it would hand this question to staff.</p>}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white">
            <div className="space-y-2 border-b border-slate-200 p-3">
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search entries" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <div className="flex flex-wrap gap-1">
                {[["all", "All"], ["general", "General rules"], ["lookup", "Looked up"], ["off", "Switched off"]].map(([v, l]) => (
                  <button key={v} type="button" onClick={() => setFilter(v)} className={`rounded-full px-2.5 py-1 text-xs ${filter === v ? "bg-[#1e3a8a] text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>{l}</button>
                ))}
              </div>
            </div>
            <ul className="max-h-[420px] overflow-y-auto">
              {shown.length === 0 && <li className="p-4 text-sm text-slate-400">{data.items.length ? "Nothing matches." : "No entries yet."}</li>}
              {shown.map((i) => (
                <li key={i.id} className={`flex items-start gap-2 border-b border-slate-100 px-3 py-2 ${form?.id === i.id ? "bg-blue-50" : ""}`}>
                  <button type="button" onClick={() => open(i)} className="min-w-0 flex-1 text-left">
                    <div className={`truncate text-sm ${i.active ? "text-slate-800" : "text-slate-400 line-through"}`}>{i.title}</div>
                    <div className="truncate text-[11px] text-slate-500">{i.always_send ? "General rule" : i.category || "No category"} &middot; {i.chars.toLocaleString()} characters</div>
                  </button>
                  <button type="button" onClick={() => toggle(i)} title={i.active ? "Switch off" : "Switch on"} className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] ${i.active ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"}`}>{i.active ? "On" : "Off"}</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          {!form ? (
            <p className="text-sm text-slate-400">Pick an entry on the left to edit it, or start a new one.</p>
          ) : (
            <form onSubmit={save} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm font-medium text-slate-700">Title
                  <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm font-normal" />
                </label>
                <label className="block text-sm font-medium text-slate-700">Category
                  <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm font-normal" />
                </label>
              </div>
              <label className="block text-sm font-medium text-slate-700">Text the assistant may use
                <textarea required rows={16} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-xs font-normal" />
              </label>
              <p className="text-xs text-slate-500">{form.body.length.toLocaleString()} characters. Put the model code or the words customers use in the title, because that is how it is found.</p>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.always_send} onChange={(e) => setForm({ ...form, always_send: e.target.checked })} /> General rule (sent with every question; keep it short)</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Active</label>
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={busy} className="rounded bg-[#1e3a8a] px-4 py-2 text-sm font-medium text-white disabled:opacity-60">{busy ? "Saving..." : "Save"}</button>
                {form.id && <button type="button" onClick={remove} className="rounded border border-rose-300 px-4 py-2 text-sm text-rose-700 hover:bg-rose-50">Delete</button>}
                <button type="button" onClick={() => setForm(null)} className="rounded border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50">Close</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
