import { useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useAsync, useMarketing } from "./marketingUi.jsx";

const CHANNELS = [
  ["all", "All channels"],
  ["email", "Email only"],
  ["whatsapp", "WhatsApp only"],
  ["sms", "SMS only"],
];

export default function MarketingConsent() {
  useMarketing();
  const list = useAsync(() => marketingApi.consent(), []);
  const [contact, setContact] = useState("");
  const [channel, setChannel] = useState("all");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function add(e) {
    e.preventDefault();
    if (!contact.trim()) { setMsg("Enter a phone number or email."); return; }
    setBusy(true); setMsg("");
    try {
      await marketingApi.addConsent({ contact: contact.trim(), channel, reason: reason.trim() });
      setContact(""); setReason(""); setChannel("all");
      list.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  async function remove(c) {
    if (!window.confirm(`Take "${c.contact}" off the STOP list? They become reachable again.`)) return;
    try { await marketingApi.removeConsent(c.id); list.reload(); } catch (e) { setMsg(errText(e)); }
  }

  return (
    <div>
      <PageTitle title="Consent / STOP list" sub="Anyone here is excluded from every Audience count, and will be skipped by any future campaign send." />
      <MarketingTabs />
      {msg && <Notice tone="bad">{msg}</Notice>}
      {list.error && <Notice tone="bad">{list.error}</Notice>}

      <form onSubmit={add} className="s-rise mb-4 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-4">
        <label className="text-sm text-slate-600 md:col-span-2">Phone or email
          <input className={fieldClass} value={contact} onChange={(e) => setContact(e.target.value)} placeholder="9xxxxxxxxx or name@example.com" />
        </label>
        <label className="text-sm text-slate-600">Channel
          <select className={fieldClass} value={channel} onChange={(e) => setChannel(e.target.value)}>
            {CHANNELS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-600">Reason (optional)
          <input className={fieldClass} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Asked to stop" />
        </label>
        <div className="md:col-span-4">
          <button type="submit" className={btn.primary} disabled={busy}>{busy ? "Adding..." : "Add to STOP list"}</button>
        </div>
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2.5">Contact</th>
              <th className="px-4 py-2.5">Channel</th>
              <th className="px-4 py-2.5">Reason</th>
              <th className="px-4 py-2.5">Source</th>
              <th className="px-4 py-2.5">Added</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(list.data || []).map((c) => (
              <tr key={c.id}>
                <td className="px-4 py-2.5 font-medium text-slate-800">{c.contact}</td>
                <td className="px-4 py-2.5 text-slate-600">{CHANNELS.find(([k]) => k === c.channel)?.[1] || c.channel}</td>
                <td className="px-4 py-2.5 text-slate-600">{c.reason || "—"}</td>
                <td className="px-4 py-2.5 text-slate-500">{c.source === "reply_stop" ? "Auto (replied STOP)" : "Manual"}</td>
                <td className="px-4 py-2.5 text-slate-500">{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
                <td className="px-4 py-2.5 text-right">
                  <button type="button" className={btn.plain} onClick={() => remove(c)}>Remove</button>
                </td>
              </tr>
            ))}
            {!list.loading && (list.data || []).length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-sm text-slate-500">Nobody is on the STOP list yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
