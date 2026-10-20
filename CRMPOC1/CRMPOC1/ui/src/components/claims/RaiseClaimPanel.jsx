import { useEffect, useState } from "react";

import { api } from "../../api/client.js";
import { shortageClaimsApi, ITEMS_MISSING } from "../../api/shortageClaims.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";

const PHOTO_LABELS = ["Box as received", "Seal / tape", "Empty space inside", "Item's label on box"];

/**
 * Raised from inside the actual Service/Installation step or its approval — collapsed to one button until
 * needed. For "parts" and "service" flows the whoever-is-responsible decision (manufacturer, company,
 * insurance or transport) is mandatory right here, at raise time, instead of as a separate step later.
 * "installation" keeps the original what's-missing + 4-photo form.
 */
export default function RaiseClaimPanel({ flow, context, triggerLabel, onSent }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [photos, setPhotos] = useState([]);
  const [extraPhotos, setExtraPhotos] = useState([]);
  const [unitPhotos, setUnitPhotos] = useState([]);
  const [respType, setRespType] = useState("");
  const [vendorId, setVendorId] = useState("");
  const [courierId, setCourierId] = useState("");
  const [insurer, setInsurer] = useState("");
  const [parties, setParties] = useState({ vendors: [], couriers: [] });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [sent, setSent] = useState(null);

  useEffect(() => {
    if (open && (flow === "parts" || flow === "service")) shortageClaimsApi.parties().then(setParties).catch(() => {});
  }, [open, flow]);

  useEffect(() => {
    if (open && flow === "service" && context?.unit_id) {
      api.get(`/api/field-photos/service-units/${context.unit_id}`).then((r) => setUnitPhotos(r.data)).catch(() => setUnitPhotos([]));
    }
  }, [open, flow, context?.unit_id]);

  function toggleItem(i) {
    setItems((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]));
  }
  function setPhotoAt(i, file) {
    setPhotos((cur) => { const next = [...cur]; next[i] = file; return next; });
  }

  async function send() {
    if (flow !== "service" && !items.length) { setErr("Pick what's missing"); return; }
    if (!description.trim()) { setErr("Describe what you found"); return; }
    if (flow !== "service") {
      const filled = photos.filter(Boolean).length;
      if (filled < 4) { setErr(`Add all 4 photos (${filled}/4 so far)`); return; }
    }
    if ((flow === "parts" || flow === "service") && !respType) { setErr("Pick who this claim is on"); return; }
    if ((flow === "parts" || flow === "service") && respType === "mfg" && !vendorId) { setErr("Select the manufacturer"); return; }
    if ((flow === "parts" || flow === "service") && respType === "trans" && !courierId) { setErr("Select the transporter"); return; }
    if ((flow === "parts" || flow === "service") && respType === "ins" && !insurer.trim()) { setErr("Name the insurer / policy"); return; }
    setErr("");
    setBusy(true);
    try {
      const body = { flow, items, description: description.trim(), ...context };
      if (amount.trim() !== "") body.amount = Number(amount);
      if (flow === "parts" || flow === "service") {
        body.responsible_type = respType;
        if (respType === "mfg") body.vendor_id = Number(vendorId);
        if (respType === "trans") body.courier_id = Number(courierId);
        if (respType === "ins") body.insurer_name = insurer;
      }
      const claim = await shortageClaimsApi.raise(body);
      for (let i = 0; i < 4; i++) {
        if (photos[i]) await shortageClaimsApi.uploadPhoto(claim.id, photos[i], PHOTO_LABELS[i]);
      }
      for (const file of extraPhotos) {
        if (file) await shortageClaimsApi.uploadPhoto(claim.id, file, "Added by raiser");
      }
      setSent(claim);
      onSent?.(claim);
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not send the claim");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Claim <span className="font-mono">{sent.claim_no}</span> sent — waiting on the Service Manager.
      </div>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100"
      >
        ⚠ {triggerLabel}
      </button>
    );
  }

  return (
    <div className="mt-3 space-y-3 rounded-md border border-amber-300 bg-amber-50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-amber-900">Report a missing item</span>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-amber-700 hover:underline">Cancel</button>
      </div>
      {flow !== "service" && (
        <div>
          <label className="text-xs uppercase tracking-wide text-slate-500">What's missing (pick all that apply)</label>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {ITEMS_MISSING.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => toggleItem(i)}
                className={`rounded-full border px-2.5 py-1 text-xs font-medium ${items.includes(i) ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 bg-white text-slate-700"}`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>
      )}
      <div>
        <label className="text-xs uppercase tracking-wide text-slate-500">Describe what you found</label>
        <textarea
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. box resealed with different tape, weight felt light, gas pressure reading near zero..."
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </div>
      {flow === "service" ? (
        <div>
          <label className="text-xs uppercase tracking-wide text-slate-500">
            Photos from serial verification ({unitPhotos.length}) — attached automatically, no need to retake them
          </label>
          {unitPhotos.length > 0 ? (
            <div className="mt-1 grid grid-cols-4 gap-2">
              {unitPhotos.map((p, i) => (
                <a key={p.id} href={toDownloadUrl(p.file_path)} target="_blank" rel="noreferrer" className="block">
                  <img
                    src={toDownloadUrl(p.file_path)}
                    alt={`Serial verification photo ${i + 1}`}
                    className="h-16 w-full rounded border border-slate-200 object-cover"
                  />
                </a>
              ))}
            </div>
          ) : (
            <div className="mt-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
              No photos found from serial verification for this unit yet.
            </div>
          )}
          <label className="mt-2 block text-xs uppercase tracking-wide text-slate-500">Add your own photos — optional</label>
          <input
            type="file" accept=".jpg,.jpeg,.png" multiple
            onChange={(e) => setExtraPhotos((cur) => [...cur, ...Array.from(e.target.files || [])])}
            className="mt-1 block w-full text-xs"
          />
          {extraPhotos.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {extraPhotos.map((f, i) => (
                <li key={i} className="flex items-center justify-between text-xs text-emerald-700">
                  <span className="truncate">✓ {f.name}</span>
                  <button type="button" onClick={() => setExtraPhotos((cur) => cur.filter((_, j) => j !== i))} className="ml-2 text-slate-400 hover:text-rose-600">✕</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div>
          <label className="text-xs uppercase tracking-wide text-slate-500">
            4 photos required ({photos.filter(Boolean).length}/4) — box as received, the seal/tape, the empty space, the item's label on the box
          </label>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {PHOTO_LABELS.map((label, i) => (
              <div key={i} className="rounded-md border border-dashed border-slate-300 bg-white p-2">
                <p className="truncate text-xs text-slate-500">{label}</p>
                <input type="file" accept=".jpg,.jpeg,.png" onChange={(e) => setPhotoAt(i, e.target.files?.[0] || null)} className="mt-1 block w-full text-xs" />
                {photos[i] && <p className="mt-1 truncate text-xs text-emerald-700">✓ {photos[i].name}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
      <div>
        <label className="text-xs uppercase tracking-wide text-slate-500">Claimed amount (₹) — optional</label>
        <input
          type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)}
          placeholder="At or under ₹2,500, Service Manager can close this claim outright"
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </div>
      {(flow === "parts" || flow === "service") && (
        <div className="rounded-md border border-slate-200 bg-white p-2">
          <label className="text-xs uppercase tracking-wide text-slate-500">Term of claim — on whom (required)</label>
          <div className="mt-2 grid grid-cols-4 gap-2">
            {(flow === "service"
              ? [["mfg", "Manufacturer"], ["company", "Company"], ["ins", "Insurance"], ["trans", "Transport"]]
              : [["mfg", "Manufacturer"], ["trans", "Transporter"], ["ins", "Insurance"], ["company", "Company"]]
            ).map(([k, l]) => (
              <button
                key={k} type="button" onClick={() => setRespType(k === respType ? "" : k)}
                className={`rounded-md border px-2 py-2 text-xs font-semibold ${respType === k ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 text-slate-600"}`}
              >
                {l}
              </button>
            ))}
          </div>
          {respType === "mfg" && (
            <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm">
              <option value="">Select manufacturer</option>
              {parties.vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          )}
          {respType === "trans" && (
            <select value={courierId} onChange={(e) => setCourierId(e.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm">
              <option value="">Select transporter</option>
              {parties.couriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          )}
          {respType === "ins" && (
            <input value={insurer} onChange={(e) => setInsurer(e.target.value)} placeholder="Insurer / policy" className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
          )}
        </div>
      )}
      {err && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{err}</p>}
      <div className="flex justify-end">
        <button type="button" disabled={busy} onClick={send} className="rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-50">
          {busy ? "Sending…" : "Send the claim"}
        </button>
      </div>
    </div>
  );
}
