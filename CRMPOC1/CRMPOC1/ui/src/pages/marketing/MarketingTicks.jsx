import { useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, fmtDateTime, useAsync } from "./marketingUi.jsx";

const MENU = (has) => [
  ["Overview and reports", has("view")], ["Audiences", has("aud_own") || has("aud_all")], ["All CRM customers and leads", has("aud_all")],
  ["Prospect list upload", has("upload")], ["Campaigns (drafts and templates)", has("draft")], ["Send for approval", has("submit")],
  ["Send small campaigns without approval", has("release_small")],
  ["Approve and release", has("approve")], ["Cost", has("cost")], ["Opt-in and STOP list", has("consent_edit")],
];

export default function MarketingTicks() {
  const { data, loading, error, reload } = useAsync(() => marketingApi.ticks(), []);
  const history = useAsync(() => marketingApi.ticksHistory(), []);
  const [who, setWho] = useState("kind:mkt");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  if (error) return <div><MarketingTabs /><Notice tone="bad">{error}</Notice></div>;
  if (!data) return <div><MarketingTabs />{loading && <p className="text-sm text-slate-500">Loading...</p>}</div>;

  const isKind = who.startsWith("kind:");
  const kind = isKind ? who.slice(5) : null;
  const person = isKind ? null : data.people.find((p) => String(p.user_id) === who);
  const ticks = new Set(isKind ? data.roles[kind] : person?.ticks || []);
  const label = (k) => data.kinds.find((x) => x.key === k)?.label || k;
  const members = isKind ? data.people.filter((p) => p.kind === kind) : [];

  async function toggle(key, on) {
    setBusy(true); setMsg("");
    try {
      if (isKind) await marketingApi.setKindTicks(kind, { [key]: on });
      else {
        const kindHas = data.roles[person.kind].includes(key);
        await marketingApi.setUserTicks(person.user_id, { [key]: on === kindHas ? null : on });
      }
      reload(); history.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  async function reset() {
    setBusy(true); setMsg("");
    try {
      await marketingApi.setUserTicks(person.user_id, Object.fromEntries(Object.keys(person.overrides).map((k) => [k, null])));
      setMsg("Back to the ticks of their kind"); reload(); history.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div>
      <PageTitle title="Access ticks for Marketing" sub="Admin and Sub Admin tick what each kind of person, and each person, can do inside Marketing. These ticks are kept in the Marketing database." />
      <MarketingTabs />
      {msg && <Notice>{msg}</Notice>}
      <Notice>Who gets the Marketing menu at all is set on the user (Admin, Users): the role <b>marketing</b>, or the tick <b>Can manage marketing</b>. This page is what they can do once inside.</Notice>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <b className="text-sm">Tick for:</b>
        <select className={`${fieldClass} !w-auto`} value={who} onChange={(e) => setWho(e.target.value)}>
          <optgroup label="A kind of person (the default for everyone of it)">{data.kinds.map((k) => <option key={k.key} value={`kind:${k.key}`}>{k.label}</option>)}</optgroup>
          <optgroup label="One person">{data.people.map((p) => <option key={p.user_id} value={p.user_id}>{p.name} ({label(p.kind)})</option>)}</optgroup>
        </select>
        {isKind ? <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800">Changes everyone of this kind who has no tick of their own ({members.length} people)</span>
          : <button type="button" className={btn.plain} disabled={busy || Object.keys(person.overrides).length === 0} onClick={reset}>Follow their kind again</button>}
        {!isKind && !person.has_menu && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">This person has no Marketing menu yet: tick "Can manage marketing" on the user</span>}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="s-fade rounded-lg border border-slate-200 bg-white p-4">
          {data.groups.map((g) => (
            <div key={g.group} className="mb-3">
              <h3 className="mb-1 text-sm font-semibold text-indcool-navy">{g.group}</h3>
              {g.ticks.map((k) => {
                const on = ticks.has(k.key);
                const changed = !isKind && person.overrides[k.key] !== undefined;
                return (
                  <label key={k.key} className="flex items-start gap-2 border-t border-slate-100 py-1.5 text-sm">
                    <input type="checkbox" className="mt-1" disabled={busy || k.locked} checked={k.locked ? false : on} onChange={(e) => toggle(k.key, e.target.checked)} />
                    <span className="flex-1">{k.label}{k.locked && <span className="block text-xs text-slate-500">Admin and Sub Admin only. It cannot be ticked for anyone else.</span>}</span>
                    {k.locked ? <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">locked</span> : changed && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] text-amber-800">{on ? "added for this person" : "taken away"}</span>}
                  </label>
                );
              })}
            </div>
          ))}
        </div>
        <div className="space-y-3">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h3 className="text-sm font-semibold">{isKind ? `What ${label(kind)} sees` : `What ${person.name.split(" ")[0]} sees`}</h3>
            <p className="mb-2 text-xs text-slate-500">Inside Marketing, from the ticks</p>
            {MENU((k) => ticks.has(k)).map(([name, on]) => <div key={name} className={`py-0.5 text-sm ${on ? "" : "text-slate-400"}`}>{on ? "✓" : "–"} {name}</div>)}
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600">
            <h3 className="mb-1 text-sm font-semibold text-slate-800">Rules for the ticks</h3>
            <ul className="list-disc space-y-1 pl-4"><li>Only Admin and Sub Admin can change a tick.</li><li>Nobody can tick for themselves.</li><li>Admin and Sub Admin always have everything.</li><li>Every change is written to the history below.</li></ul>
          </div>
        </div>
      </div>
      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold">History of changes</h3>
        <ul className="space-y-1 text-sm">{(history.data || []).slice(0, 20).map((h, i) => <li key={i} className="text-slate-700">{fmtDateTime(h.at)}: <b>{h.by}</b> {h.allowed === null ? "put back to the default" : h.allowed ? "ticked" : "unticked"} <i>{h.tick}</i> for {h.person || label(h.kind)}</li>)}{(history.data || []).length === 0 && <li className="text-slate-500">No change yet.</li>}</ul>
      </div>
    </div>
  );
}
