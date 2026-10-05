import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";
import Modal from "../Modal.jsx";

// Photos of the machine found in the field, taken against one serial, each saved with the phone's location.
// kind is "service-units" or "installation-serials"; id is the unit or serial row id.

const MAX_SIDE = 1600;

function fmtWhen(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function getPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("This phone or browser cannot give a location."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      (err) => {
        if (err.code === 1) reject(new Error("Location is blocked. Allow location for this app, then try again."));
        else if (err.code === 3) reject(new Error("The phone took too long to find its location. Go outside or near a window and try again."));
        else reject(new Error("The phone could not find its location. Switch location on and try again."));
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 10000 },
    );
  });
}

// Phone cameras make 4 to 10 MB pictures. Shrink them before sending: slow mobile data is the usual problem in the field.
async function shrink(file) {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
    return blob || file;
  } catch {
    return file;
  }
}

export default function FieldPhotos({ kind, id, serialNo, canAdd, count, onChanged }) {
  const [open, setOpen] = useState(false);
  const [photos, setPhotos] = useState([]);
  const [total, setTotal] = useState(count ?? null);
  const [pos, setPos] = useState(null);
  const [posErr, setPosErr] = useState("");
  const [locating, setLocating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [big, setBig] = useState(null);
  const input = useRef(null);

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

  async function onPicked(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setErr("");
    setBusy(true);
    try {
      // a fresh fix for the moment the picture was taken; a photo without a location is not accepted
      const here = await getPosition();
      setPos(here);
      const blob = await shrink(file);
      const form = new FormData();
      form.append("photo", blob, "machine.jpg");
      form.append("latitude", String(here.latitude));
      form.append("longitude", String(here.longitude));
      form.append("accuracy", String(here.accuracy));
      form.append("captured_at", new Date().toISOString());
      await api.post(`/api/field-photos/${kind}/${id}`, form, { headers: { "Content-Type": "multipart/form-data" } });
      await load();
      onChanged?.();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Could not save the photo");
    } finally {
      setBusy(false);
    }
  }

  const accuracyOk = pos && pos.accuracy <= 100;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
        title="Machine photos with location"
      >
        <span aria-hidden="true">📷</span> Photos{total != null ? ` (${total})` : ""}
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title={`Machine photos${serialNo ? `, serial ${serialNo}` : ""}`} maxWidth="max-w-xl">
        <div className="space-y-3">
          {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

          {canAdd && (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-800">Take a photo of the machine</div>
              <p className="mt-0.5 text-xs text-slate-500">Stand at the machine. The photo is saved with where you are, so admin can see the place.</p>
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
                  disabled={busy || locating || !pos}
                  onClick={() => input.current?.click()}
                  className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {busy ? "Saving…" : "Take photo"}
                </button>
                {!locating && !pos && (
                  <button type="button" onClick={locate} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50">
                    Try location again
                  </button>
                )}
              </div>
              <input ref={input} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPicked} />
            </div>
          )}

          {photos.length === 0 && <p className="text-sm text-slate-500">No photos yet.</p>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {photos.map((p) => (
              <div key={p.id} className="rounded-md border border-slate-200 bg-white p-2">
                <button type="button" onClick={() => setBig(p)} className="block w-full">
                  <img src={toDownloadUrl(p.file_path)} alt={`Machine ${p.serial_no || ""}`} className="h-40 w-full rounded object-cover" />
                </button>
                <div className="mt-1.5 text-xs text-slate-600">
                  <div>{fmtWhen(p.captured_at || p.created_at)}{p.uploaded_by_name ? `, ${p.uploaded_by_name}` : ""}</div>
                  <div className="font-mono">{p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}{p.accuracy_m != null ? ` (±${Math.round(p.accuracy_m)} m)` : ""}</div>
                  <a href={p.map_url} target="_blank" rel="noreferrer" className="font-medium text-sky-700 underline">Open the place on the map</a>
                </div>
              </div>
            ))}
          </div>
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
