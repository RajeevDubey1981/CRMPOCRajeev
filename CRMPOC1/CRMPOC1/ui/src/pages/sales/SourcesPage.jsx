import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import Modal from "../../components/Modal.jsx";
import { Footer } from "./LeadModals.jsx";
import { Field, Notice, PageTitle, SalesTabs, btn, errText, fieldClass, fmtDateTime, useAsync, useSales } from "./salesUi.jsx";

// What each kind of connection needs, in plain words. "pull" = Sales asks the other side every few minutes. "push" = the other side posts to our web address.
const HELP = {
  indiamart: {
    title: "IndiaMART",
    how: "Sales asks IndiaMART for new enquiries (about every 6 minutes or more, because IndiaMART allows one call every 5 minutes). Or IndiaMART posts each enquiry to the web address shown after you save (push).",
    need: "Your IndiaMART CRM key. In your IndiaMART seller login, open Lead Manager, then Import / Export Leads, then CRM integration, and copy the key. If you cannot find it, ask your IndiaMART account manager.",
  },
  meta: {
    title: "Meta lead forms (Facebook and Instagram)",
    how: "Sales reads the leads of the forms you name (every few minutes). For instant delivery you can also point a Meta webhook at the web address shown after you save.",
    need: "A page access token with permission to read leads (leads_retrieval) and the form numbers. Meta must have approved that permission for your Meta app. Please type the verify token you will also type in Meta.",
  },
  webhook: {
    title: "Web address (any form or tool that can post)",
    how: "You get a web address with a long secret in it. Paste it into any form tool, landing page, Zapier, Make or an app that can send its answers to a web address. Each answer becomes a lead.",
    need: "Nothing to log in to. Keep the address private: whoever has it can add leads.",
  },
  api: {
    title: "Any API (your own account with a marketplace or supplier)",
    how: "Sales calls the API address you give, with your key, every few minutes, reads the list of enquiries in the answer and maps its fields to ours.",
    need: "The API address, your key (a header such as Authorization or X-Api-Key), the path to the list in the answer, and which field is the name, phone and so on. Your marketplace's API guide says these.",
  },
  sheet: {
    title: "Google Sheet (published as CSV)",
    how: "Sales reads the sheet every few minutes. Each new row with a phone number becomes a lead.",
    need: "In Google Sheets: File, Share, Publish to the web, choose the sheet and CSV, and copy the address.",
  },
  mailbox: {
    title: "Mailbox (Alibaba.com, TradeWheel, TradeKey and other marketplaces that send an e-mail)",
    how: "Many marketplaces tell you about an enquiry by e-mail and give no API. Sales reads that mailbox, picks the mails from the senders you list, and reads the buyer's details out of each mail. The whole mail text stays on the lead, so check the details against it.",
    need: "A mailbox that receives the marketplace mails (IMAP address, login, password) and the sender words to look for, for example: alibaba.com, tradewheel.com. For Gmail use an app password.",
  },
};

const emptyForm = (kind) => ({
  id: null, kind, name: HELP[kind]?.title.split(" (")[0] || "", is_active: true, default_lead_type: "", default_owner_user_id: "", interval_minutes: 15,
  config: kind === "indiamart" ? { mode: "pull" } : kind === "api" ? { method: "GET" } : kind === "mailbox" ? { port: 993, folder: "INBOX" } : {},
  secret: kind === "meta" ? { verify_token: Math.random().toString(36).slice(2, 12) + Math.random().toString(36).slice(2, 8) } : {}, mappingText: "", secret_set: {},
});

function mappingToText(m) { return Object.entries(m || {}).map(([k, v]) => `${k}=${v}`).join("\n"); }
function textToMapping(t) {
  const out = {};
  (t || "").split("\n").forEach((ln) => { const i = ln.indexOf("="); if (i > 0) { const k = ln.slice(0, i).trim(), v = ln.slice(i + 1).trim(); if (k && v) out[k] = v; } });
  return out;
}

