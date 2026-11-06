import { useMemo, useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { HeroArt } from "./marketingArt.jsx";
import { CountUp, Icon, MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, greeting, useAsync, useMarketing } from "./marketingUi.jsx";

const STATUS_LABEL = {
  draft: ["Draft", "bg-slate-100 text-slate-600"],
  wait: ["Waiting for approval", "bg-amber-100 text-amber-800 s-urgent"],
  appr: ["Approved", "bg-sky-100 text-sky-800"],
  sent: ["Sent", "bg-emerald-100 text-emerald-800"],
  rejected: ["Rejected", "bg-rose-100 text-rose-800"],
  cancelled: ["Cancelled", "bg-slate-100 text-slate-500"],
};

const EMPTY = { name: "", audience_id: "", send_to_all: false, image_path: null, subject: "", body: "" };

function EmailPreview({ form }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      {form.image_path && <img src={form.image_path} alt="Banner" className="block w-full" />}
      <div className="bg-white p-3.5">
        <div className="mb-1.5 border-b border-slate-100 pb-1.5 text-xs text-slate-400">
          <div><b className="text-slate-600">Subject:</b> {form.subject || <span className="italic text-slate-300">(no subject yet)</span>}</div>
        </div>
        <div className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700">
          {(form.body || "Hi {{name}},\n\n...").replace(/\{\{name\}\}/g, "Rohit")}
        </div>
      </div>
    </div>
  );
}

