import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { bidsApi } from "../../api/bids.js";
import { BidTabs, Notice, PageTitle, btnGhost, btnPrimary, errText, fieldClass, isoDate, labelClass } from "./bidUi.jsx";

const EMD_MODES = ["Online (GeM)", "Demand draft", "Bank guarantee", "FDR", "Online (portal)", "Exempt (MSE)", "Exempt (Startup)"];

const EMPTY = {
  bid_type: "GeM",
  bid_number: "",
  portal: "",
  title: "",
  department: "",
  product_category: "",
  product_type: "",
  quantity: "",
  estimated_value: "",
  publish_date: isoDate(new Date()),
  end_date: "",
  opening_date: "",
  emd_amount: "",
  emd_mode: "Online (GeM)",
  emd_exempt: false,
  epbg_details: "",
  tender_fee: "",
  notes: "",
};

const NUMBER_FIELDS = ["quantity", "estimated_value", "emd_amount", "tender_fee"];

function Section({ title, children }) {
  return (
    <section className="rounded-lg bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>
    </section>
  );
}

function Field({ label, children, wide, hint }) {
  return (
    <div className={wide ? "md:col-span-2" : ""}>
      <label className={labelClass}>{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export default function BidForm() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const isEdit = !!id;
  const [meta, setMeta] = useState(null);
  const [form, setForm] = useState({ ...EMPTY, bid_number: params.get("number") || "" });
  const [auto, setAuto] = useState({ on: !isEdit, hit: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const touched = useRef(false);

  useEffect(() => { bidsApi.meta().then(setMeta).catch(() => {}); }, []);

  useEffect(() => {
    if (!isEdit) return;
    bidsApi.get(id).then((b) => {
      setForm(Object.fromEntries(Object.keys(EMPTY).map((k) => [k, b[k] ?? (typeof EMPTY[k] === "boolean" ? false : "")])));
    }).catch((e) => setErr(errText(e, "Could not load the bid")));
  }, [id, isEdit]);

  // pick the product category and type from the words of the item, until the user chooses one by hand
  useEffect(() => {
    if (!auto.on || touched.current || form.title.trim().length < 3) return undefined;
    const timer = setTimeout(() => {
      bidsApi.detect(form.title).then((r) => {
        setForm((f) => ({ ...f, product_category: r.name, product_type: r.type || "" }));
        setAuto({ on: true, hit: r.hit });
      }).catch(() => {});
    }, 300);
    return () => clearTimeout(timer);
  }, [form.title, auto.on]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function pickCategory(value) {
    touched.current = true;
    setAuto({ on: false, hit: true });
    setForm((f) => ({ ...f, product_category: value, product_type: "" }));
  }

  function changeBidType(value) {
    setForm((f) => ({
      ...f,
      bid_type: value,
      emd_mode: value === "GeM" && (!f.emd_mode || f.emd_mode === "Demand draft") ? "Online (GeM)" : value === "State govt" && f.emd_mode === "Online (GeM)" ? "Demand draft" : f.emd_mode,
    }));
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (form.end_date && form.publish_date && form.end_date < form.publish_date) {
      setErr("The end date cannot be before the publish date.");
      return;
    }
    const body = {};
    Object.entries(form).forEach(([k, v]) => {
      if (NUMBER_FIELDS.includes(k)) body[k] = v === "" ? null : Number(v);
      else if (typeof v === "string") body[k] = v.trim() === "" ? null : v.trim();
      else body[k] = v;
    });
    body.bid_type = form.bid_type;
    if (body.portal && form.bid_type === "GeM") body.portal = null;
    setBusy(true);
    try {
      const saved = isEdit ? await bidsApi.update(id, body) : await bidsApi.create(body);
      navigate(`/bids/${saved.id}`);
    } catch (e2) {
      setErr(errText(e2, "Could not save the bid"));
    } finally {
      setBusy(false);
    }
  }

  const types = meta && form.product_category ? meta.types[form.product_category] || [] : [];

  return (
    <div>
      <PageTitle title={isEdit ? "Edit bid" : "Enter a bid"} sub="The bid team enters every bid once. Allocation comes next." />
      <BidTabs manager />
      <form onSubmit={submit} className="space-y-4">
        <Notice tone="bad">{err}</Notice>

        <Section title="Bid">
          <Field label="Bid category *">
            <div className="flex gap-4 pt-1.5 text-sm">
              {["GeM", "State govt"].map((t) => (
                <label key={t} className="flex items-center gap-1.5">
                  <input type="radio" name="bid_type" checked={form.bid_type === t} onChange={() => changeBidType(t)} />
                  {t === "GeM" ? "GeM bid" : "State govt bid"}
                </label>
              ))}
            </div>
          </Field>
          <Field label="Bid number *">
            <input required minLength={3} value={form.bid_number} onChange={(e) => set("bid_number", e.target.value)} className={fieldClass} placeholder={form.bid_type === "GeM" ? "GEM/2026/B/5821904" : "UPPWD/2026-27/T-0441"} />
          </Field>
          {form.bid_type === "State govt" && (
            <Field label="Portal">
              <input value={form.portal} onChange={(e) => set("portal", e.target.value)} className={fieldClass} placeholder="UP eProcurement, MP Tenders…" />
            </Field>
          )}
          <Field label="Item *" wide hint="Type what the bid is for. The product category below is picked from these words.">
            <input required value={form.title} onChange={(e) => set("title", e.target.value)} className={fieldClass} placeholder="Split AC 1.5 ton 5 star, 120 units" />
          </Field>
          <Field label="Buyer / department">
            <input value={form.department} onChange={(e) => set("department", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Quantity">
            <input type="number" min="0" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Product category">
            <select value={form.product_category} onChange={(e) => pickCategory(e.target.value)} className={fieldClass}>
              <option value="">Choose the category</option>
              {Object.keys(meta?.types || {}).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Product type" hint={auto.on && form.product_category ? (auto.hit ? "Picked automatically. Change it if it is wrong." : "No product word found in the item, so Other Appliances is set. Please check.") : undefined}>
            <select value={form.product_type} onChange={(e) => { touched.current = true; set("product_type", e.target.value); }} disabled={!form.product_category} className={fieldClass}>
              <option value="">{form.product_category ? "Choose the type" : "Choose the category first"}</option>
              {types.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Estimated value (₹)">
            <input type="number" min="0" step="any" value={form.estimated_value} onChange={(e) => set("estimated_value", e.target.value)} className={fieldClass} />
          </Field>
        </Section>

        <Section title="Dates">
          <Field label="Bid publish date">
            <input type="date" value={form.publish_date || ""} onChange={(e) => set("publish_date", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Bid end date *" hint="The bidder must submit before this date. Confirmation and submission dates are worked out from it.">
            <input type="date" required value={form.end_date || ""} onChange={(e) => set("end_date", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Bid opening date">
            <input type="date" value={form.opening_date || ""} onChange={(e) => set("opening_date", e.target.value)} className={fieldClass} />
          </Field>
        </Section>

        <Section title="EMD and ePBG">
          <Field label="EMD amount (₹)">
            <input type="number" min="0" step="any" value={form.emd_amount} onChange={(e) => set("emd_amount", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="EMD mode">
            <select value={form.emd_mode || ""} onChange={(e) => set("emd_mode", e.target.value)} className={fieldClass}>
              <option value="">Not stated</option>
              {EMD_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
            <input type="checkbox" checked={form.emd_exempt} onChange={(e) => set("emd_exempt", e.target.checked)} className="h-4 w-4" />
            EMD exempted for INDcool or the bidder
          </label>
          <Field label="ePBG details" hint="Performance security percentage and months, for example 3% for 24 months.">
            <input value={form.epbg_details} onChange={(e) => set("epbg_details", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Tender fee (₹)">
            <input type="number" min="0" step="any" value={form.tender_fee} onChange={(e) => set("tender_fee", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Internal notes" wide hint="Only the bid team sees these. Vendors never do.">
            <textarea rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} className={fieldClass} />
          </Field>
        </Section>

        <div className="flex justify-end gap-2">
          <Link to={isEdit ? `/bids/${id}` : "/bids"} className={btnGhost}>Cancel</Link>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? "Saving…" : isEdit ? "Save changes" : "Enter bid"}</button>
        </div>
      </form>
    </div>
  );
}
