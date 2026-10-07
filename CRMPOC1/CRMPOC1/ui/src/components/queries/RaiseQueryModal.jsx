import { useEffect, useState } from "react";

import Modal from "../Modal.jsx";
import { usersAdminApi } from "../../api/admin.js";
import { QUERY_CATEGORIES, announceQueriesChanged, queriesApi } from "../../api/queries.js";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

/**
 * Raise a query (everyone), or, for an Admin / Sub Admin, write to a user first (staff = true).
 * onCreated gets the new thread.
 */
export default function RaiseQueryModal({ open, onClose, onCreated, staff = false }) {
  const [form, setForm] = useState({ category: "General", related_to: "", subject: "", message: "" });
  const [person, setPerson] = useState(null);
  const [personSearch, setPersonSearch] = useState("");
  const [matches, setMatches] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (open) {
      setForm({ category: "General", related_to: "", subject: "", message: "" });
      setPerson(null);
      setPersonSearch("");
      setMatches([]);
      setErr("");
    }
  }, [open]);

  useEffect(() => {
    if (!staff || person || personSearch.trim().length < 2) { setMatches([]); return undefined; }
    const timer = setTimeout(() => {
      usersAdminApi.list({ search: personSearch.trim(), active: true }).then((rows) => setMatches((rows || []).slice(0, 8))).catch(() => setMatches([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [staff, person, personSearch]);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (staff && !person) { setErr("Choose the user you are writing to"); return; }
    setBusy(true);
    try {
      const created = await queriesApi.create({
        subject: form.subject,
        category: form.category,
        related_to: form.related_to || null,
        message: form.message,
        to_user_id: staff ? person.id : undefined,
      });
      announceQueriesChanged();
      onCreated?.(created);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Could not send. Try again");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={staff ? "Write to a user" : "Raise a query"} maxWidth="max-w-xl">
      <form onSubmit={submit} className="space-y-3">
        {!staff && (
          <p className="rounded-md bg-sky-50 px-3 py-2 text-sm text-sky-900">
            Your Admin and Sub Admin will see this and answer here. You will see the reply in Queries.
          </p>
        )}
        {staff && (
          <div>
            <label className={labelClass}>To *</label>
            {person ? (
              <div className="flex items-center justify-between rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm">
                <span><span className="font-medium">{person.name}</span> <span className="text-slate-500">({person.role}) {person.email}</span></span>
                <button type="button" onClick={() => setPerson(null)} className="text-xs font-medium underline">Change</button>
              </div>
            ) : (
              <div className="relative">
                <input value={personSearch} onChange={(e) => setPersonSearch(e.target.value)} placeholder="Type a name or email" className={fieldClass} />
                {matches.length > 0 && (
                  <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-slate-200 bg-white shadow-lg">
                    {matches.map((u) => (
                      <li key={u.id}>
                        <button type="button" onClick={() => { setPerson(u); setMatches([]); }} className="block w-full px-3 py-2 text-left text-sm hover:bg-sky-50">
                          <span className="font-medium">{u.name}</span> <span className="text-xs text-slate-500">{u.role} · {u.email}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={labelClass}>About</label>
            <select value={form.category} onChange={(e) => set("category", e.target.value)} className={fieldClass}>
              {QUERY_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Order / request / complaint number</label>
            <input value={form.related_to} maxLength={200} onChange={(e) => set("related_to", e.target.value)} placeholder="Optional" className={fieldClass} />
          </div>
        </div>
        <div>
          <label className={labelClass}>Subject *</label>
          <input required value={form.subject} maxLength={200} onChange={(e) => set("subject", e.target.value)} placeholder="In a few words" className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Message *</label>
          <textarea required rows={5} value={form.message} maxLength={4000} onChange={(e) => set("message", e.target.value)} placeholder="Write what you need help with" className={fieldClass} />
        </div>
        {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Cancel</button>
          <button type="submit" disabled={busy} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
            {busy ? "Sending..." : "Send"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
