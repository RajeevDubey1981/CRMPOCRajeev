import { useState } from "react";

import { marketingApi } from "../../api/marketing.js";
import { MarketingTabs, Notice, PageTitle, btn, errText, fieldClass, useAsync, useMarketing } from "./marketingUi.jsx";

const THEMES = {
  green: { label: "Diwali green", bg: "linear-gradient(135deg,#0b3d2e,#1c6b4f)", accent: "#f4c542" },
  violet: { label: "Diwali violet", bg: "linear-gradient(135deg,#2b1a4a,#4a2f7a)", accent: "#f4c542" },
  navy: { label: "Navy & gold", bg: "linear-gradient(135deg,#122050,#1d3a7a)", accent: "#f4c542" },
  maroon: { label: "Maroon & gold", bg: "linear-gradient(135deg,#450a0a,#7f1d1d)", accent: "#f4c542" },
  red: { label: "Classic Diwali red", bg: "linear-gradient(135deg,#5c0a0a,#9c1c1c)", accent: "#f4c542" },
  teal: { label: "Teal & gold", bg: "linear-gradient(135deg,#063a3a,#0f766e)", accent: "#f4c542" },
  charcoal: { label: "Charcoal & gold", bg: "linear-gradient(135deg,#18181b,#3f3f46)", accent: "#f4c542" },
};

const EMPTY = {
  name: "", theme: "green", greeting: "Happy Diwali!", headline: "Heavy Duty Dubai Series — festive price, built for extreme heat.",
  pill1: "HEAVY DUTY", pill2: "Dubai Series", cta_text: "Shop Now", cta_link: "", image_path: null, start_date: "", end_date: "", target_type: "all", is_enabled: true,
};

function BannerPreview({ b }) {
  if (b.image_path) {
    return <img src={b.image_path} alt={b.headline || "Banner"} className="w-full rounded-lg border border-slate-200" />;
  }
  const theme = THEMES[b.theme] || THEMES.green;
  return (
    <div style={{ background: theme.bg }} className="rounded-lg p-3">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-white">
        {b.greeting && <span style={{ color: theme.accent }} className="font-bold">✦ {b.greeting}</span>}
        {b.pill1 && <span className="rounded-full bg-white/15 px-2.5 py-0.5">{b.pill1}</span>}
        {b.pill2 && <span className="rounded-full bg-white/15 px-2.5 py-0.5">{b.pill2}</span>}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-3">
        <span className="text-sm font-bold text-white">{b.headline || "Your headline here"}</span>
        {b.cta_text && (
          <span style={{ background: theme.accent }} className="rounded-full px-3.5 py-1 text-xs font-bold text-slate-900">{b.cta_text}</span>
        )}
      </div>
    </div>
  );
}

