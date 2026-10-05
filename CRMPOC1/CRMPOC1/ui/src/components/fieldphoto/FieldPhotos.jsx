import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";
import Modal from "../Modal.jsx";

// Photos of the machine found in the field, taken against one serial, each saved with the phone's location.
// kind is "service-units" or "installation-serials"; id is the unit or serial row id.
// At least 1 photo is needed to verify a serial (the server checks it too) and at most 4 can be kept.

export const MIN_PHOTOS = 1;
export const MAX_PHOTOS = 4;

const MAX_SIDE = 1280; // longest side after shrinking, in pixels
const TARGET_BYTES = 350 * 1024; // the picture is squeezed until it is about this small
const POSITION_MAX_AGE_MS = 10 * 60 * 1000; // a location fix up to 10 minutes old is still the same place

function fmtWhen(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function fmtSize(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function getPosition({ timeout = 20000, maximumAge = 10000 } = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("This phone or browser cannot give a location."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy, at: Date.now() }),
      (err) => {
        if (err.code === 1) reject(new Error("Location is blocked. Allow location for this app, then try again."));
        else if (err.code === 3) reject(new Error("The phone took too long to find its location. Go outside or near a window and try again."));
        else reject(new Error("The phone could not find its location. Switch location on and try again."));
      },
      { enableHighAccuracy: true, timeout, maximumAge },
    );
  });
}

// Phone cameras make 3 to 10 MB pictures. Shrink right after the photo is taken: slow mobile data is the usual
// problem in the field. Returns { blob, from, to }.
async function shrink(file) {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    let blob = null;
    for (const quality of [0.75, 0.65, 0.55, 0.45]) {
      blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
      if (blob && blob.size <= TARGET_BYTES) break;
    }
    return blob ? { blob, from: file.size, to: blob.size } : { blob: file, from: file.size, to: file.size };
  } catch {
    return { blob: file, from: file.size, to: file.size };
  }
}

const STAGE_TEXT = {
  compressing: "Making the photo smaller",
  locating: "Checking your location",
  uploading: "Uploading",
  saved: "Saved",
};

