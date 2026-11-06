import { useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useAsync, useMarketing } from "./marketingUi.jsx";

const STATUS_LABEL = {
  draft: ["Draft", "bg-slate-100 text-slate-600"],
  wait: ["Waiting for approval", "bg-amber-100 text-amber-800"],
  appr: ["Approved", "bg-sky-100 text-sky-800"],
  sent: ["Sent", "bg-emerald-100 text-emerald-800"],
  rejected: ["Rejected", "bg-rose-100 text-rose-800"],
  cancelled: ["Cancelled", "bg-slate-100 text-slate-500"],
};

const EMPTY = { name: "", audience_id: "", subject: "", body: "" };

function Form({ audiences, initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function save() {
    if (!form.name.trim() || !form.audience_id || !form.subject.trim() || !form.body.trim()) {
      setMsg("Name, audience, subject and message are all required.");
      return;
    }
    setBusy(true); setMsg("");
    try {
      const body = { ...form, audience_id: Number(form.audience_id) };
      if (form.id) await marketingApi.updateCampaign(form.id, body);
      else await marketingApi.createCampaign(body);
      onSaved();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-800">{form.id ? "Edit draft" : "New campaign"}</h3>
      {msg && <Notice tone="bad">{msg}</Notice>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm text-slate-600">Campaign name
          <input className={fieldClass} value={form.name} onChange={set("name")} placeholder="GeM — festive follow-up" />
        </label>
        <label className="text-sm text-slate-600">Audience
          <select className={fieldClass} value={form.audience_id} onChange={set("audience_id")}>
            <option value="">— Select a saved audience —</option>
            {audiences.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.count})</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-600 md:col-span-2">Subject
          <input className={fieldClass} value={form.subject} onChange={set("subject")} />
        </label>
        <label className="text-sm text-slate-600 md:col-span-2">Message
          <textarea className={fieldClass} rows={6} value={form.body} onChange={set("body")} placeholder={"Hi {{name}},\n\n..."} />
          <span className="mt-1 block text-xs text-slate-400">Use {"{{name}}"} to greet each person by name. Email only, for now.</span>
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>{form.id ? "Save draft" : "Create draft"}</button>
        <button type="button" className={btn.plain} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function CampaignCard({ c, canApprove, onChanged }) {
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
    <div className="s-rise rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-800">{c.name}</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{label}</span>
          </div>
          <div className="text-xs text-slate-500">{c.audience_name || "—"} · {c.subject}</div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {c.status === "sent" && <span>{c.sent_count} sent · {c.skipped_count} skipped (of {c.total_count})</span>}
          <button type="button" className={btn.plain} onClick={() => setOpen((v) => !v)}>{open ? "Hide" : "Details"}</button>
        </div>
      </div>
      {msg && <div className="mt-2"><Notice tone="bad">{msg}</Notice></div>}
      <div className="mt-3 flex flex-wrap gap-2">
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
        {c.status === "wait" && !canApprove && <span className="text-xs text-slate-500">Waiting for a Marketing manager to approve ({c.total_count} people — over the no-approval limit).</span>}
        {(c.status === "draft" || c.status === "rejected") && (
          <button type="button" className={btn.plain} disabled={busy} onClick={() => act(() => marketingApi.deleteCampaign(c.id))}>Delete</button>
        )}
      </div>
      {open && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <pre className="whitespace-pre-wrap text-xs text-slate-700">{c.body}</pre>
          {detail.data?.logs && (
            <div className="mt-3 max-h-56 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="text-left text-slate-400"><tr><th>Contact</th><th>Address</th><th>Result</th></tr></thead>
                <tbody>
                  {detail.data.logs.map((l, i) => (
                    <tr key={i} className="border-t border-slate-200">
                      <td className="py-1">{l.contact || "—"}</td>
                      <td className="py-1">{l.address || "—"}</td>
                      <td className="py-1">{l.result}</td>
                    </tr>
                  ))}
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

export default function MarketingCampaigns() {
  const { has } = useMarketing();
  const list = useAsync(() => marketingApi.campaigns(), []);
  const audiences = useAsync(() => marketingApi.audiences(), []);
  const [editing, setEditing] = useState(null);

  const canApprove = has("approve");

  return (
    <div>
      <PageTitle title="Campaigns" sub="Send a message to a saved audience's contacts. Each contact is logged once, and skipped if they're on the STOP list or were messaged recently." />
      <MarketingTabs />
      {list.error && <Notice tone="bad">{list.error}</Notice>}

      {editing ? (
        <Form audiences={audiences.data || []} initial={editing} onSaved={() => { setEditing(null); list.reload(); }} onCancel={() => setEditing(null)} />
      ) : (
        <div className="mb-4">
          <button type="button" className={btn.primary} onClick={() => setEditing({ ...EMPTY })} disabled={!(audiences.data || []).length}>+ New campaign</button>
          {!(audiences.data || []).length && !audiences.loading && <p className="mt-1 text-xs text-slate-500">Save an audience first, under Audiences.</p>}
        </div>
      )}

      <div className="grid gap-3">
        {(list.data || []).map((c) => <CampaignCard key={c.id} c={c} canApprove={canApprove} onChanged={list.reload} />)}
        {!list.loading && (list.data || []).length === 0 && <p className="text-sm text-slate-500">No campaigns yet.</p>}
      </div>
    </div>
  );
}
