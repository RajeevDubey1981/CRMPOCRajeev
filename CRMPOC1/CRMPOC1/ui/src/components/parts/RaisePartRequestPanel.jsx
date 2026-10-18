import { useState } from "react";

import { partsApi, REQUEST_KINDS, REQUIRED_PHOTOS } from "../../api/parts.js";

const PHOTO_LABELS = {
  part: ["Wide shot of the unit", "Close-up of the damage", "The part's label or code", "With the unit or its box"],
  unit: ["Wide shot of the unit", "Close-up of the fault", "Serial number plate", "With the unit or its box", "Any other angle"],
};

/**
 * A small, self-contained "raise a request" panel to drop into a service/installation step. Collapsed to one
 * button by default so it never changes the look of the step it sits in until an engineer actually needs it.
 */
export default function RaisePartRequestPanel({
  context,
  allowedKinds = ["part", "expense", "ondemand"],
  triggerLabel = "Can't complete — request a part or raise an expense",
  onSent,
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState(allowedKinds[0] || "part");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState([]); // File[]
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [sent, setSent] = useState(null);

  const need = REQUIRED_PHOTOS[kind] || 0;
  const labels = PHOTO_LABELS[kind] || [];

  function setPhotoAt(i, file) {
    setPhotos((current) => {
      const next = [...current];
      next[i] = file;
      return next;
    });
  }

  async function send() {
    if (!description.trim()) { setErr("Describe what's needed"); return; }
    const filled = photos.filter(Boolean).length;
    if (need && filled < need) { setErr(`Add all ${need} photos (${filled}/${need} so far)`); return; }
    setErr("");
    setBusy(true);
    try {
      const req = await partsApi.raiseRequest({ kind, description: description.trim(), ...context });
      for (let i = 0; i < photos.length; i++) {
        if (photos[i]) await partsApi.uploadPhoto(req.id, photos[i], labels[i] || null);
      }
      setSent(req);
      onSent?.(req);
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not send the request");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Request <span className="font-mono">{sent.request_no}</span> sent — waiting on the Service Manager. You can carry on; this step stays paused until it's sorted.
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
        <span className="text-sm font-medium text-amber-900">Raise a request</span>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-amber-700 hover:underline">Cancel</button>
      </div>
      <div>
        <label className="text-xs uppercase tracking-wide text-slate-500">What is this for</label>
        <select value={kind} onChange={(e) => { setKind(e.target.value); setPhotos([]); }} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          {REQUEST_KINDS.filter((k) => allowedKinds.includes(k.value)).map((k) => (
            <option key={k.value} value={k.value}>{k.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs uppercase tracking-wide text-slate-500">Describe it</label>
        <textarea
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={kind === "part" ? "Which part, and why" : kind === "unit" ? "Why the whole unit needs replacing" : "What this is for"}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </div>
      {need > 0 && (
        <div>
          <label className="text-xs uppercase tracking-wide text-slate-500">
            {need} photos required ({photos.filter(Boolean).length}/{need})
          </label>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {Array.from({ length: need }).map((_, i) => (
              <div key={i} className="rounded-md border border-dashed border-slate-300 bg-white p-2">
                <p className="truncate text-xs text-slate-500">{labels[i]}</p>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png"
                  onChange={(e) => setPhotoAt(i, e.target.files?.[0] || null)}
                  className="mt-1 block w-full text-xs"
                />
                {photos[i] && <p className="mt-1 truncate text-xs text-emerald-700">✓ {photos[i].name}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
      {err && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{err}</p>}
      <div className="flex justify-end">
        <button
          type="button"
          disabled={busy}
          onClick={send}
          className="rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-50"
        >
          {busy ? "Sending…" : "Send the request"}
        </button>
      </div>
    </div>
  );
}
