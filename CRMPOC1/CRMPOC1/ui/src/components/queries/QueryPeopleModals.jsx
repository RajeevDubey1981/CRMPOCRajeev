import { useEffect, useMemo, useState } from "react";

import Modal from "../Modal.jsx";
import { queriesApi } from "../../api/queries.js";

const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

export const ROLE_LABEL = {
  service_manager: "Service Manager", sales_manager: "Sales Manager", service: "Service Team", sales: "Sales",
  engineer: "Engineer", vendor: "Vendor", admin: "Admin", sub_admin: "Sub Admin", incool: "Admin",
};
const GROUPS = ["service_manager", "sales_manager", "service", "engineer", "vendor", "sales", "sub_admin", "admin"];
export const roleLabel = (role) => ROLE_LABEL[String(role || "").trim().toLowerCase()] || role || "";

function errText(e) {
  const d = e.response?.data?.detail;
  return Array.isArray(d) ? d.map((x) => x.msg).join("; ") : d || "That did not work. Try again";
}

// the people a query can go to, grouped by what they are
function PersonSelect({ people, exclude = [], value, onChange, id }) {
  const groups = useMemo(() => {
    const by = {};
    people.filter((p) => !exclude.includes(p.id)).forEach((p) => {
      const key = String(p.role || "").trim().toLowerCase();
      (by[key] = by[key] || []).push(p);
    });
    return GROUPS.filter((g) => by[g]).map((g) => [g, by[g]]);
  }, [people, exclude]);
  return (
    <select id={id} className={fieldClass} value={value} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}>
      <option value="">Choose a person</option>
      {groups.map(([g, list]) => (
        <optgroup key={g} label={ROLE_LABEL[g] || g}>
          {list.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </optgroup>
      ))}
    </select>
  );
}

function usePeople(open) {
  const [people, setPeople] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!open) return;
    queriesApi.people().then((rows) => { setPeople(rows); setErr(""); }).catch((e) => setErr(errText(e)));
  }, [open]);
  return { people, err };
}

/** Forward the query to one person; it then waits for them, with a new 24 hours. */
export function ForwardModal({ open, onClose, thread, onDone }) {
  const { people, err: loadErr } = usePeople(open);
  const [to, setTo] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { if (open) { setTo(""); setNote(""); setErr(""); } }, [open]);

  async function go(e) {
    e.preventDefault();
    if (!to) { setErr("Choose who to forward it to"); return; }
    setBusy(true);
    setErr("");
    try { onDone(await queriesApi.forward(thread.id, to, note)); } catch (x) { setErr(errText(x)); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Forward this query">
      <form onSubmit={go} className="space-y-3">
        <p className="text-sm text-slate-600">The person gets it on their dashboard and has 24 hours to answer, or an alarm rings for them. They read everything said so far.</p>
        {(loadErr || err) && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadErr || err}</div>}
        <div>
          <label className={labelClass} htmlFor="fwd-to">Forward to</label>
          <PersonSelect id="fwd-to" people={people} exclude={[thread.holder_id].filter(Boolean)} value={to} onChange={setTo} />
          <p className="mt-1 text-xs text-slate-500">Service Manager, Sales Manager, Service Team, Engineer or Vendor.</p>
        </div>
        <div>
          <label className={labelClass} htmlFor="fwd-note">Note for them (optional)</label>
          <textarea id="fwd-note" rows={3} maxLength={1000} className={fieldClass} value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: please check the spare stock" />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Cancel</button>
          <button type="submit" disabled={busy || !to} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">{busy ? "Forwarding..." : "Forward"}</button>
        </div>
      </form>
    </Modal>
  );
}

/** Add a person to the conversation as a member (can write) or in CC (reads, can comment, is not asked to answer). */
export function AddPeopleModal({ open, onClose, thread, onDone }) {
  const { people, err: loadErr } = usePeople(open);
  const [who, setWho] = useState("");
  const [kind, setKind] = useState("member");
  const [history, setHistory] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { if (open) { setWho(""); setKind("member"); setHistory(true); setErr(""); } }, [open]);
  const inside = thread.members.filter((m) => m.active).map((m) => m.user_id);
  const out = thread.members.filter((m) => !m.active);

  async function go(e) {
    e.preventDefault();
    if (!who) { setErr("Choose a person"); return; }
    setBusy(true);
    setErr("");
    try { onDone(await queriesApi.addMember(thread.id, who, kind, history)); } catch (x) { setErr(errText(x)); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Add people to this conversation">
      <form onSubmit={go} className="space-y-3">
        {(loadErr || err) && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadErr || err}</div>}
        {out.length > 0 && (
          <div className="rounded-md bg-slate-50 p-2 text-sm text-slate-600">
            Taken out earlier: {out.map((m) => (
              <button key={m.user_id} type="button" onClick={() => setWho(m.user_id)} className="mr-1 rounded-full border border-slate-300 bg-white px-2 py-0.5 text-xs font-medium text-brand-700 hover:bg-sky-50">{m.name} (add back)</button>
            ))}
          </div>
        )}
        <div>
          <label className={labelClass} htmlFor="add-who">Person</label>
          <PersonSelect id="add-who" people={people} exclude={inside} value={who} onChange={setWho} />
        </div>
        <fieldset>
          <legend className={labelClass}>They are</legend>
          <label className="mr-5 inline-flex items-center gap-2 text-sm"><input type="radio" checked={kind === "member"} onChange={() => setKind("member")} /> A member: takes part and can answer</label>
          <label className="inline-flex items-center gap-2 text-sm"><input type="radio" checked={kind === "cc"} onChange={() => setKind("cc")} /> In CC: reads, and is not asked to answer</label>
        </fieldset>
        <label className="flex items-start gap-2 text-sm text-slate-700"><input type="checkbox" className="mt-1" checked={history} onChange={(e) => setHistory(e.target.checked)} />
          <span>Show them what was said before they came<span className="block text-xs text-slate-500">Private messages sent while someone was out stay private.</span></span></label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Cancel</button>
          <button type="submit" disabled={busy || !who} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">{busy ? "Adding..." : kind === "cc" ? "Add in CC" : "Add"}</button>
        </div>
      </form>
    </Modal>
  );
}
