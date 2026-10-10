import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { salesApi } from "../../api/sales.js";
import Modal from "../../components/Modal.jsx";
import { CallModal, DisposeModal, Footer, GiveModal, PriorityModal, StageModal } from "./LeadModals.jsx";
import { waLink } from "./MyDay.jsx";
import {
  AttendedChip, FirstCallChip, HEAT, HeatChip, Icon, Notice, PRIORITY, PageTitle, PriorityChip, QUOTE_TONE, STAGES, SalesTabs, StatusChip, TypeChip, btn, errText,
  fieldClass, fmtDate, fmtDateTime, useAsync, useSales, valueText,
} from "./salesUi.jsx";

const EXPORT_COUNTRIES = {
  Nepal: { cur: "NPR", tz: "Asia/Kathmandu", diff: "15 minutes ahead of India", route: "By road to Birgunj (through Raxaul), or by sea to Kolkata and then road", chk: "Landlocked, so the price is usually DAP Birgunj. Check the Nepal Bureau of Standards rules for appliances." },
  Kenya: { cur: "KES", tz: "Africa/Nairobi", diff: "2 h 30 min behind India", route: "By sea to Mombasa", chk: "Regulated goods may need a pre-export conformity certificate (PVoC) from an agent appointed by KEBS. Check if air conditioners are covered." },
  Ghana: { cur: "GHS", tz: "Africa/Accra", diff: "5 h 30 min behind India", route: "By sea to Tema", chk: "Air conditioners may need to meet the Energy Commission efficiency and label rules. Check with the buyer's clearing agent." },
  "Sri Lanka": { cur: "LKR", tz: "Asia/Colombo", diff: "Same time as India", route: "By sea to Colombo", chk: "Imported appliances may need to meet Sri Lanka Standards Institution rules. Check refrigerant and energy rules with the buyer." },
};

export function localTime(tz) {
  const d = new Date();
  return {
    text: d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: tz }),
    hour: Number(d.toLocaleString("en-GB", { hour: "2-digit", hour12: false, timeZone: tz })),
  };
}