function Form({ audiences, canAll, initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");
  const guide = useAsync(() => marketingApi.campaignImageGuide(), []);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function pickImage(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true); setMsg("");
    try {
      const r = await marketingApi.uploadCampaignImage(file);
      setForm((f) => ({ ...f, image_path: r.image_path }));
    } catch (err) { setMsg(errText(err)); } finally { setUploading(false); e.target.value = ""; }
  }

  async function save() {
    if (!form.name.trim() || (!form.send_to_all && !form.audience_id) || !form.subject.trim() || !form.body.trim()) {
      setMsg("Name, a target (audience or Everyone), subject and message are all required.");
      return;
    }
    setBusy(true); setMsg("");
    try {
      const body = { ...form, audience_id: form.send_to_all ? null : Number(form.audience_id) };
      if (form.id) await marketingApi.updateCampaign(form.id, body);
      else await marketingApi.createCampaign(body);
      onSaved();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div className="s-rise s-pop mb-4 rounded-xl border border-violet-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-violet-100 text-violet-700"><Icon name="chat" size={14} /></span>
        {form.id ? "Edit draft" : "New campaign"}
      </h3>
      {msg && <Notice tone="bad">{msg}</Notice>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm text-slate-600">Campaign name
          <input className={fieldClass} value={form.name} onChange={set("name")} placeholder="GeM — festive follow-up" />
        </label>
        <label className="text-sm text-slate-600">Send to
          <select
            className={fieldClass}
            value={form.send_to_all ? "all" : "audience"}
            onChange={(e) => setForm((f) => ({ ...f, send_to_all: e.target.value === "all" }))}
          >
            <option value="audience">A saved audience</option>
            {canAll && <option value="all">Everyone (all CRM contacts with an email)</option>}
          </select>
        </label>
        {!form.send_to_all && (
          <label className="text-sm text-slate-600 md:col-span-2">Audience
            <select className={fieldClass} value={form.audience_id} onChange={set("audience_id")}>
              <option value="">— Select a saved audience —</option>
              {audiences.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.count})</option>)}
            </select>
          </label>
        )}
        <label className="text-sm text-slate-600 md:col-span-2">Subject
          <input className={fieldClass} value={form.subject} onChange={set("subject")} />
        </label>
        <label className="text-sm text-slate-600 md:col-span-2">Message
          <textarea className={fieldClass} rows={6} value={form.body} onChange={set("body")} placeholder={"Hi {{name}},\n\n..."} />
          <span className="mt-1 block text-xs text-slate-400">Use {"{{name}}"} to greet each person by name. Email only, for now.</span>
        </label>
      </div>

      <div className="mt-4 rounded-lg border border-dashed border-slate-300 p-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Hero banner image (optional)</div>
        <p className="mb-2 text-xs text-slate-500">
          Recommended size: <b>{guide.data?.recommended_size || "1200 x 600 px"}</b>. Format: <b>{(guide.data?.formats || ["JPG", "PNG"]).join(" or ")}</b>, under <b>{guide.data?.max_size_mb ?? 3}MB</b>.
          {" "}Shown at the top of the email, above your message.
        </p>
        <div className="flex items-center gap-2">
          <input type="file" accept="image/jpeg,image/png" onChange={pickImage} disabled={uploading} className="text-sm" />
          {uploading && <span className="text-xs text-slate-500">Uploading...</span>}
          {form.image_path && <button type="button" className={btn.plain} onClick={() => setForm((f) => ({ ...f, image_path: null }))}>Remove image</button>}
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Email preview</div>
        <EmailPreview form={form} />
      </div>

      <div className="mt-3 flex gap-2">
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>{form.id ? "Save draft" : "Create draft"}</button>
        <button type="button" className={btn.plain} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function ProgressBar({ sent, skipped, total }) {
  if (!total) return null;
  const sentPct = Math.round((sent / total) * 100);
  return (
    <div className="mt-3">
      <div className="mb-1 flex justify-between text-[11px] text-slate-500"><span>{sent} sent</span><span>{skipped} skipped · {total} total</span></div>
      <div className="flex h-2 overflow-hidden rounded-full bg-slate-100">
        <span className="s-grow h-full bg-emerald-500" style={{ "--i": 0, width: `${sentPct}%` }} />
        <span className="s-grow h-full bg-slate-300" style={{ "--i": 1, width: `${100 - sentPct}%` }} />
      </div>
    </div>
  );
}

const RESULT_LABEL = { sent: ["Delivered", "bg-emerald-100 text-emerald-700"], stopped: ["On STOP list", "bg-rose-100 text-rose-700"], cooldown: ["Cooldown", "bg-amber-100 text-amber-700"], no_email: ["No email", "bg-slate-100 text-slate-500"], failed: ["Failed", "bg-rose-100 text-rose-700"] };

function CampaignCard({ c, i, canApprove, onChanged }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const detail = useAsync(() => (open ? marketingApi.campaign(c.id) : Promise.resolve(null)), [open, c.id]);
  const [label, cls] = STATUS_LABEL[c.status] || [c.status, "bg-slate-100 text-slate-600"];

  async function act(fn) {
    setBusy(true); setMsg("");
    try { await fn(); onChanged(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div style={{ "--i": i }} className="s-rise s-lift rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-violet-100 text-violet-700"><Icon name="mail" size={16} /></span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-slate-800">{c.name}</span>
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${cls}`}>{label}</span>
            </div>
            <div className="text-xs text-slate-500">{c.audience_name || "—"} · {c.subject}</div>
          </div>
        </div>
        <button type="button" className={btn.plain} onClick={() => setOpen((v) => !v)}>{open ? "Hide" : "Details"}</button>
      </div>

      {c.status === "sent" && <ProgressBar sent={c.sent_count} skipped={c.skipped_count} total={c.total_count} />}
      {c.status === "wait" && !canApprove && (
        <p className="mt-2 text-xs text-slate-500">{c.total_count} people — over the no-approval limit. Waiting for a Marketing manager to approve.</p>
      )}

      {msg && <div className="mt-2"><Notice tone="bad">{msg}</Notice></div>}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {(c.status === "draft" || c.status === "rejected") && (
          <button type="button" className={btn.primary} disabled={busy} onClick={() => act(() => marketingApi.submitCampaign(c.id))}>
            {busy ? "Submitting..." : c.status === "rejected" ? "Resubmit" : "Submit / Send"}
          </button>
        )}
        {c.status === "wait" && canApprove && (
          <>
            <button type="button" className={btn.primary} disabled={busy} onClick={() => act(() => marketingApi.approveCampaign(c.id))}>Approve & send</button>
            <input className={`${fieldClass} w-auto`} placeholder="Reason to reject (optional)" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
            <button type="button" className={btn.plain} disabled={busy} onClick={() => act(() => marketingApi.rejectCampaign(c.id, rejectReason))}>Reject</button>
          </>
        )}
        {(c.status === "draft" || c.status === "rejected") && (
          <button type="button" className={btn.plain} disabled={busy} onClick={() => act(() => marketingApi.deleteCampaign(c.id))}>Delete</button>
        )}
      </div>

      {open && (
        <div className="s-pop mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          {c.image_path && <img src={c.image_path} alt="" className="mb-2 w-full rounded border border-slate-200" />}
          <pre className="whitespace-pre-wrap text-xs text-slate-700">{c.body}</pre>
          {detail.data?.logs && (
            <div className="mt-3 max-h-56 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="text-left text-slate-400"><tr><th className="pb-1">Contact</th><th className="pb-1">Address</th><th className="pb-1">Result</th></tr></thead>
                <tbody>
                  {detail.data.logs.map((l, li) => {
                    const [rl, rc] = RESULT_LABEL[l.result] || [l.result, "bg-slate-100 text-slate-500"];
                    return (
                      <tr key={li} className="border-t border-slate-200">
                        <td className="py-1.5">{l.contact || "—"}</td>
                        <td className="py-1.5">{l.address || "—"}</td>
                        <td className="py-1.5"><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${rc}`}>{rl}</span></td>
                      </tr>
                    );
                  })}
                  {detail.data.logs.length === 0 && <tr><td colSpan={3} className="py-2 text-slate-400">Nobody logged yet.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmptyState({ onNew, canCreate }) {
  const steps = [["users", "Audience"], ["chat", "Message"], ["mail", "Send"]];
  return (
    <div className="s-rise s-pop rounded-2xl border border-dashed border-violet-200 bg-white px-6 py-12 text-center">
      <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-full bg-violet-100 text-violet-600">
        <Icon name="chat" size={26} />
      </div>
      <h3 className="text-base font-semibold text-slate-800">No campaigns yet</h3>
      <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">Build an audience, write a message, and send — each step logged, each contact reached once.</p>
      <div className="mx-auto mt-6 flex max-w-sm items-center justify-center">
        {steps.map(([icon, label], i) => (
          <div key={label} className="flex items-center">
            {i > 0 && <span className="mx-1 h-px w-10 bg-violet-200" />}
            <div style={{ "--i": i }} className="s-pop flex flex-col items-center gap-1.5">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-violet-100 text-violet-700"><Icon name={icon} size={16} /></span>
              <span className="text-[11px] font-semibold text-slate-500">{label}</span>
            </div>
          </div>
        ))}
      </div>
      <button type="button" className={`${btn.primary} mt-7`} disabled={!canCreate} onClick={onNew}>+ New campaign</button>
      {!canCreate && <p className="mt-1 text-xs text-slate-400">Save an audience first, under Audiences.</p>}
    </div>
  );
}

export default function MarketingCampaigns() {
  const { has } = useMarketing();
  const list = useAsync(() => marketingApi.campaigns(), []);
  const audiences = useAsync(() => marketingApi.audiences(), []);
  const [editing, setEditing] = useState(null);

  const canApprove = has("approve");
  const canAll = has("aud_all");
  const canCreate = canAll || !!(audiences.data || []).length;
  const campaigns = list.data || [];

  const stats = useMemo(() => {
    const sent = campaigns.filter((c) => c.status === "sent");
    return {
      total: campaigns.length,
      sentCount: sent.reduce((n, c) => n + (c.sent_count || 0), 0),
      waiting: campaigns.filter((c) => c.status === "wait").length,
      peopleInAudiences: (audiences.data || []).reduce((n, a) => n + (a.count || 0), 0),
    };
  }, [campaigns, audiences.data]);

  const tiles = [
    [stats.total, "Campaigns", "chat", "#7c3aed"],
    [stats.sentCount, "Messages sent", "mail", "#059669"],
    [stats.waiting, "Waiting for approval", "bell", "#d97706"],
    [stats.peopleInAudiences, "People in saved audiences", "users", "#2f5bb5"],
  ];

  return (
    <div>
      <PageTitle title="Campaigns" sub="Send a message to a saved audience's contacts. Each contact is logged once, and skipped if they're on the STOP list or were messaged recently." />
      <MarketingTabs />

      <div className="s-hero mk-hero s-rise mb-4 flex items-center justify-between gap-4 rounded-xl p-5 shadow-sm">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-white/70">{greeting()}</div>
          <div className="text-2xl font-semibold">Reach your audiences</div>
          <div className="mt-1 text-sm text-white/80">Pick a saved audience, write the message, and send — approval kicks in automatically above the limit.</div>
        </div>
        <HeroArt />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {tiles.map(([value, label, icon, color], i) => (
          <div key={label} style={{ "--i": i }} className="s-rise s-lift relative overflow-hidden rounded-lg border border-slate-200 bg-white p-3.5">
            <span style={{ "--i": i, background: color }} className="s-grow absolute inset-x-0 top-0 h-1.5" />
            <div className="flex items-start justify-between gap-2">
              <div className="text-2xl font-semibold tabular-nums text-slate-800"><CountUp value={value} /></div>
              <span style={{ background: `${color}22`, color }} className="grid h-8 w-8 shrink-0 place-items-center rounded-full"><Icon name={icon} size={16} /></span>
            </div>
            <div className="mt-1 text-xs font-medium text-slate-600">{label}</div>
          </div>
        ))}
      </div>

      {list.error && <Notice tone="bad">{list.error}</Notice>}

      {editing ? (
        <Form audiences={audiences.data || []} canAll={canAll} initial={editing} onSaved={() => { setEditing(null); list.reload(); }} onCancel={() => setEditing(null)} />
      ) : (
        <div className="mb-4">
          <button type="button" className={btn.primary} onClick={() => setEditing({ ...EMPTY })} disabled={!canCreate}>+ New campaign</button>
          {!canCreate && <p className="mt-1 text-xs text-slate-500">Save an audience first, under Audiences.</p>}
        </div>
      )}

      {!editing && !list.loading && campaigns.length === 0 ? (
        <EmptyState onNew={() => setEditing({ ...EMPTY })} canCreate={canCreate} />
      ) : (
        <div className="grid gap-3">
          {campaigns.map((c, i) => <CampaignCard key={c.id} c={c} i={i} canApprove={canApprove} onChanged={list.reload} />)}
        </div>
      )}
    </div>
  );
}
