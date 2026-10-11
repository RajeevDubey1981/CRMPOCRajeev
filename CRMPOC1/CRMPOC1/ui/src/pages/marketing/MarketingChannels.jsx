import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { marketingApi } from "../../api/marketing.js";
import { CountUp, Icon, MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useAsync, useMarketing } from "./marketingUi.jsx";

const RESULT = {
  connected: ["good", "Meta is connected."],
  cancelled: ["warn", "The Meta login was cancelled. Nothing was connected."],
  failed: ["bad", "The Meta login did not work. Try again; if it repeats, check the App ID, the App Secret and the redirect address in the Meta app."],
};
const money = (v, cur) => `${cur === "INR" || !cur ? "₹" : `${cur} `}${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

function Steps({ status }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
      <b>Meta is not set up on the server yet.</b> Do this once:
      <ol className="mt-2 list-decimal space-y-1 pl-5">
        <li>At developers.facebook.com open your app, then <b>App settings, Basic</b>: copy the <b>App ID</b> and the <b>App Secret</b>.</li>
        <li>Under <b>Facebook Login, Settings</b>, add this address as a <b>Valid OAuth Redirect URI</b>: <code className="rounded bg-white px-1.5 py-0.5 text-xs">{status?.redirect_uri || "https://indcoolapplainces.com/api/marketing/meta/callback"}</code></li>
        <li>On your PC, in the project folder, run <code className="rounded bg-white px-1.5 py-0.5 text-xs">py scripts/set_meta_keys.py</code> and paste the two values when asked. It stores them on the server and never shows the secret.</li>
        <li>Come back here and press <b>Connect Meta</b>.</li>
      </ol>
    </div>
  );
}

function Campaigns({ accounts }) {
  const inUse = accounts.filter((a) => a.in_use);
  const [acc, setAcc] = useState(inUse[0]?.id || "");
  const list = useAsync(() => (acc ? marketingApi.metaCampaigns(acc) : Promise.resolve([])), [acc]);
  useEffect(() => { if (!acc && inUse[0]) setAcc(inUse[0].id); }, [inUse, acc]);
  if (!inUse.length) return <p className="text-sm text-slate-500">Switch on at least one ad account above to see its campaigns.</p>;
  const rows = list.data || [];
  const total = (k) => rows.reduce((n, r) => n + Number(r.last_30_days?.[k] || 0), 0);
  const cur = inUse.find((a) => a.id === acc)?.currency;
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select className={`${fieldClass} !w-auto`} value={acc} onChange={(e) => setAcc(e.target.value)}>{inUse.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.id})</option>)}</select>
        <span className="text-xs text-slate-500">Last 30 days. Read only: nothing here can change or spend money.</span>
      </div>
      {list.error && <Notice tone="bad">{list.error}</Notice>}
      <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[["Spent", total("spend"), true], ["People reached", total("reach")], ["Clicks", total("clicks")], ["Leads", total("leads")]].map(([label, v, isMoney], i) => (
          <div key={label} style={{ "--i": i }} className="s-rise s-lift rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-2xl font-semibold tabular-nums text-slate-800">{isMoney ? `${cur === "INR" || !cur ? "₹" : `${cur} `}` : ""}<CountUp value={Math.round(v)} /></div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Campaign</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Goal</th><th className="px-3 py-2 text-right">Spent</th><th className="px-3 py-2 text-right">Reached</th><th className="px-3 py-2 text-right">Clicks</th><th className="px-3 py-2 text-right">Leads</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.id}><td className="px-3 py-2 font-medium">{r.name}</td>
                <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${r.effective_status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>{r.effective_status || r.status}</span></td>
                <td className="px-3 py-2 text-slate-600">{String(r.objective || "").replace(/^OUTCOME_/, "").toLowerCase()}</td>
                <td className="px-3 py-2 text-right tabular-nums">{money(r.last_30_days?.spend, cur)}</td><td className="px-3 py-2 text-right tabular-nums">{Number(r.last_30_days?.reach || 0).toLocaleString("en-IN")}</td>
                <td className="px-3 py-2 text-right tabular-nums">{Number(r.last_30_days?.clicks || 0).toLocaleString("en-IN")}</td><td className="px-3 py-2 text-right tabular-nums">{r.last_30_days?.leads || 0}</td></tr>
            ))}
            {!list.loading && rows.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No campaigns in this ad account.</td></tr>}
            {list.loading && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading from Meta...</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function MarketingChannels() {
  const { has } = useMarketing();
  const [params, setParams] = useSearchParams();
  const result = params.get("meta");
  const st = useAsync(() => marketingApi.metaStatus(), []);
  const accounts = useAsync(() => (st.data?.connected && has("cost") ? marketingApi.metaAdAccounts() : Promise.resolve([])), [st.data?.connected]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [diag, setDiag] = useState(null);
  const [sysOpen, setSysOpen] = useState(false);
  const [sysToken, setSysToken] = useState("");
  const s = st.data;

  async function check() {
    setBusy(true); setMsg("");
    try { setDiag(await marketingApi.metaDiagnose()); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  async function saveSystemToken() {
    setBusy(true); setMsg("");
    try {
      const r = await marketingApi.metaSystemToken(sysToken);
      setSysToken(""); setSysOpen(false); setMsg(`Connected as ${r.name}. ${r.ad_accounts} ad account(s) found.`);
      st.reload(); accounts.reload();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  async function connect() {
    setBusy(true); setMsg("");
    try { const { url } = await marketingApi.metaConnect(); window.location.assign(url); } catch (e) { setMsg(errText(e)); setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm("Disconnect Meta? The saved login is erased. Nothing in your Meta account changes.")) return;
    setBusy(true);
    try { await marketingApi.metaDisconnect(); st.reload(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  async function toggle(a) {
    try { await marketingApi.metaUseAccount(a.id, !a.in_use); accounts.reload(); } catch (e) { setMsg(errText(e)); }
  }

  return (
    <div>
      <PageTitle title="Channels" sub="Connect your company accounts once, with the platform's own login. Nothing is posted or spent from here yet." />
      <MarketingTabs />
      {result && RESULT[result] && <Notice tone={RESULT[result][0]}>{RESULT[result][1]} <button type="button" className="ml-2 underline" onClick={() => setParams({})}>dismiss</button></Notice>}
      {msg && <Notice tone="bad">{msg}</Notice>}
      {st.error && <Notice tone="bad">{st.error}</Notice>}

      <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#0b57d0] text-sm font-bold text-white">Meta</span>
            <div>
              <h2 className="text-base font-semibold text-slate-800">Meta: Facebook, Instagram and ads</h2>
              <p className="text-sm text-slate-500">{s?.connected ? `Connected as ${s.name}` : "Not connected"}{s?.connected && s.days_left != null ? ` · login valid for ${s.days_left} more days` : ""}</p>
            </div>
          </div>
          {s && s.configured && !s.connected && s.can_connect && <button type="button" className={btn.primary} disabled={busy} onClick={connect}>Connect Meta</button>}
          {s?.connected && s.can_connect && <div className="flex gap-2"><button type="button" className={s.days_left != null && s.days_left < 10 ? btn.go : btn.primary} disabled={busy} onClick={connect} title="Log in with Facebook again, for example after you were given access to another ad account">Reconnect Meta</button><button type="button" className={btn.plain} disabled={busy} onClick={disconnect}>Disconnect</button></div>}
        </div>
        {s?.connected && <p className="mt-2 text-xs text-slate-500">Missing an ad account? Press <b>Reconnect Meta</b> and, in the Facebook window, choose every ad account you want to share. Allowed to: <b>read your ad accounts and their results</b>. It cannot create or change ads, and it cannot spend money.</p>}
        {s && !s.configured && <div className="mt-3"><Steps status={s} /></div>}
        {s?.configured && s.can_connect && (
          <div className="mt-3">
            <button type="button" className={btn.plain} onClick={() => setSysOpen((v) => !v)}>Connect with a System User token instead</button>
            {sysOpen && (
              <div className="s-pop mt-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                <p>In Business settings, open <b>Users, System users</b>, add a System User with Employee access, give it <b>View performance</b> on the ad accounts, then <b>Generate token</b> for this app with <b>ads_read</b>. Paste it here. It is saved encrypted and never shown again; it does not run out after 60 days.</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <input type="password" autoComplete="off" value={sysToken} onChange={(e) => setSysToken(e.target.value)} placeholder="Paste the token" className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm" />
                  <button type="button" className={btn.primary} disabled={busy || sysToken.trim().length < 20} onClick={saveSystemToken}>Save token</button>
                </div>
              </div>
            )}
          </div>
        )}
        {s?.connected && s.can_connect && (
          <div className="mt-3">
            <button type="button" className={btn.plain} disabled={busy} onClick={check}>Check why an ad account is missing</button>
            {diag && (
              <div className="s-pop mt-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                <div><b>Permissions Facebook gave this login:</b> {(diag.permissions || []).map((p) => `${p.name}: ${p.status}`).join(", ") || diag.permissions_error || "none"}</div>
                <div className="mt-1"><b>Ad accounts chosen in Facebook's window:</b> {(diag.granular || []).map((g) => `${g.scope} for ${(g.target_ids || []).join(", ") || "all"}`).join("; ") || diag.granular_error || "no limit was set"}</div>
                <div className="mt-1"><b>Ad accounts given to the person directly:</b> {diag.direct_accounts ?? diag.direct_error}</div>
                <div className="mt-1"><b>Businesses the person belongs to:</b> {(diag.businesses || []).map((b) => `${b.name} (owns ${b.owned_ad_accounts}, client ${b.client_ad_accounts})`).join("; ") || diag.businesses_error || "none"}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {s?.connected && has("cost") && (
        <>
          <section className="mb-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Your ad accounts</h3>
            {accounts.error && <Notice tone="bad">{accounts.error}</Notice>}
            <div className="grid gap-2 md:grid-cols-2">
              {(accounts.data || []).map((a, i) => (
                <div key={a.id} style={{ "--i": i }} className="s-rise flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3">
                  <div className="min-w-0"><div className="truncate text-sm font-semibold text-slate-800">{a.name}</div><div className="text-xs text-slate-500">{a.id} · {a.currency}{a.business ? ` · ${a.business}` : ""}{a.amount_spent ? ` · spent so far ${money(a.amount_spent, a.currency)}` : ""}</div></div>
                  <label className="flex shrink-0 items-center gap-1.5 text-xs font-medium text-slate-600"><input type="checkbox" checked={a.in_use} disabled={!s.can_connect} onChange={() => toggle(a)} />Use in the CRM</label>
                </div>
              ))}
              {!accounts.loading && (accounts.data || []).length === 0 && <p className="text-sm text-slate-500">This Meta login has no ad accounts. Ask the owner of the ad account to give it to this login in Business Manager.</p>}
            </div>
          </section>
          <section className="mb-4"><h3 className="mb-2 text-sm font-semibold text-slate-800">Campaigns</h3><Campaigns accounts={accounts.data || []} /></section>
        </>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[["Facebook Page", "Post and schedule to your Page.", "calendar"], ["Instagram (careindcool)", "Photos, Reels and carousels, once the account is linked to the Page.", "chat"], ["Create ads, paused", "Start a campaign for a manager to approve; never active until approved.", "bell"], ["WhatsApp promotions", "Approved marketing templates on your existing WhatsApp account.", "phone"]].map(([t, d, icon], i) => (
          <div key={t} style={{ "--i": i }} className="s-rise s-lift rounded-lg border border-dashed border-slate-300 bg-white p-4">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-violet-100 text-violet-700"><Icon name={icon} size={16} /></span>
            <span className="mt-2 block"><span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Coming next</span></span>
            <h3 className="mt-1 text-sm font-semibold text-slate-800">{t}</h3><p className="text-sm text-slate-500">{d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