function ExportBox({ lead }) {
  const country = lead.country || (lead.place || "").split(",").pop().trim();
  const m = EXPORT_COUNTRIES[country];
  if (!m) return <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4"><h3 className="text-sm font-semibold">Export lead</h3><p className="text-sm text-slate-600">Country: <b>{country || "not given"}</b>. This is not one of the four first countries, so the manager decides whether we sell there.</p></section>;
  const t = localTime(m.tz);
  const ok = t.hour >= 9 && t.hour < 18;
  return (
    <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800">Export details</h3>
      <p className="mt-1 text-sm text-slate-700"><b>Country:</b> {country} · <b>their currency:</b> {m.cur} · <b>we quote in:</b> US dollars</p>
      <p className="text-sm text-slate-700"><b>Price basis:</b> {lead.price_basis || "not asked yet"} · <b>route:</b> {m.route}</p>
      <p className="text-sm text-slate-700"><b>Time there now:</b> {t.text} ({m.diff}) <span className={`ml-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{ok ? "Good time to call" : "Outside their office hours: send a WhatsApp or mail first"}</span></p>
      <p className="mt-1 text-xs text-slate-500"><b>To check (not confirmed here):</b> {m.chk}</p>
    </section>
  );
}

function PartnerPanel({ lead, data, can, reload }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  const p = data;
  if (!p) return null;
  const idx = p.steps.indexOf(p.onboarding_status);
  const req = p.papers.filter((i) => i.required);
  const done = p.required_done;
  const closed = lead.closed;

  async function act(fn, ok) {
    setBusy(true);
    setMsg("");
    try { await fn(); setMsg(ok); reload(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  return (
    <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800">Partner registration {p.registration_no} <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">{p.partner_type}</span> <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">{p.business_type}</span></h3>
      <p className="text-xs text-slate-500">Everything here is read from the CRM each time this page opens. Sales keeps no copy of the papers.</p>
      <div className="mt-2 flex flex-wrap items-center gap-1 text-[11px] font-semibold">
        {p.steps.map((s, i) => {
          const state = p.onboarding_status === "Rejected" ? (i < 2 ? "done" : "todo") : p.onboarding_status === "Cancelled" ? (i < 1 ? "done" : "todo") : i < idx ? "done" : i === idx ? "now" : "todo";
          return <span key={s} className={`rounded-full px-2 py-0.5 ${state === "done" ? "bg-emerald-100 text-emerald-800" : state === "now" ? "bg-sky-200 text-sky-900" : "bg-slate-100 text-slate-500"}`}>{s}</span>;
        })}
      </div>
      {p.onboarding_status === "Rejected" && <Notice tone="warn"><b>Rejected in the CRM</b>, sent back to the partner. {p.admin_remark} The partner can correct it and submit again, so the lead stays open.</Notice>}
      {p.onboarding_status === "Cancelled" && <Notice tone="warn"><b>Cancelled in the CRM.</b> {p.admin_remark}</Notice>}
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        <div>
          <div className="text-sm font-semibold">Required papers: {done} of {req.length}</div>
          <div className="my-1 h-2 overflow-hidden rounded bg-slate-200"><div className="h-full bg-emerald-600" style={{ width: `${req.length ? Math.round((done * 100) / req.length) : 0}%` }} /></div>
          <ul className="text-sm">
            {p.papers.map((i) => (
              <li key={i.key} className={i.ok ? "text-emerald-700" : i.required ? "text-rose-700" : "text-slate-500"}>
                {i.ok ? "✓" : i.required ? "✗" : "○"} {i.label}{i.note ? <span className="text-xs text-slate-500"> · {i.note}</span> : null}{!i.required && <span className="text-xs text-slate-500"> · optional</span>}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-sm font-semibold">What you can do</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link className={btn.primary} to="/partner-registrations">Open the registrations in the CRM</Link>
            {can.remind && <button type="button" className={btn.plain} disabled={busy || closed || p.reminder_used} onClick={() => act(() => salesApi.remind(lead.id), "Reminder sent through the CRM mail")}>Remind the partner about missing papers</button>}
            {can.cancel_request && !closed && <button type="button" className={btn.plain} onClick={() => setAsking(true)}>Ask the partner admin to cancel</button>}
          </div>
          <p className="mt-2 text-xs text-slate-500">The reminder uses the CRM's own mail. The CRM allows <b>one</b> resend per registration{p.reminder_used ? " (already used: call the partner instead)" : ""}.</p>
          <Notice>Disposal is done in the CRM. Approve, reject or cancel are done by the people who have the partner right there. This lead follows what they decide.</Notice>
          {msg && <p className="text-sm text-slate-700">{msg}</p>}
        </div>
      </div>
      <Modal open={asking} onClose={() => setAsking(false)} title="Ask the partner admin to cancel">
        <p className="mb-2 text-sm text-slate-600">If the partner says they are not interested, the partner admin gets a card in their login popup and cancels it in the CRM. The lead then closes by itself.</p>
        <input className={fieldClass} placeholder="What the partner said (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
        <Footer onClose={() => setAsking(false)}><button type="button" className={btn.danger} onClick={() => { setAsking(false); act(() => salesApi.cancelRequest(lead.id, reason), "The partner admin was told"); }}>Send the request</button></Footer>
      </Modal>
    </section>
  );
}

// The workflow of a lead: where it is, whether its owner has attended it, and the quick things a person does about it.
function WorkflowPanel({ lead, can, busy, quick, moveTo, logCall }) {
  const partner = lead.crm_kind === "partner";
  const idx = STAGES.findIndex(([k]) => k === lead.status);
  const ended = lead.closed;
  const acting = can.work && !ended;
  return (
    <section className="s-fade mb-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Workflow</h3>
        <AttendedChip lead={lead} />
        {lead.attended && !ended && <span className="text-xs text-slate-500">last action {fmtDateTime(lead.last_action_at)} · {lead.attempts} call{lead.attempts === 1 ? "" : "s"}</span>}
        {!lead.attended && !ended && lead.owner_name && <span className="text-xs text-slate-500">{lead.owner_name} has not acted on it yet</span>}
        {!lead.owner_user_id && !ended && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Not given to anyone yet</span>}
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="s-bar h-full rounded-full bg-indcool-blue" style={{ width: `${ended ? 100 : Math.max(0, idx) / STAGES.length * 100 + (idx >= 0 ? 100 / STAGES.length / 2 : 0)}%` }} /></div>
      <ol className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-6">
        {STAGES.map(([key, label], i) => {
          const done = idx > i || (ended && lead.status === "won");
          const now = idx === i && !ended;
          const canMove = acting && !partner && key !== "new" && !now;
          const tone = now ? "border-indcool-blue bg-sky-50 text-indcool-navy ring-1 ring-indcool-blue" : done ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-white text-slate-400";
          return (
            <li key={key}>
              <button type="button" disabled={!canMove || busy} onClick={() => moveTo(key, label)} className={`s-press s-cell w-full rounded-md border px-2 py-1.5 text-left text-xs ${tone} ${canMove ? "cursor-pointer hover:border-indcool-blue" : "cursor-default"}`}>
                <div className="font-semibold">{done ? <Icon name="check" size={12} className="mr-1 -mt-0.5" /> : `${i + 1}. `}{label}</div>
                <div className="text-[10px] font-normal">{now ? "the lead is here" : canMove ? "press to move here" : ""}</div>
              </button>
            </li>
          );
        })}
        <li>
          <div className={`rounded-md border px-2 py-1.5 text-xs ${ended ? (lead.status === "won" ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-400 bg-slate-200 text-slate-700") : "border-slate-200 bg-white text-slate-400"}`}>
            <div className="font-semibold">{ended ? (lead.status === "won" ? "Won" : lead.status === "rev" ? "Waiting for the manager" : "Closed") : "Won or closed"}</div>
            <div className="text-[10px] font-normal">{ended ? "" : "the end of the workflow"}</div>
          </div>
        </li>
      </ol>
      {partner && !ended && <p className="mt-2 text-xs text-slate-500">This lead follows its partner registration in the CRM, so its stage is set there. You can still log calls and notes.</p>}
      {acting && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-semibold text-slate-600">What did you do? One press marks the lead as attended and writes it in the history.</div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={btn.go} disabled={busy} onClick={logCall}><Icon name="phone" size={14} className="mr-1.5 -mt-0.5" />Called and spoke</button>
            <button type="button" className={btn.plain} disabled={busy} onClick={() => quick("No answer", "Marked: called, no answer. Follow-up set for tomorrow.")}><Icon name="phoneOff" size={14} className="mr-1.5 -mt-0.5" />Called, no answer</button>
            <button type="button" className={btn.plain} disabled={busy} onClick={() => quick("Sent a WhatsApp", "Marked: WhatsApp sent")}><Icon name="chat" size={14} className="mr-1.5 -mt-0.5" />WhatsApp sent</button>
            <button type="button" className={btn.plain} disabled={busy} onClick={() => quick("Sent a mail", "Marked: mail sent")}><Icon name="mail" size={14} className="mr-1.5 -mt-0.5" />Mail sent</button>
            <button type="button" className={btn.plain} disabled={busy} onClick={() => quick("Visit done", "Marked: visit done")}><Icon name="pin" size={14} className="mr-1.5 -mt-0.5" />Visit done</button>
          </div>
          {lead.attempts >= 4 && !lead.is_prospect && <p className="mt-2 text-xs text-amber-700">{lead.attempts} attempts so far. After 5 with no answer you can dispose the lead as "Not reachable".</p>}
        </div>
      )}
    </section>
  );
}

export default function LeadDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { has } = useSales();
  const { data: lead, loading, error, reload } = useAsync(() => salesApi.lead(id), [id]);
  const team = useAsync(() => (has("give") ? salesApi.team() : Promise.resolve([])), [has("give")]);
  const [modal, setModal] = useState("");
  const [stageTo, setStageTo] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const people = (team.data || []).filter((p) => p.is_active && (p.role || "").trim().toLowerCase() === "sales");

  if (error) return <div><SalesTabs /><Notice tone="bad">{error}</Notice></div>;
  if (!lead) return <div><SalesTabs />{loading && <p className="text-sm text-slate-500">Loading...</p>}</div>;
  const c = lead.can;
  const done = () => { setModal(""); setMsg(""); reload(); };

  async function run(fn, ok) {
    setBusy(true);
    setMsg("");
    try { const r = await fn(); setMsg(typeof ok === "function" ? ok(r) : ok); reload(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  async function makeQuote() {
    setBusy(true);
    try { const q = await salesApi.makeQuotation(lead.id, {}); nav(`/sales/quotations/${q.id}`); } catch (e) { setMsg(errText(e)); setBusy(false); }
  }

  return (
    <div>
      <PageTitle title={lead.name} sub={`${lead.lead_no || ""} · ${lead.lead_type_label}`} right={<StatusChip status={lead.status} />} />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      {lead.asked_again_at && !lead.closed && <Notice tone="warn">This customer asked again on {fmtDateTime(lead.asked_again_at)}. See the history.</Notice>}
      <WorkflowPanel lead={lead} can={c} busy={busy} quick={(outcome, ok) => run(() => salesApi.call(lead.id, { outcome, note: "" }), ok)} moveTo={(key, label) => setStageTo({ key, label })} logCall={() => setModal("call")} />
      <div className="grid gap-3 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">The lead</h3>
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
            <dt className="text-slate-500">Type</dt><dd><TypeChip lead={lead} /></dd>
            <dt className="text-slate-500">Priority</dt><dd>{lead.closed ? "—" : <><PriorityChip lead={lead} always /> <span className="text-xs text-slate-500">{lead.priority_by}</span><div className="mt-1 flex flex-wrap gap-1">{lead.priority_why.map((w) => <span key={w} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{w}</span>)}</div></>}</dd>
            <dt className="text-slate-500">Heat</dt><dd>{lead.closed ? "—" : <><HeatChip lead={lead} /> <span className="text-xs text-slate-500">{lead.heat_by}</span><div className="mt-1 flex flex-wrap gap-1">{lead.heat_why.map((w) => <span key={w} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{w}</span>)}</div></>}</dd>
            <dt className="text-slate-500">Value</dt><dd>{valueText(lead)}{lead.closes_on ? ` · closes ${fmtDate(lead.closes_on)}` : ""}</dd>
            <dt className="text-slate-500">Wants</dt><dd>{lead.item || "—"}</dd>
            {lead.details && <><dt className="text-slate-500">Details</dt><dd>{lead.details}</dd></>}
            <dt className="text-slate-500">Phone</dt><dd><a className="text-indcool-blue hover:underline" href={`tel:${lead.phone}`}>{lead.phone}</a>{lead.email ? ` · ${lead.email}` : ""}</dd>
            <dt className="text-slate-500">Place</dt><dd>{[...new Set([lead.place, lead.district, lead.state, lead.country].filter(Boolean).flatMap((x) => x.split(",").map((y) => y.trim())))].join(", ") || "—"}{lead.pincode ? ` (${lead.pincode})` : ""}</dd>
            <dt className="text-slate-500">Source</dt><dd>{lead.source}{lead.crm_ref ? ` · registered in the CRM as ${lead.crm_ref}` : ""}</dd>
            <dt className="text-slate-500">Owner</dt><dd>{lead.owner_name || "Not given to anyone yet"}</dd>
            <dt className="text-slate-500">Next follow-up</dt><dd className={lead.follow_up_late ? "font-semibold text-rose-600" : ""}>{lead.follow_up_on ? fmtDate(lead.follow_up_on) : "—"}</dd>
            <dt className="text-slate-500">First call</dt><dd>{lead.first_called ? "Done" : lead.status === "new" ? <FirstCallChip lead={lead} /> : "Not called yet"}</dd>
          </dl>
          {lead.message && <p className="mt-2 rounded bg-slate-50 p-2 text-sm italic text-slate-600">"{lead.message}"</p>}
          {lead.closed || lead.status === "rev" ? (
            <div className={`mt-3 rounded border px-3 py-2 text-sm ${lead.status === "won" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
              {lead.status === "rev" ? "Waiting for the manager to approve: " : "Closed: "}<b>{(lead.disposal_reason && (status_label(lead))) || "Disposed"}</b>. {lead.disposal_note}{lead.order_no ? ` Order ${lead.order_no}.` : ""}
              {lead.crm_close_pending && <div className="text-xs">The CRM has not taken the close yet. It will be sent again.</div>}
              <div className="mt-2 flex flex-wrap gap-2">
                {lead.status === "rev" && c.approve_disposal && <button type="button" className={btn.go} disabled={busy} onClick={() => run(() => salesApi.approveDisposal(lead.id), "Approved: the lead is closed")}>Approve the disposal</button>}
                {c.approve_disposal && lead.crm_kind !== "partner" && <button type="button" className={btn.plain} disabled={busy} onClick={() => run(() => salesApi.reopen(lead.id), "Reopened")}>Reopen</button>}
              </div>
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2">
              <a className={btn.go} href={`tel:${lead.phone}`}>Call</a>
              <a className={btn.plain} href={waLink(lead.phone)} target="_blank" rel="noreferrer">WhatsApp</a>
              {c.work && <button type="button" className={btn.primary} onClick={() => setModal("call")}>Log call</button>}
              {c.rate && <button type="button" className={btn.plain} onClick={() => setModal("rate")}>Rate the lead</button>}
              {c.flag && !c.set_priority && <button type="button" className={btn.plain} onClick={() => setModal("flag")}>Flag high</button>}
              {c.set_priority && <button type="button" className={btn.plain} onClick={() => setModal("priority")}>Set priority</button>}
              {c.give && <button type="button" className={btn.plain} onClick={() => setModal("give")}>Give to...</button>}
              {c.quote && <button type="button" className={btn.plain} disabled={busy} onClick={makeQuote}>Make a quotation</button>}
              {c.dispose && (lead.crm_kind === "partner"
                ? <span className="self-center text-xs text-slate-500">Disposal is done in the CRM for this lead</span>
                : <button type="button" className={btn.danger} onClick={() => setModal("dispose")}>Dispose this lead</button>)}
            </div>
          )}
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">History</h3>
          <ol className="max-h-[28rem] space-y-2 overflow-y-auto border-l-2 border-slate-200 pl-3">
            {lead.activities.map((a) => (
              <li key={a.id} className="text-sm"><span className={a.kind === "call" ? "font-medium text-slate-800" : "text-slate-700"}>{a.text}</span><div className="text-xs text-slate-400">{fmtDateTime(a.at)} · {a.by}</div></li>
            ))}
          </ol>
        </section>
      </div>
      {lead.crm_kind === "partner" && <PartnerPanel lead={lead} data={lead.partner} can={{ remind: c.remind, cancel_request: c.cancel_request }} reload={reload} />}
      {lead.lead_type === "export" && <ExportBox lead={lead} />}
      {lead.quotations.length > 0 && (
        <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Quotations</h3>
          <ul className="divide-y divide-slate-100 text-sm">
            {lead.quotations.map((q) => (
              <li key={q.id} className="flex flex-wrap items-center justify-between gap-2 py-1.5"><Link to={`/sales/quotations/${q.id}`} className="font-semibold text-indcool-navy hover:underline">{q.quote_no}</Link><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${QUOTE_TONE[q.status]}`}>{q.status_label}</span><span className="tabular-nums">{q.currency === "USD" ? "US$" : "₹"} {q.total.toLocaleString("en-IN")}</span></li>
            ))}
          </ul>
        </section>
      )}
      {stageTo && <StageModal open lead={lead} stage={stageTo.key} label={stageTo.label} onClose={() => setStageTo(null)} onDone={() => { setStageTo(null); setMsg(""); reload(); }} />}
      {modal === "call" && <CallModal open lead={lead} onClose={() => setModal("")} onDone={done} />}
      {modal === "rate" && <CallModal open rateOnly lead={lead} onClose={() => setModal("")} onDone={done} />}
      {(modal === "priority" || modal === "flag") && <PriorityModal open flag={modal === "flag"} lead={lead} onClose={() => setModal("")} onDone={done} />}
      {modal === "dispose" && <DisposeModal open lead={lead} onClose={() => setModal("")} onDone={(r) => { setModal(""); setMsg(r.status === "rev" ? "Sent to the manager to approve" : "Lead closed"); reload(); }} />}
      {modal === "give" && <GiveModal open lead={lead} people={people} onClose={() => setModal("")} onDone={done} />}
    </div>
  );
}

function status_label(lead) {
  const labels = {
    won: "Won: order confirmed", lost_price: "Lost: price too high", lost_brand: "Lost: chose another brand", lost_cancel: "Lost: project cancelled or no budget",
    noint: "Not interested", wrong: "Wrong number", dup: "Duplicate lead", fake: "Invalid or fake enquiry", unreach: "Not reachable after 5 attempts",
    pr_won: "Won: partner approved in the CRM", pr_can: "Not interested: registration cancelled in the CRM",
  };
  return labels[lead.disposal_reason] || lead.disposal_reason;
}