function Form({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [uploading, setUploading] = useState(false);
  const guide = useAsync(() => marketingApi.bannerImageGuide(), []);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  async function pickImage(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true); setMsg("");
    try {
      const r = await marketingApi.uploadBannerImage(file);
      setForm((f) => ({ ...f, image_path: r.image_path }));
    } catch (err) { setMsg(errText(err)); } finally { setUploading(false); e.target.value = ""; }
  }

  async function save() {
    if (!form.name.trim() || !form.headline.trim() || !form.start_date || !form.end_date) {
      setMsg("Name, headline and both dates are required.");
      return;
    }
    setBusy(true); setMsg("");
    try {
      if (form.id) await marketingApi.updateBanner(form.id, form);
      else await marketingApi.createBanner(form);
      onSaved();
    } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div className="s-rise mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-800">{form.id ? "Edit banner" : "New festive banner"}</h3>
      {msg && <Notice tone="bad">{msg}</Notice>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm text-slate-600">Banner name
          <input className={fieldClass} value={form.name} onChange={set("name")} placeholder="Diwali — Dubai Series offer" />
        </label>
        <label className="text-sm text-slate-600">Theme
          <select className={fieldClass} value={form.theme} onChange={set("theme")}>
            {Object.entries(THEMES).map(([k, t]) => <option key={k} value={k}>{t.label}</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-600">Greeting (optional)
          <input className={fieldClass} value={form.greeting} onChange={set("greeting")} placeholder="Happy Diwali!" />
        </label>
        <label className="text-sm text-slate-600">Target
          <select className={fieldClass} value={form.target_type} onChange={set("target_type")}>
            <option value="all">Everyone (all outgoing mail)</option>
          </select>
        </label>
        <label className="text-sm text-slate-600 md:col-span-2">Headline / offer line
          <input className={fieldClass} value={form.headline} onChange={set("headline")} />
        </label>
        <label className="text-sm text-slate-600">Pill 1</label>
        <label className="text-sm text-slate-600">Pill 2</label>
        <input className={fieldClass} value={form.pill1} onChange={set("pill1")} />
        <input className={fieldClass} value={form.pill2} onChange={set("pill2")} />
        <label className="text-sm text-slate-600">CTA text
          <input className={fieldClass} value={form.cta_text} onChange={set("cta_text")} />
        </label>
        <label className="text-sm text-slate-600">Offer link (CTA target)
          <input className={fieldClass} value={form.cta_link} onChange={set("cta_link")} placeholder="https://..." />
        </label>
        <label className="text-sm text-slate-600">Active from
          <input type="date" className={fieldClass} value={form.start_date} onChange={set("start_date")} />
        </label>
        <label className="text-sm text-slate-600">Active to
          <input type="date" className={fieldClass} value={form.end_date} onChange={set("end_date")} />
        </label>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          <input type="checkbox" checked={form.is_enabled} onChange={set("is_enabled")} />Enabled
        </label>
      </div>
      <div className="mt-4 rounded-lg border border-dashed border-slate-300 p-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Upload your own banner image (optional)</div>
        <p className="mb-2 text-xs text-slate-500">
          Recommended size: <b>{guide.data?.recommended_size || "1200 x 300 px (a 4:1 wide strip)"}</b>.
          Format: <b>{(guide.data?.formats || ["JPG", "PNG"]).join(" or ")}</b>, under <b>{guide.data?.max_size_mb ?? 2}MB</b>.
          {guide.data?.note ? ` ${guide.data.note}` : " Keep important text inside the middle 80% — some mail apps crop the edges."}
          {" "}If no image is uploaded, the theme design above is used instead.
        </p>
        <div className="flex items-center gap-2">
          <input type="file" accept="image/jpeg,image/png" onChange={pickImage} disabled={uploading} className="text-sm" />
          {uploading && <span className="text-xs text-slate-500">Uploading...</span>}
          {form.image_path && <button type="button" className={btn.plain} onClick={() => setForm((f) => ({ ...f, image_path: null }))}>Remove image</button>}
        </div>
      </div>
      <div className="mt-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Live preview</div>
        <BannerPreview b={form} />
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" className={btn.primary} disabled={busy} onClick={save}>{form.id ? "Save changes" : "Create banner"}</button>
        <button type="button" className={btn.plain} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function MarketingBanners() {
  useMarketing();
  const list = useAsync(() => marketingApi.banners(), []);
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");

  async function remove(b) {
    if (!window.confirm(`Delete banner "${b.name}"?`)) return;
    try { await marketingApi.deleteBanner(b.id); list.reload(); } catch (e) { setMsg(errText(e)); }
  }

  return (
    <div>
      <PageTitle title="Festive banner" sub="Shown at the top of outgoing CRM emails while active — a reminder/offer banner, like a bank's festive promo." />
      <MarketingTabs />
      {msg && <Notice tone="bad">{msg}</Notice>}
      {list.error && <Notice tone="bad">{list.error}</Notice>}

      {editing ? (
        <Form initial={editing} onSaved={() => { setEditing(null); list.reload(); }} onCancel={() => setEditing(null)} />
      ) : (
        <div className="mb-4">
          <button type="button" className={btn.primary} onClick={() => setEditing({ ...EMPTY })}>+ New banner</button>
        </div>
      )}

      <div className="grid gap-3">
        {(list.data || []).map((b, i) => (
          <div key={b.id} style={{ "--i": i }} className="s-rise rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-800">{b.name}</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.is_active_now ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
                  {b.is_active_now ? "Active now" : "Not active"}
                </span>
                <span className="text-xs text-slate-400">{b.start_date} → {b.end_date}</span>
              </div>
              <div className="flex gap-2">
                <button type="button" className={btn.plain} onClick={() => setEditing(b)}>Edit</button>
                <button type="button" className={btn.plain} onClick={() => remove(b)}>Delete</button>
              </div>
            </div>
            <BannerPreview b={b} />
          </div>
        ))}
        {!list.loading && (list.data || []).length === 0 && <p className="text-sm text-slate-500">No festive banners yet.</p>}
      </div>
    </div>
  );
}
