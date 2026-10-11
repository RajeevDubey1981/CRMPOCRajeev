import { marketingApi } from "../../api/marketing.js";
import { FlowGraphic, HeroArt } from "./marketingArt.jsx";
import { CountUp, Icon, MarketingTabs, Notice, PageTitle, greeting, useAsync, useMarketing } from "./marketingUi.jsx";

const TICK_LABEL = {
  view: "View and reports", aud_own: "Audiences from my own leads", aud_all: "Audiences from all CRM data", upload: "Upload prospect lists",
  draft: "Write drafts and templates", submit: "Send for approval", release_small: "Send small campaigns", approve: "Approve and release", cost: "See cost",
  consent_edit: "Edit opt-in and STOP list", connect: "Connect platforms", settings: "Rates and limits", give_ticks: "Give Marketing ticks",
};
const KIND = { admin: "Admin", mktm: "Marketing manager", mkt: "Marketing user", mgr: "Sales Manager", team: "Sales Team", oth: "Marketing access" };

const NEXT = [
  ["Audiences", "Build lists from the CRM customers and the Sales leads, by type, category and place.", "users"],
  ["Campaigns", "WhatsApp, SMS and email, with approval, schedule and cost.", "chat"],
  ["Channels", "Connect and publish to Facebook, Instagram, YouTube, LinkedIn and more.", "calendar"],
  ["Leads for Sales", "A reply or click becomes a Sales lead with the campaign name.", "phone"],
];

export default function MarketingHome() {
  const { status } = useMarketing();
  const people = useAsync(() => (status?.ticks?.includes("view") ? marketingApi.people() : Promise.resolve([])), [status?.ticks?.join(",")]);
  const rules = status?.rules || {};
  const tiles = [
    [(people.data || []).length, "People with Marketing", "users", "#7c3aed", ""],
    [(status?.ticks || []).length, "Things you can do here", "check", "#2f5bb5", ""],
    [Number(rules.approval_min_audience || 0), "People: a campaign above this needs approval", "bell", "#d97706", ""],
    [Number(rules.pause_days || 0), "Days promotions pause after Sales talks to a lead", "calendar", "#059669", ""],
    [Number(rules.monthly_cap || 0), "Promotions per person a month, at most", "mail", "#a855f7", ""],
  ];
  return (
    <div>
      <PageTitle title="Marketing" sub="Audiences, campaigns and channels, working hand in hand with Sales." />
      <MarketingTabs />
      <div className="s-hero mk-hero s-rise mb-4 flex items-center justify-between gap-4 rounded-xl p-5 shadow-sm">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-white/70">{greeting()}</div>
          <div className="text-2xl font-semibold">Marketing for INDcool</div>
          <div className="mt-1 text-sm text-white/80">You are in as <b>{KIND[status?.kind] || "Marketing"}</b>. Every message, post and call here goes through your approval rules, and every reply lands in Sales.</div>
        </div>
        <HeroArt />
      </div>
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {tiles.map(([value, label, icon, color], i) => (
          <div key={label} style={{ "--i": i }} className="s-rise s-lift relative overflow-hidden rounded-lg border border-slate-200 bg-white p-3.5">
            <span style={{ "--i": i, background: color }} className="s-grow absolute inset-x-0 top-0 h-1.5" />
            <div className="flex items-start justify-between gap-2">
              <div className="text-3xl font-semibold tabular-nums text-slate-800"><CountUp value={value} /></div>
              <span style={{ background: `${color}22`, color }} className="grid h-8 w-8 shrink-0 place-items-center rounded-full"><Icon name={icon} size={16} /></span>
            </div>
            <div className="mt-1 text-xs font-medium text-slate-600">{label}</div>
          </div>
        ))}
      </div>
      <div className="s-rise mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800">How a campaign travels</h2>
        <p className="mb-1 text-sm text-slate-500">Marketing builds the audience and sends; people who reply become Sales leads; Sales closes the sale. The result comes back to Marketing.</p>
        <FlowGraphic />
      </div>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {NEXT.map(([t, d, icon], i) => (
          <div key={t} style={{ "--i": i }} className="s-rise s-lift rounded-lg border border-dashed border-slate-300 bg-white p-4">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-violet-100 text-violet-700"><Icon name={icon} size={16} /></span>
            <span className="mt-2 block"><span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Coming next</span></span>
            <h3 className="mt-1 text-sm font-semibold text-slate-800">{t}</h3>
            <p className="text-sm text-slate-500">{d}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="s-rise rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800">Your access</h2>
          <p className="mb-2 text-sm text-slate-500">Set by Admin or Sub Admin on the Access ticks page.</p>
          <div className="flex flex-wrap gap-1.5">{(status?.ticks || []).map((t) => <span key={t} className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-800">{TICK_LABEL[t] || t}</span>)}</div>
        </div>
        <div className="s-rise rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-base font-semibold text-slate-800">Who has Marketing</h2>
          {people.error && <Notice tone="bad">{people.error}</Notice>}
          <ul className="grid gap-1 text-sm sm:grid-cols-2">{(people.data || []).map((p) => <li key={p.user_id} className="flex justify-between border-t border-slate-100 py-1"><span>{p.name}</span><span className="text-slate-500">{p.role}</span></li>)}</ul>
        </div>
      </div>
    </div>
  );
}
