import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, useAsync, useMarketing } from "./marketingUi.jsx";

const TICK_LABEL = {
  view: "View and reports", aud_own: "Audiences from my own leads", aud_all: "Audiences from all CRM data", upload: "Upload prospect lists",
  draft: "Write drafts and templates", submit: "Send for approval", approve: "Approve and release", cost: "See cost",
  consent_edit: "Edit opt-in and STOP list", connect: "Connect platforms", settings: "Rates and limits", give_ticks: "Give Marketing ticks",
};

const NEXT = [
  ["Audiences", "Build lists from the CRM customers and the Sales leads, by type, category and place."],
  ["Campaigns", "WhatsApp, SMS and email, with approval, schedule and cost."],
  ["Channels", "Connect and publish to Facebook, Instagram, YouTube, LinkedIn and more."],
  ["Sales leads from replies", "A reply or click becomes a Sales lead with the campaign name."],
];

export default function MarketingHome() {
  const { status } = useMarketing();
  const people = useAsync(() => (status?.ticks?.includes("view") ? marketingApi.people() : Promise.resolve([])), [status?.ticks?.join(",")]);
  return (
    <div>
      <PageTitle title="Marketing" sub="Its own database and its own access. Audiences, campaigns and channels are added step by step." />
      <MarketingTabs />
      <div className="s-rise mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800">Your access in Marketing</h2>
        <p className="mb-2 text-sm text-slate-500">What you can do is set by Admin or Sub Admin on the Access ticks page.</p>
        <div className="flex flex-wrap gap-1.5">
          {(status?.ticks || []).map((t) => <span key={t} className="rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-semibold text-indcool-navy">{TICK_LABEL[t] || t}</span>)}
        </div>
      </div>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {NEXT.map(([t, d], i) => (
          <div key={t} style={{ "--i": i }} className="s-rise s-lift rounded-lg border border-dashed border-slate-300 bg-white p-4">
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Coming next</span>
            <h3 className="mt-2 text-sm font-semibold text-slate-800">{t}</h3>
            <p className="text-sm text-slate-500">{d}</p>
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-base font-semibold text-slate-800">Who has Marketing</h2>
        {people.error && <Notice tone="bad">{people.error}</Notice>}
        <ul className="grid gap-1 text-sm sm:grid-cols-2">
          {(people.data || []).map((p) => <li key={p.user_id} className="flex justify-between border-t border-slate-100 py-1"><span>{p.name}</span><span className="text-slate-500">{p.role}</span></li>)}
        </ul>
        <p className="mt-2 text-xs text-slate-500">Admin, Sub Admin, the marketing role, and people whose user has "Can manage marketing" ticked.</p>
      </div>
    </div>
  );
}
