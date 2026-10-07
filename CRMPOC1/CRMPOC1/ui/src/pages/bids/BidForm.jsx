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
  const [lines, setLines] = useState([]); // the items of the bid: { item, quantity }
  const autoTitle = useRef(""); // the Item text made from the items below, kept until the user types their own
  const [auto, setAuto] = useState({ on: !isEdit, hit: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const touched = useRef(false);
  const [dup, setDup] = useState({ exact: null, similar: [] }); // answer of the live bid number check

  useEffect(() => { bidsApi.meta().then(setMeta).catch(() => {}); }, []);

  useEffect(() => {
    if (!isEdit) return;
    bidsApi.get(id).then((b) => {
      setForm(Object.fromEntries(Object.keys(EMPTY).map((k) => [k, b[k] ?? (typeof EMPTY[k] === "boolean" ? false : "")])));
      setLines((b.lines || []).map((l) => ({ item: l.item, quantity: l.quantity ?? "" })));
      const made = (b.lines || []).map((l) => l.item).join(", ");
      if (made && made === b.title) autoTitle.current = made; // the Item text was made from the items, so keep it in step
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

  // is this bid number already entered? asked while typing, so nobody finds out only after filling the whole form
  useEffect(() => {
    const number = form.bid_number.trim();
    if (number.length < 4) {
      setDup({ exact: null, similar: [] });
      return undefined;
    }
    const timer = setTimeout(() => {
      bidsApi.checkNumber(number, isEdit ? Number(id) : null).then(setDup).catch(() => {});
    }, 350);
    return () => clearTimeout(timer);
  }, [form.bid_number, isEdit, id]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  // items of the bid: add, change, remove. The Item text follows them until the user writes their own.
  function changeLines(next) {
    setLines(next);
    const made = next.map((l) => l.item.trim()).filter(Boolean).join(", ");
    const follows = !form.title.trim() || form.title === autoTitle.current;
    autoTitle.current = made;
    if (follows) setForm((f) => ({ ...f, title: made }));
  }
  const addLine = () => changeLines([...lines, { item: "", quantity: "" }]);
  const editLine = (i, key, value) => changeLines(lines.map((l, k) => (k === i ? { ...l, [key]: value } : l)));
  const removeLine = (i) => changeLines(lines.filter((_, k) => k !== i));
  const lineTotal = lines.reduce((sum, l) => sum + (Number(l.quantity) || 0), 0);
  const hasLineQuantity = lines.some((l) => String(l.quantity).trim() !== "");

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
    if (dup.exact) {
      setErr(`Bid number ${dup.exact.bid_number} is already entered. Open that bid instead of entering it again.`);
      return;
    }
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
    body.lines = lines
      .filter((l) => l.item.trim())
      .map((l) => ({ item: l.item.trim(), quantity: String(l.quantity).trim() === "" ? null : Number(l.quantity) }));
    if (body.lines.length && body.lines.some((l) => l.quantity !== null)) body.quantity = body.lines.reduce((s, l) => s + (l.quantity || 0), 0);
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
            <input
              required
              minLength={3}
              value={form.bid_number}
              onChange={(e) => set("bid_number", e.target.value)}
              className={`${fieldClass} ${dup.exact ? "border-rose-500 focus:border-rose-500" : dup.similar.length ? "border-amber-400" : ""}`}
              placeholder={form.bid_type === "GeM" ? "GEM/2026/B/5821904" : "UPPWD/2026-27/T-0441"}
              aria-invalid={dup.exact ? "true" : undefined}
            />
            {dup.exact && (
              <div className="mt-1.5 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">
                <strong>Already entered.</strong> {dup.exact.bid_number}, {dup.exact.title} ({dup.exact.status}).{" "}
                <Link to={`/bids/${dup.exact.id}`} className="font-semibold underline">Open that bid</Link>
              </div>
            )}
            {!dup.exact && dup.similar.length > 0 && (
              <div className="mt-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <strong>Check this is not the same bid.</strong> A bid with the same number part is already entered:
                <ul className="mt-1 space-y-0.5">
                  {dup.similar.map((b) => (
                    <li key={b.id}><Link to={`/bids/${b.id}`} className="font-mono underline">{b.bid_number}</Link> <span className="text-xs">{b.title} ({b.status})</span></li>
                  ))}
                </ul>
              </div>
            )}
          </Field>
          {form.bid_type === "State govt" && (
            <Field label="Portal">
              <input value={form.portal} onChange={(e) => set("portal", e.target.value)} className={fieldClass} placeholder="UP eProcurement, MP Tenders…" />
            </Field>
          )}
          <Field label="Item *" wide hint="Type what the bid is for. The product category below is picked from these words.">
            <input required value={form.title} onChange={(e) => set("title", e.target.value)} className={fieldClass} placeholder="Split AC 1.5 ton 5 star, 120 units" />
          </Field>
          <div className="md:col-span-2">
            <div className="mb-1 flex items-center justify-between">
              <label className={labelClass}>Items in this bid</label>
              <button type="button" onClick={addLine} className="rounded-md border border-brand-600 px-3 py-1 text-sm font-medium text-brand-700 hover:bg-brand-50">+ Add item</button>
            </div>
            {lines.length === 0 && <p className="text-xs text-slate-500">One item only? Just use the Item box above. If the bid has several things (for example 1.3 to 1.7 ton and 1.8 to 2.2 ton), add each one here with its quantity.</p>}
            <div className="space-y-2">
              {lines.map((l, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                  <input
                    value={l.item}
                    onChange={(e) => editLine(i, "item", e.target.value)}
                    placeholder="Item, for example Split AC 1.3 Ton - 1.7 Ton"
                    aria-label={`Item ${i + 1}`}
                    className="min-w-0 flex-1 basis-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none sm:basis-0"
                  />
                  <input
                    type="number"
                    min="0"
                    value={l.quantity}
                    onChange={(e) => editLine(i, "quantity", e.target.value)}
                    placeholder="Qty"
                    aria-label={`Quantity of item ${i + 1}`}
                    className="w-24 shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  />
                  <button type="button" onClick={() => removeLine(i)} aria-label={`Remove item ${i + 1}`} className="min-h-[38px] shrink-0 rounded-md border border-slate-300 px-3 text-slate-600 hover:bg-slate-50">&times;</button>
                </div>
              ))}
            </div>
            {lines.length > 0 && <p className="mt-1 text-xs text-slate-500">{lines.filter((l) => l.item.trim()).length} item{lines.filter((l) => l.item.trim()).length === 1 ? "" : "s"}{hasLineQuantity ? `, ${lineTotal} in total` : ""}.</p>}
          </div>
          <Field label="Buyer / department">
            <input value={form.department} onChange={(e) => set("department", e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Quantity" hint={hasLineQuantity ? "Worked out from the items above." : undefined}>
            <input type="number" min="0" value={hasLineQuantity ? lineTotal : form.quantity} disabled={hasLineQuantity} onChange={(e) => set("quantity", e.target.value)} className={fieldClass} />
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
          <button type="submit" disabled={busy || !!dup.exact} className={btnPrimary}>{busy ? "Saving…" : isEdit ? "Save changes" : "Enter bid"}</button>
        </div>
      </form>
    </div>
  );
}