function SourceModal({ form, onClose, onSaved, people, types }) {
  const [f, setF] = useState(form);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const kind = f.kind;
  const setC = (k, v) => setF((s) => ({ ...s, config: { ...s.config, [k]: v } }));
  const setS = (k, v) => setF((s) => ({ ...s, secret: { ...s.secret, [k]: v } }));
  const pulls = kind !== "webhook";
  const keepNote = (key) => (f.secret_set?.[key] ? "A value is saved. Leave empty to keep it." : "");
  const secretInput = (key, label, type = "password", hint = "") => (
    <Field label={label} hint={[keepNote(key), hint].filter(Boolean).join(" ")}><input className={fieldClass} type={type} autoComplete="new-password" value={f.secret[key] || ""} onChange={(e) => setS(key, e.target.value)} placeholder={f.secret_set?.[key] ? "(saved)" : ""} /></Field>
  );

  async function save() {
    setBusy(true); setError("");
    try {
      const config = { ...f.config };
      if (["api", "sheet", "webhook"].includes(kind)) config.mapping = textToMapping(f.mappingText);
      const body = {
        kind, name: f.name, is_active: f.is_active, config, secret: f.secret, default_lead_type: f.default_lead_type || null,
        default_owner_user_id: f.default_owner_user_id ? Number(f.default_owner_user_id) : null, interval_minutes: Number(f.interval_minutes) || 15,
      };
      if (f.id) { delete body.kind; await salesApi.patchSource(f.id, body); } else await salesApi.addSource(body);
      onSaved();
    } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  }

  return (
    <Modal open onClose={onClose} title={`${f.id ? "Change" : "Connect"}: ${HELP[kind].title}`} maxWidth="max-w-2xl">
      {error && <Notice tone="bad">{error}</Notice>}
      <Notice><b>How it works.</b> {HELP[kind].how}<br /><b>You need.</b> {HELP[kind].need}</Notice>
      <Field label="Name of this connection"><input className={fieldClass} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      {kind === "indiamart" && (
        <>
          <Field label="How leads reach us"><select className={fieldClass} value={f.config.mode || "pull"} onChange={(e) => setC("mode", e.target.value)}><option value="pull">Sales asks IndiaMART (pull)</option><option value="push">IndiaMART posts to our web address (push)</option><option value="both">Both</option></select></Field>
          {secretInput("crm_key", "IndiaMART CRM key")}
        </>
      )}
      {kind === "meta" && (
        <>
          {secretInput("page_token", "Page access token")}
          <Field label="Form numbers" hint="One or more, separated by commas. In Meta, open the form to see its number."><input className={fieldClass} value={Array.isArray(f.config.form_ids) ? f.config.form_ids.join(", ") : f.config.form_ids || ""} onChange={(e) => setC("form_ids", e.target.value)} /></Field>
          {secretInput("verify_token", "Verify token for the webhook (you choose it; type the same in Meta)", "text")}
        </>
      )}
      {kind === "api" && (
        <>
          <div className="grid gap-x-3 sm:grid-cols-[1fr_8rem]"><Field label="Address of the API"><input className={fieldClass} value={f.config.url || ""} onChange={(e) => setC("url", e.target.value)} placeholder="https://api.example.com/inquiries" /></Field>
            <Field label="Method"><select className={fieldClass} value={f.config.method || "GET"} onChange={(e) => setC("method", e.target.value)}><option>GET</option><option>POST</option></select></Field></div>
          <div className="grid gap-x-3 sm:grid-cols-2">{secretInput("header_name", "Key header name", "text", "For example Authorization or X-Api-Key")}{secretInput("header_value", "Key header value", "password", "For example Bearer abc123")}</div>
          <Field label="Path to the list in the answer" hint="For example data.items. Leave empty if the answer is the list itself."><input className={fieldClass} value={f.config.list_path || ""} onChange={(e) => setC("list_path", e.target.value)} /></Field>
        </>
      )}
      {kind === "sheet" && <Field label="Address of the published sheet (CSV)"><input className={fieldClass} value={f.config.csv_url || ""} onChange={(e) => setC("csv_url", e.target.value)} placeholder="https://docs.google.com/spreadsheets/d/e/.../pub?output=csv" /></Field>}
      {kind === "mailbox" && (
        <>
          <div className="grid gap-x-3 sm:grid-cols-[1fr_6rem]"><Field label="Mail server (IMAP)"><input className={fieldClass} value={f.config.host || ""} onChange={(e) => setC("host", e.target.value)} placeholder="imap.gmail.com" /></Field><Field label="Port"><input className={fieldClass} value={f.config.port || 993} onChange={(e) => setC("port", e.target.value)} /></Field></div>
          <div className="grid gap-x-3 sm:grid-cols-2"><Field label="Login"><input className={fieldClass} value={f.config.user || ""} onChange={(e) => setC("user", e.target.value)} /></Field>{secretInput("password", "Password")}</div>
          <div className="grid gap-x-3 sm:grid-cols-2"><Field label="Folder"><input className={fieldClass} value={f.config.folder || "INBOX"} onChange={(e) => setC("folder", e.target.value)} /></Field><Field label="Only mails from these senders" hint="Words in the sender, separated by commas"><input className={fieldClass} value={f.config.senders || ""} onChange={(e) => setC("senders", e.target.value)} placeholder="alibaba.com, tradewheel.com" /></Field></div>
        </>
      )}
      {["api", "sheet", "webhook"].includes(kind) && (
        <Field label="Which field is which (optional)" hint="One per line, like name=buyer.name. Our fields: external_id, name, phone, email, company, message, product, city, state, country, address. Without this we guess from the names.">
          <textarea className={`${fieldClass} font-mono text-xs`} rows={4} value={f.mappingText} onChange={(e) => setF({ ...f, mappingText: e.target.value })} placeholder={"name=buyer.company\nphone=buyer.tel\ncountry=buyer.country"} />
        </Field>
      )}
      <div className="grid gap-x-3 sm:grid-cols-2">
        <Field label="Lead type for these enquiries" hint="Leave empty to let the words decide (Nepal, FOB ... make an Export lead)"><select className={fieldClass} value={f.default_lead_type || ""} onChange={(e) => setF({ ...f, default_lead_type: e.target.value })}><option value="">Decide from the words</option>{types.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</select></Field>
        <Field label="Give them to" hint="Leave empty to give by type and place"><select className={fieldClass} value={f.default_owner_user_id || ""} onChange={(e) => setF({ ...f, default_owner_user_id: e.target.value })}><option value="">By type and place (as for all leads)</option>{people.map((p) => <option key={p.crm_user_id} value={p.crm_user_id}>{p.name}</option>)}</select></Field>
        {pulls && <Field label="Ask every (minutes)"><input className={fieldClass} type="number" min="5" max="1440" value={f.interval_minutes} onChange={(e) => setF({ ...f, interval_minutes: e.target.value })} /></Field>}
        <label className="mb-3 flex items-center gap-2 self-end text-sm"><input type="checkbox" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} /> Switched on</label>
      </div>
      <Footer onClose={onClose}><button type="button" className={btn.go} disabled={busy} onClick={save}>{f.id ? "Save" : "Connect"}</button></Footer>
    </Modal>
  );
}

