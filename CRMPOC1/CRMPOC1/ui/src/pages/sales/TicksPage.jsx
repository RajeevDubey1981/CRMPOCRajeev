import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import { Notice, PageTitle, SalesTabs, btn, errText, fieldClass, fmtDateTime, useAsync } from "./salesUi.jsx";

const MENU = (t) => [
  ["My day", true], ["All leads", t.has("see_all")], ["Quotations", t.has("make_quote") || t.has("approve_quote")],
  ["Approvals", t.has("approve_quote") || t.has("approve_disp")], ["Export desk", t.has("exp_desk")], ["Connect sources", t.has("connect")],
  ["Team and profiles", t.has("others_profile") || t.has("targets")], ["Team dashboard", t.has("team_dash")], ["Company view", t.has("co_dash")],
];

export default function TicksPage() {
  const { data, loading, error, reload } = useAsync(() => salesApi.ticks(), []);
  const history = useAsync(() => salesApi.ticksHistory(), []);
  const [who, setWho] = useState("role:team");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  if (error) return <div><SalesTabs /><Notice tone="bad">{error}</Notice></div>;
  if (!data) return <div><SalesTabs />{loading && <p className="text-sm text-slate-500">Loading...</p>}</div>;

  const isRole = who.startsWith("role:");
  const roleKey = isRole ? who.slice(5) : null;
  const person = isRole ? null : data.people.find((p) => String(p.user_id) === who);
  const ticks = new Set(isRole ? data.roles[roleKey] : person?.ticks || []);
  const members = isRole ? data.people.filter((p) => p.role_key === roleKey) : [];

  async function toggle(key, on) {
    // "See all leads" lets a person read every lead, including other people's. Ask before it is given, most of all to a whole role.
    if (key === "see_all" && on) {
      const who = isRole ? `EVERY person in the role ${roleKey === "mgr" ? "Sales Manager" : "Sales Team"} (${members.length} people)` : person.name;
      if (!window.confirm(`Give "See all leads" to ${who}?\n\nThey will see every lead in Sales, including the leads of other people. Normally only a Sales Manager has this.`)) return;
    }
    setBusy(true); setMsg("");
    try {
      if (isRole) await salesApi.setRoleTicks(roleKey, { [key]: on });
      else {
        const roleHas = data.roles[person.role_key].includes(key);
        await salesApi.setUserTicks(person.user_id, { [key]: on === roleHas ? null : on });
      }
      reload(); history.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  async function reset() {
    setBusy(true); setMsg("");
    try {
      await salesApi.setUserTicks(person.user_id, Object.fromEntries(Object.keys(person.overrides).map((k) => [k, null])));
      setMsg("Back to the role's ticks"); reload(); history.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  const t = { has: (k) => ticks.has(k) };

  return (
    <div>
      <PageTitle title="Access ticks for Sales" sub="Admin and Sub Admin tick what each role, and each person, can do inside Sales. These ticks are kept in the Sales database." />
      <SalesTabs />
      {msg && <Notice>{msg}</Notice>}
      <Notice>Layer 1 is in the CRM Roles screen: the module <b>Sales</b> (view) shows the Sales menu. This page is layer 2: what a person can do once inside.</Notice>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <b className="text-sm">Tick for:</b>
        <select className={`${fieldClass} !w-auto`} value={who} onChange={(e) => setWho(e.target.value)}>
          <optgroup label="A role (the default for everyone in it)"><option value="role:team">Role: Sales Team</option><option value="role:mgr">Role: Sales Manager</option></optgroup>
          <optgroup label="One person">{data.people.map((p) => <option key={p.user_id} value={p.user_id}>{p.name} ({p.role_key === "mgr" ? "Sales Manager" : "Sales Team"})</option>)}</optgroup>
        </select>
        {isRole ? <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800">Changes everyone in this role who has no tick of their own ({members.length} people)</span>
          : <button type="button" className={btn.plain} disabled={busy || Object.keys(person.overrides).length === 0} onClick={reset}>Follow the role again</button>}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          {data.groups.map((g) => (
            <div key={g.group} className="mb-3">
              <h3 className="mb-1 text-sm font-semibold text-indcool-navy">{g.group}</h3>
              {g.ticks.map((k) => {
                const on = ticks.has(k.key);
                const changed = !isRole && person.overrides[k.key] !== undefined;
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
            <h3 className="text-sm font-semibold">{isRole ? "What this role sees" : `What ${person.name.split(" ")[0]} sees`}</h3>
            <p className="mb-2 text-xs text-slate-500">The Sales menu, from the ticks</p>
            {MENU(t).map(([name, on]) => <div key={name} className={`py-0.5 text-sm ${on ? "" : "text-slate-400"}`}>{on ? "✓" : "–"} {name}</div>)}
            <p className="mt-2 text-xs text-slate-500">A Sales Team member sees only the leads given to them, unless <b>See all leads</b> is ticked.</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600">
            <h3 className="mb-1 text-sm font-semibold text-slate-800">Rules for the ticks</h3>
            <ul className="list-disc space-y-1 pl-4"><li>Only Admin and Sub Admin can change a tick.</li><li>Nobody can tick for themselves.</li><li>Admin and Sub Admin always have everything.</li><li>Every change is written to the history below.</li></ul>
          </div>
        </div>
      </div>
      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold">History of changes</h3>
        <ul className="space-y-1 text-sm">{(history.data || []).slice(0, 20).map((h, i) => <li key={i} className="text-slate-700">{fmtDateTime(h.at)}: <b>{h.by}</b> {h.allowed === null ? "put back to the role's tick" : h.allowed ? "ticked" : "unticked"} <i>{h.tick}</i> for {h.person || (h.role_key === "mgr" ? "the Sales Manager role" : "the Sales Team role")}</li>)}{(history.data || []).length === 0 && <li className="text-slate-500">No change yet.</li>}</ul>
      </div>
    </div>
  );
}