export default function FieldPhotos({ kind, id, serialNo, canAdd, count, onChanged, onCountChange }) {
  const [open, setOpen] = useState(false);
  const [photos, setPhotos] = useState([]);
  const [total, setTotal] = useState(count ?? null);
  const [pos, setPos] = useState(null);
  const [posErr, setPosErr] = useState("");
  const [locating, setLocating] = useState(false);
  const [job, setJob] = useState(null); // the photo being saved: { stage, percent, preview, sizes, error, blob, position }
  const [err, setErr] = useState("");
  const [big, setBig] = useState(null);
  const input = useRef(null);
  const jobSeq = useRef(0); // each photo gets a number, so an old banner timer never wipes out the next photo

  const busy = !!job && job.stage !== "failed";
  const taken = photos.length;
  const full = taken >= MAX_PHOTOS;

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/api/field-photos/${kind}/${id}`);
      setPhotos(data);
      setTotal(data.length);
    } catch (e) {
      setErr(e.response?.data?.detail || "Could not load the photos");
    }
  }, [kind, id]);

  const locate = useCallback(async () => {
    setLocating(true);
    setPosErr("");
    try {
      setPos(await getPosition());
    } catch (e) {
      setPos(null);
      setPosErr(e.message);
    } finally {
      setLocating(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    setErr("");
    load();
    if (canAdd) locate();
  }, [open, canAdd, load, locate]);

  useEffect(() => {
    if (count == null) {
      api.get(`/api/field-photos/${kind}/${id}`).then((r) => setTotal(r.data.length)).catch(() => {});
    }
  }, [kind, id, count]);

  useEffect(() => {
    if (total != null) onCountChange?.(total);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total]);

  useEffect(() => () => { if (job?.preview) URL.revokeObjectURL(job.preview); }, [job?.preview]);

  async function send(blob, position, preview, sizes, jobId) {
    setJob({ id: jobId, stage: "uploading", percent: 45, preview, sizes, blob, position });
    try {
      const form = new FormData();
      form.append("photo", blob, "machine.jpg");
      form.append("latitude", String(position.latitude));
      form.append("longitude", String(position.longitude));
      form.append("accuracy", String(position.accuracy));
      form.append("captured_at", new Date().toISOString());
      await api.post(`/api/field-photos/${kind}/${id}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (!e.total) return;
          setJob((j) => (j && j.id === jobId ? { ...j, stage: "uploading", percent: 45 + Math.round((e.loaded / e.total) * 55) } : j));
        },
      });
      setJob((j) => (j && j.id === jobId ? { ...j, stage: "saved", percent: 100 } : j));
      await load();
      onChanged?.();
      setTimeout(() => setJob((j) => (j && j.id === jobId ? null : j)), 1600);
    } catch (e) {
      const status = e.response?.status;
      const detail = e.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join("; ")
        : detail || (status ? `The server answered ${status}.` : "No internet. Your photo is kept here. Tap Try again when you have signal.");
      setJob((j) => (j && j.id === jobId ? { ...j, stage: "failed", error: message } : j));
    }
  }

  async function onPicked(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setErr("");
    const preview = URL.createObjectURL(file);
    jobSeq.current += 1;
    const jobId = jobSeq.current;
    setJob({ id: jobId, stage: "compressing", percent: 10, preview, sizes: { from: file.size } });

    const { blob, from, to } = await shrink(file);
    const sizes = { from, to };
    setJob({ id: jobId, stage: "locating", percent: 30, preview, sizes });

    // a fresh fix if the phone gives one quickly, otherwise the one found when this window was opened
    let position = null;
    try {
      position = await getPosition({ timeout: 6000, maximumAge: 60000 });
    } catch (e) {
      if (pos && Date.now() - pos.at < POSITION_MAX_AGE_MS) position = pos;
      else {
        setJob({ id: jobId, stage: "failed", percent: 30, preview, sizes, error: e.message, blob, position: null });
        return;
      }
    }
    setPos(position);
    await send(blob, position, preview, sizes, jobId);
  }

  async function retry() {
    if (!job?.blob) return;
    let position = job.position;
    if (!position) {
      try {
        position = await getPosition({ timeout: 8000, maximumAge: 60000 });
        setPos(position);
      } catch (e) {
        setJob((j) => ({ ...j, error: e.message }));
        return;
      }
    }
    await send(job.blob, position, job.preview, job.sizes, job.id);
  }

  const accuracyOk = pos && pos.accuracy <= 100;
  const needsOne = canAdd && total === 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-2 py-1 text-xs ${
          needsOne ? "border-amber-400 bg-amber-50 font-semibold text-amber-900 hover:bg-amber-100" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
        }`}
        title="Machine photos with location"
      >
        <span aria-hidden="true">📷</span> {needsOne ? "Add photo" : "Photos"}{total != null ? ` (${total}/${MAX_PHOTOS})` : ""}
      </button>

      <Modal open={open} onClose={() => (busy ? null : setOpen(false))} title={`Machine photos${serialNo ? `, serial ${serialNo}` : ""}`} maxWidth="max-w-xl">
        <div className="space-y-3">
          {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

          <div className={`rounded-md px-3 py-2 text-sm ${taken >= MIN_PHOTOS ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
            {taken} of {MAX_PHOTOS} photos taken.{" "}
            {taken >= MIN_PHOTOS ? (full ? "That is the most you can keep." : "You can add more if needed.") : `Take at least ${MIN_PHOTOS} photo of the machine${canAdd ? " before you verify this serial" : ""}.`}
          </div>

          {canAdd && (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-800">Take a photo of the machine</div>
              <p className="mt-0.5 text-xs text-slate-500">Stand at the machine. The photo is made smaller on the phone, then saved on the server with where you are, so admin can see the place.</p>
              <div className="mt-2 text-xs">
                {locating && <span className="text-slate-600">Finding your location…</span>}
                {!locating && pos && (
                  <span className={accuracyOk ? "text-emerald-700" : "text-amber-700"}>
                    Location found, accurate to about {Math.round(pos.accuracy)} m{accuracyOk ? "" : ". Move to open sky for a better fix"}
                  </span>
                )}
                {!locating && posErr && <span className="text-rose-700">{posErr}</span>}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || locating || !pos || full || (job && job.stage === "failed")}
                  onClick={() => input.current?.click()}
                  className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {full ? "4 photos taken" : busy ? "Saving…" : "Take photo"}
                </button>
                {!locating && !pos && (
                  <button type="button" onClick={locate} className="min-h-[44px] rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50">
                    Try location again
                  </button>
                )}
              </div>
              <input ref={input} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPicked} />

              {job && (
                <div className="mt-3 rounded-md border border-slate-200 bg-white p-2">
                  <div className="flex gap-3">
                    {job.preview && <img src={job.preview} alt="Photo just taken" className="h-16 w-16 shrink-0 rounded object-cover" />}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between text-xs font-medium text-slate-700">
                        <span>{job.stage === "failed" ? "Not saved yet" : STAGE_TEXT[job.stage]}{job.stage === "uploading" ? `… ${job.percent}%` : ""}</span>
                        {job.stage === "saved" && <span className="text-emerald-700">Done</span>}
                      </div>
                      <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${job.stage === "failed" ? "bg-rose-500" : job.stage === "saved" ? "bg-emerald-600" : "bg-brand-600"}`}
                          style={{ width: `${job.percent}%` }}
                        />
                      </div>
                      {job.sizes?.to ? (
                        <div className="mt-1 text-[11px] text-slate-500">{fmtSize(job.sizes.from)} made smaller to {fmtSize(job.sizes.to)}</div>
                      ) : (
                        <div className="mt-1 text-[11px] text-slate-500">{fmtSize(job.sizes?.from || 0)}</div>
                      )}
                    </div>
                  </div>
                  {job.stage === "failed" && (
                    <div className="mt-2 space-y-2">
                      <div className="rounded bg-rose-50 px-2 py-1.5 text-xs text-rose-700">{job.error}</div>
                      <div className="flex gap-2">
                        <button type="button" onClick={retry} className="min-h-[44px] flex-1 rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white">Try again</button>
                        <button type="button" onClick={() => setJob(null)} className="min-h-[44px] flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm">Discard</button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {photos.length === 0 && !job && <p className="text-sm text-slate-500">No photos saved yet.</p>}
          <div className="grid grid-cols-2 gap-3">
            {photos.map((p, i) => (
              <div key={p.id} className="rounded-md border border-slate-200 bg-white p-2">
                <button type="button" onClick={() => setBig(p)} className="block w-full">
                  <img src={toDownloadUrl(p.file_path)} alt={`Machine photo ${i + 1}`} className="h-32 w-full rounded object-cover" />
                </button>
                <div className="mt-1.5 text-xs text-slate-600">
                  <div className="font-medium text-slate-800">Photo {i + 1} of {MAX_PHOTOS}</div>
                  <div>{fmtWhen(p.captured_at || p.created_at)}{p.uploaded_by_name ? `, ${p.uploaded_by_name}` : ""}</div>
                  <div className="font-mono">{p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}{p.accuracy_m != null ? ` (±${Math.round(p.accuracy_m)} m)` : ""}</div>
                  <a href={p.map_url} target="_blank" rel="noreferrer" className="font-medium text-sky-700 underline">Open on the map</a>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-slate-400">Saved on the INDcool server, with the time and place. Admin sees them on this same serial.</p>
        </div>
      </Modal>

      <Modal open={!!big} onClose={() => setBig(null)} title="Machine photo" maxWidth="max-w-3xl">
        {big && (
          <div className="space-y-2">
            <img src={toDownloadUrl(big.file_path)} alt="Machine" className="max-h-[70vh] w-full rounded object-contain" />
            <div className="text-xs text-slate-600">
              {fmtWhen(big.captured_at || big.created_at)}. {big.latitude.toFixed(6)}, {big.longitude.toFixed(6)}.{" "}
              <a href={big.map_url} target="_blank" rel="noreferrer" className="font-medium text-sky-700 underline">Open on the map</a>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