export default function SourcesPage() {
  const { status } = useSales();
  const { data, loading, error, reload } = useAsync(() => salesApi.sources(), []);
  const team = useAsync(() => salesApi.team(), []);
  const [modal, setModal] = useState(null);
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState(null);
  const people = (team.data || []).filter((p) => p.is_active && p.role === "sales");
  const types = status?.lead_types || [];
  const origin = typeof window !== "undefined" ? window.location.origin : "";

  async function act(id, fn, done) {
    setBusyId(id); setMsg("");
    try { const r = await fn(); setMsg(typeof done === "function" ? done(r) : done); reload(); } catch (e) { setMsg(errText(e)); } finally { setBusyId(null); }
  }
  function openEdit(s) {
    setModal({ ...emptyForm(s.kind), id: s.id, name: s.name, is_active: s.is_active, default_lead_type: s.default_lead_type || "", default_owner_user_id: s.default_owner_user_id || "", interval_minutes: s.interval_minutes, config: s.config || {}, secret: {}, secret_set: s.secret_set || {}, mappingText: mappingToText(s.config?.mapping) });
  }
  const copy = (text) => { try { navigator.clipboard.writeText(text); setMsg("Copied"); } catch { setMsg("Select the address and copy it"); } };

  return (
    <div>
      <PageTitle title="Connections" sub="Bring enquiries in from IndiaMART, Meta, marketplaces and any API or form. Each enquiry is registered in the CRM first (an IDC_ number, like a website enquiry), then becomes a lead." />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      {error && <Notice tone="bad">{error}</Notice>}
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Add a connection</h2>
      <div className="mb-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {(data?.kinds || []).map((k) => (
          <div key={k.key} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="font-semibold text-slate-800">{HELP[k.key]?.title || k.label}</div>
            <p className="mt-1 text-xs text-slate-500">{HELP[k.key]?.need}</p>
            <button type="button" className={`${btn.primary} mt-2`} onClick={() => setModal(emptyForm(k.key))}>Connect</button>
          </div>
        ))}
      </div>
      <Notice tone="warn">I did not have your accounts, so the connections are built from each company's published way of working and tested with sample answers, not with your real account. Press <b>Test</b> after you save a connection: it asks the other side what it has and makes nothing. If the other side answers differently, the error is shown here in plain words.</Notice>
      <h2 className="mb-2 mt-4 text-sm font-semibold text-slate-700">Your connections</h2>
      <div className="space-y-2">
        {(data?.items || []).map((s) => (
          <div key={s.id} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><span className="font-semibold text-slate-800">{s.name}</span> <span className="text-xs text-slate-500">{s.kind_label}</span> <span className={`ml-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${s.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"}`}>{s.is_active ? "On" : "Off"}</span></div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className={btn.plain} disabled={busyId === s.id} onClick={() => act(s.id, () => salesApi.testSource(s.id), (r) => (r.ok ? (r.message || `Works: ${r.count} enquiries are waiting. ${(r.sample || []).join(" | ")}`) : `Not working: ${r.error}`))}>Test</button>
                {s.pulls && <button type="button" className={btn.go} disabled={busyId === s.id} onClick={() => act(s.id, () => salesApi.runSource(s.id), (r) => (r.ok ? `${r.new} new lead(s), ${r.again} joined an open lead, ${r.skipped} already had, ${r.no_phone} without a phone` : `Not working: ${r.error}`))}>Fetch now</button>}
                <button type="button" className={btn.plain} onClick={() => openEdit(s)}>Change</button>
                <button type="button" className={btn.plain} onClick={() => { if (window.confirm(`Remove the connection "${s.name}"? Leads already made stay.`)) act(s.id, () => salesApi.deleteSource(s.id), "Removed"); }}>Remove</button>
              </div>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {s.received_count} enquiries received · last asked {s.last_run_at ? fmtDateTime(s.last_run_at) : "never"}{s.last_ok_at ? ` · last good ${fmtDateTime(s.last_ok_at)}` : ""}
            </div>
            {s.last_error && <div className="mt-1 rounded bg-rose-50 px-2 py-1 text-xs text-rose-700">Last problem: {s.last_error}</div>}
            {["webhook", "meta", "indiamart"].includes(s.kind) && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-slate-500">Web address for the other side to post to:</span>
                <code className="select-all break-all rounded bg-slate-100 px-2 py-1">{s.webhook_url || origin + s.webhook_path}</code>
                <button type="button" className={btn.plain} onClick={() => copy(s.webhook_url || origin + s.webhook_path)}>Copy</button>
                <button type="button" className="text-rose-600 hover:underline" onClick={() => { if (window.confirm("The old address stops working at once. Make a new one?")) act(s.id, () => salesApi.newToken(s.id), "A new address was made. Give it to the other side.") }}>Make a new address</button>
              </div>
            )}
          </div>
        ))}
        {!loading && (data?.items || []).length === 0 && <p className="text-sm text-slate-500">No connection yet. Press Connect on one of the boxes above.</p>}
      </div>
      {modal && <SourceModal form={modal} people={people} types={types} onClose={() => setModal(null)} onSaved={() => { setModal(null); setMsg("Saved. Press Test to check it."); reload(); }} />}
    </div>
  );
}
