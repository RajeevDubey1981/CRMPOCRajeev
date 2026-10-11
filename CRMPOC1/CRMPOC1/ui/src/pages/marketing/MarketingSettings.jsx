import { useEffect, useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useMarketing } from "./marketingUi.jsx";

const FIELDS = [
  ["approval_min_audience", "A campaign to more people than this needs approval", "people", false],
  ["pause_days", "Pause promotions to a lead after Sales spoke to them", "days", false],
  ["monthly_cap", "Promotions one person may get in a month (all channels together)", "promotions", false],
  ["daily_limit", "Messages sent in a day", "messages", false],
  ["rate_whatsapp", "Cost of one promotional WhatsApp message (from your bill)", "rupees", true],
  ["rate_sms", "Cost of one promotional SMS (from your bill)", "rupees", true],
];

export default function MarketingSettings() {
  const { status, reload } = useMarketing();
  const base = status?.settings || {};
  const [v, setV] = useState(base);
  const [msg, setMsg] = useState("");
  const [bad, setBad] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setV(status?.settings || {}); }, [status]);

  async function save() {
    setBusy(true); setMsg(""); setBad(false);
    try {
      const body = Object.fromEntries(FIELDS.map(([k]) => [k, Number(v[k])]));
      await marketingApi.updateSettings(body);
      setMsg("Saved");
      reload();
    } catch (e) { setBad(true); setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div>
      <PageTitle title="Marketing settings" sub="The limits and prices every campaign uses. Only a Marketing manager, Admin or Sub Admin can change them." />
      <MarketingTabs />
      {msg && <Notice tone={bad ? "bad" : "good"}>{msg}</Notice>}
      <div className="s-rise max-w-2xl rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {FIELDS.map(([k, label, unit, money]) => (
          <label key={k} className="mb-3 block text-sm">
            <span className="mb-1 block font-medium text-slate-700">{label}{money && <span className="ml-1 rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-800">cost</span>}</span>
            <div className="flex items-center gap-2"><input className={`${fieldClass} !w-40`} type="number" min="0" step={money ? "0.01" : "1"} value={v[k] ?? ""} onChange={(e) => setV((s) => ({ ...s, [k]: e.target.value }))} /><span className="text-xs text-slate-500">{unit}</span></div>
          </label>
        ))}
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>Save settings</button>
      </div>
    </div>
  );
}
