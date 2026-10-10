import { useMemo, useState } from "react";

import { salesApi } from "../../api/sales.js";
import Modal from "../../components/Modal.jsx";
import { HEAT, PRIORITY, Field, Notice, btn, errText, fieldClass, useSales } from "./salesUi.jsx";

export function suggestHeat(answers, rules) {
  let score = 0;
  const why = [];
  (rules || []).forEach((r) => {
    if (answers[r.key]) { score += r.points; why.push(r.label); }
  });
  return { level: score >= 7 ? "hot" : score >= 3 ? "warm" : "cold", why, score };
}

export function Footer({ onClose, children }) {
  return (
    <div className="mt-4 flex flex-wrap justify-end gap-2 border-t pt-3">
      <button type="button" className={btn.plain} onClick={onClose}>Cancel</button>
      {children}
    </div>
  );
}

// ---------------- add a lead ----------------
const NEW_LEAD = { name: "", phone: "", email: "", item: "", place: "", state: "", district: "", pincode: "", country: "", lead_type: "", details: "", value_lakh: "", price_basis: "", closes_on: "" };

export function AddLeadModal({ open, onClose, onDone }) {
  const { status } = useSales();
  const [f, setF] = useState(NEW_LEAD);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));
  const export_ = f.lead_type === "export";

  async function save() {
    setBusy(true);
    setError("");
    try {
      const body = { ...f, value_lakh: f.value_lakh === "" ? null : Number(f.value_lakh), closes_on: f.closes_on || null, lead_type: f.lead_type || null };
      Object.keys(body).forEach((k) => { if (body[k] === "") body[k] = null; });
      const r = await salesApi.addLead(body);
      setF(NEW_LEAD);
      onDone?.(r);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a lead" maxWidth="max-w-2xl">
      {error && <Notice tone="bad">{error}</Notice>}
      <div className="grid gap-x-3 sm:grid-cols-2">
        <Field label="Lead type" hint="Leave empty to let the rules decide from the words">
          <select className={fieldClass} value={f.lead_type} onChange={set("lead_type")}>
            <option value="">Decide from the words</option>
            {(status?.lead_types || []).map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
        </Field>
        <Field label="Name *"><input className={fieldClass} value={f.name} onChange={set("name")} /></Field>
        <Field label="Phone *"><input className={fieldClass} value={f.phone} onChange={set("phone")} placeholder={export_ ? "+977 98510 22334" : "98100 11223"} /></Field>
        <Field label="Email"><input className={fieldClass} value={f.email} onChange={set("email")} /></Field>
        <Field label="Wants (item and quantity)"><input className={fieldClass} value={f.item} onChange={set("item")} placeholder="Split AC 1.5 Ton x 20" /></Field>
        <Field label="Place"><input className={fieldClass} value={f.place} onChange={set("place")} placeholder={export_ ? "Kathmandu" : "Noida"} /></Field>
        {export_ ? (
          <>
            <Field label="Country"><input className={fieldClass} value={f.country} onChange={set("country")} placeholder="Nepal, Kenya, Ghana or Sri Lanka" /></Field>
            <Field label="Price basis"><input className={fieldClass} value={f.price_basis} onChange={set("price_basis")} placeholder="FOB Mundra, CIF Mombasa, DAP Birgunj" /></Field>
          </>
        ) : (
          <>
            <Field label="State"><input className={fieldClass} value={f.state} onChange={set("state")} placeholder="Uttar Pradesh" /></Field>
            <Field label="Pin code"><input className={fieldClass} inputMode="numeric" maxLength={6} value={f.pincode} onChange={(e) => setF((s) => ({ ...s, pincode: e.target.value.replace(/\D/g, "") }))} /></Field>
          </>
        )}
        <Field label="Estimated value in lakh rupees" hint="Helps the priority"><input className={fieldClass} type="number" min="0" step="0.1" value={f.value_lakh} onChange={set("value_lakh")} /></Field>
        {(f.lead_type === "gem" || f.lead_type === "tender") && (
          <Field label="Last date of the bid or tender"><input className={fieldClass} type="date" value={f.closes_on} onChange={set("closes_on")} /></Field>
        )}
      </div>
      <Field label="Details"><textarea className={fieldClass} rows={2} value={f.details} onChange={set("details")} placeholder="Bid number, department, GST, anything that helps" /></Field>
      <Footer onClose={onClose}><button type="button" className={btn.go} disabled={busy} onClick={save}>Add lead</button></Footer>
    </Modal>
  );
}

// ---------------- log a call and rate ----------------
export function CallModal({ lead, open, onClose, onDone, rateOnly = false }) {
  const { status, has } = useSales();
  const rules = status?.heat_rules || [];
  const initial = useMemo(() => {
    const a = { ...(lead.rating_answers || {}) };
    return a;
  }, [lead]);
  const [outcome, setOutcome] = useState("Spoke: interested");
  const [note, setNote] = useState("");
  const [follow, setFollow] = useState("");
  const [answers, setAnswers] = useState(initial);
  const [time, setTime] = useState(initial.time15 ? "15" : initial.time45 ? "45" : "");
  const [heat, setHeat] = useState(null);
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const full = { ...answers, time15: time === "15", time45: time === "45" };
  const sg = suggestHeat(full, rules);
  const pick = heat || sg.level;
  const changed = pick !== sg.level && pick !== lead.heat;
  const govt = ["gem", "tender"].includes(lead.lead_type);
  const canRate = has("rate");
  const toggle = (k) => (e) => { setHeat(null); setAnswers((s) => ({ ...s, [k]: e.target.checked })); };

  async function save() {
    setBusy(true);
    setError("");
    try {
      if (rateOnly) await salesApi.rate(lead.id, { answers: full, heat: pick, why });
      else await salesApi.call(lead.id, { outcome, note, next_follow_up: follow || null, answers: canRate ? full : undefined, heat: canRate ? pick : undefined, why });
      onDone?.();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }

  const box = (k, label) => (
    <label key={k} className="flex items-center gap-2 py-0.5 text-sm"><input type="checkbox" checked={!!answers[k]} onChange={toggle(k)} /> {label}</label>
  );
  return (
    <Modal open={open} onClose={onClose} title={`${rateOnly ? "Rate this lead" : "Log a call"}: ${lead.name}`} maxWidth="max-w-xl">
      {error && <Notice tone="bad">{error}</Notice>}
      {!rateOnly && (
        <>
          <Field label="What happened">
            <select className={fieldClass} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
              {["Spoke: interested", "Spoke: needs a quote", "Spoke: will think and call back", "No answer", "Phone switched off", "Sent a WhatsApp or mail"].map((o) => <option key={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Note"><textarea className={fieldClass} rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="A line for the history" /></Field>
          <Field label="Next follow-up"><input className={fieldClass} type="date" value={follow} onChange={(e) => setFollow(e.target.value)} /></Field>
        </>
      )}
      {(canRate || rateOnly) && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="mb-2 text-xs text-slate-600">Tick what is true now. The rules suggest Hot, Warm or Cold from your answers, and you can change it.</p>
          {box("quote", "Asked for a quote or price")}
          {box("budget", "Budget is confirmed")}
          {box("boss", "Spoke to the decision maker")}
          {govt && box("soon", "Bid or tender closes within 7 days")}
          {box("noans", "No answer on the last calls")}
          {box("stale", "No contact for 7 days or more")}
          <Field label="When will they buy?">
            <select className={fieldClass} value={time} onChange={(e) => { setHeat(null); setTime(e.target.value); }}>
              <option value="">Not sure</option><option value="45">Within 45 days</option><option value="15">Within 15 days</option>
            </select>
          </Field>
          <div className="mb-2 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
            <b>The rules suggest: {HEAT[sg.level].label}</b> ({sg.score} point{sg.score === 1 ? "" : "s"})
            <div className="mt-1 flex flex-wrap gap-1">{sg.why.map((w) => <span key={w} className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-600">{w}</span>)}{sg.why.length === 0 && <span className="text-xs text-slate-500">Nothing ticked yet</span>}</div>
          </div>
          <Field label="Rating *">
            <select className={fieldClass} value={pick} onChange={(e) => setHeat(e.target.value)}>
              {Object.keys(HEAT).map((k) => <option key={k} value={k}>{HEAT[k].label}: {HEAT[k].hint.toLowerCase()}</option>)}
            </select>
          </Field>
          {changed && <Field label="Why is it different from the suggestion? *"><input className={fieldClass} value={why} onChange={(e) => setWhy(e.target.value)} placeholder="For example: customer called back and wants to order today" /></Field>}
        </div>
      )}
      <Footer onClose={onClose}><button type="button" className={btn.primary} disabled={busy} onClick={save}>Save</button></Footer>
    </Modal>
  );
}

// ---------------- priority ----------------
export function PriorityModal({ lead, open, onClose, onDone, flag }) {
  const [level, setLevel] = useState(flag ? "high" : lead.priority);
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await salesApi.priority(lead.id, { level, why, flag: !!flag });
      onDone?.();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onClose} title={`${flag ? "Flag as high priority" : "Set the priority"}: ${lead.name}`}>
      {error && <Notice tone="bad">{error}</Notice>}
      {lead.priority_why?.length > 0 && (
        <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          <b>Now: {PRIORITY[lead.priority].label}</b> <span className="text-xs">{lead.priority_by}</span>
          <div className="mt-1 flex flex-wrap gap-1">{lead.priority_why.map((w) => <span key={w} className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-600">{w}</span>)}</div>
        </div>
      )}
      {flag && <Notice>You can flag a lead High. Your manager can make it Urgent.</Notice>}
      <Field label="Priority *">
        <select className={fieldClass} value={level} onChange={(e) => setLevel(e.target.value)} disabled={flag}>
          {(flag ? ["high"] : Object.keys(PRIORITY)).map((k) => <option key={k} value={k}>{PRIORITY[k].label}</option>)}
        </select>
      </Field>
      <Field label="Why is it different from the suggestion?" hint="Needed when you change what the rules suggested">
        <input className={fieldClass} value={why} onChange={(e) => setWhy(e.target.value)} placeholder="For example: customer will place the order only if we reply today" />
      </Field>
      <Footer onClose={onClose}><button type="button" className={btn.primary} disabled={busy} onClick={save}>Save</button></Footer>
    </Modal>
  );
}

// ---------------- disposal ----------------
export function DisposeModal({ lead, open, onClose, onDone }) {
  const { status, has } = useSales();
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [order, setOrder] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const options = (status?.disposals || []).filter((d) => !d.crm_only);
  const picked = options.find((d) => d.key === reason);
  async function save() {
    setBusy(true);
    setError("");
    try {
      const r = await salesApi.dispose(lead.id, { reason, note, order_no: order || null });
      onDone?.(r);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onClose} title={`Dispose lead: ${lead.name}`}>
      {error && <Notice tone="bad">{error}</Notice>}
      <Notice>Choose why this lead is closed. A lead can always be reopened by your manager.</Notice>
      <Field label="Reason *">
        <select className={fieldClass} value={reason} onChange={(e) => setReason(e.target.value)}>
          <option value="">Choose the reason</option>
          {options.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
        </select>
      </Field>
      {picked && (picked.needs_review && !has("approve_disp")
        ? <Notice tone="warn">This one goes to your manager to approve before the lead is closed.</Notice>
        : <Notice tone="good">{picked.key === "won" ? "Great. The lead closes at once." : "The lead closes at once."}</Notice>)}
      <Field label="Note *" hint="A short line, at least 10 letters"><textarea className={fieldClass} rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: customer got a lower price from another brand" /></Field>
      {reason === "won" && <Field label="Order number"><input className={fieldClass} value={order} onChange={(e) => setOrder(e.target.value)} placeholder="For example GEMC-5116877231285" /></Field>}
      <Footer onClose={onClose}><button type="button" className={btn.danger} disabled={busy || !reason} onClick={save}>Dispose lead</button></Footer>
    </Modal>
  );
}

// ---------------- give ----------------
export function GiveModal({ lead, open, onClose, onDone, people }) {
  const [owner, setOwner] = useState(lead.owner_user_id || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      await salesApi.give(lead.id, owner ? Number(owner) : null);
      onDone?.();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onClose} title={`Give the lead: ${lead.name}`}>
      {error && <Notice tone="bad">{error}</Notice>}
      <Field label="Give to">
        <select className={fieldClass} value={owner} onChange={(e) => setOwner(e.target.value)}>
          <option value="">Not given to anyone</option>
          {people.map((p) => <option key={p.crm_user_id} value={p.crm_user_id}>{p.name}{p.state ? ` (${p.state})` : ""}{p.types_handled?.length ? ` · ${p.types_handled.join(", ")}` : ""}</option>)}
        </select>
      </Field>
      <Footer onClose={onClose}><button type="button" className={btn.primary} disabled={busy} onClick={save}>Save</button></Footer>
    </Modal>
  );
}
