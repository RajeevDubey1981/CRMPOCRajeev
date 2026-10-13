import { useRef, useState } from "react";

import { partnerRegistrationsApi } from "../../api/partnerRegistrations.js";
import { toDownloadUrl } from "../../utils/downloadUrl.js";

const ACCEPT = ".pdf,.jpg,.jpeg,.png";
const MAX_MB = 10;

const fmtDay = (v) => (v ? new Date(`${v}T00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—");
const fmtAt = (v) => (v ? new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(String(v)) ? v : `${v}Z`).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }) : "");
const sizeText = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

function errText(e) {
  const d = e.response?.data?.detail;
  return Array.isArray(d) ? d.map((x) => x.msg).join("; ") : d || "That did not work. Try again";
}

/**
 * The signed paper copy of the partner agreement. Admin and Sub Admin upload the scan; with sharing on it also shows in
 * the partner's own documents. Replace, hide and remove are kept in a small history.
 */
export default function AgreementHardCopy({ registrationId, agreement: given, canEdit, onChanged }) {
  // before the approval there is no agreement yet; the paper copy can still be kept
  const agreement = given || { agreement_no: null, is_signed: false, signing_started: false, hard_copy_received: false, hard_copy_events: [] };
  const [file, setFile] = useState(null);
  const [receivedOn, setReceivedOn] = useState(today());
  const [note, setNote] = useState("");
  const [share, setShare] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [over, setOver] = useState(false);
  const input = useRef(null);

  function choose(f) {
    setErr("");
    if (!f) return;
    if (!/\.(pdf|jpe?g|png)$/i.test(f.name)) { setErr("Choose a PDF, JPG or PNG file"); return; }
    if (f.size > MAX_MB * 1048576) { setErr(`The file is over ${MAX_MB} MB. Scan it at a lower quality`); return; }
    setFile(f);
  }
  async function run(fn) {
    setBusy(true);
    setErr("");
    try { onChanged(await fn()); return true; } catch (e) { setErr(errText(e)); return false; } finally { setBusy(false); }
  }
  async function save() {
    if (!file) return;
    if (await run(() => partnerRegistrationsApi.uploadHardCopy(registrationId, file, { received_on: receivedOn, note, share }))) { setFile(null); setNote(""); }
  }
  function remove() {
    if (!window.confirm("Remove the signed hard copy? The partner will no longer see it.")) return;
    run(() => partnerRegistrationsApi.removeHardCopy(registrationId));
  }

  const received = agreement.hard_copy_received;
  return (
    <div className={`s-rise mt-4 rounded-xl border-2 bg-white p-4 ${received ? "border-emerald-500" : "border-slate-300"}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
        Signed agreement, hard copy
        {agreement.is_signed && <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-bold text-emerald-800">Digitally signed {fmtDay(agreement.signed_at?.slice(0, 10))}</span>}
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${received ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{received ? "Hard copy received" : "Hard copy not received yet"}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">{agreement.agreement_no ? `Agreement ${agreement.agreement_no}. ` : ""}Keep the scan of the paper the partner signed and posted to INDcool.{agreement.signing_started === false ? " The digital signing link still goes to the partner when you approve the registration." : ""}</p>
      {err && <div className="mt-2 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {received ? (
        <>
          <div className="s-pop mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="grid h-14 w-11 shrink-0 place-items-center rounded border border-slate-300 bg-white text-[10px] font-extrabold text-rose-600">{(agreement.hard_copy_name || "").split(".").pop().toUpperCase().slice(0, 4)}</div>
            <div className="min-w-0 flex-1">
              <div className="break-words text-sm font-semibold text-slate-800">{agreement.hard_copy_name}</div>
              <div className="text-xs text-slate-500">Received {fmtDay(agreement.hard_copy_received_on)} · uploaded by {agreement.hard_copy_by_name || "Admin"} on {fmtAt(agreement.hard_copy_at)}</div>
              {agreement.hard_copy_note && <div className="text-xs text-slate-500">Note: {agreement.hard_copy_note}</div>}
            </div>
            <div className="flex flex-wrap gap-2">
              <a href={toDownloadUrl(agreement.hard_copy_url)} target="_blank" rel="noreferrer" className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">View</a>
              {canEdit && <button type="button" disabled={busy} onClick={() => input.current?.click()} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">Replace</button>}
              {canEdit && <button type="button" disabled={busy} onClick={remove} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50">Remove</button>}
            </div>
            <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) { choose(f); setFile(f); } }} />
          </div>
          {file && (
            <div className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-sky-50 px-3 py-2 text-sm text-sky-900">
              Replace with <b className="break-all">{file.name}</b> ({sizeText(file.size)})
              <button type="button" disabled={busy} onClick={save} className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">{busy ? "Saving..." : "Save the new file"}</button>
              <button type="button" onClick={() => setFile(null)} className="text-xs underline">Cancel</button>
            </div>
          )}
          <div className={`mt-3 flex flex-wrap items-center gap-3 rounded-lg px-3 py-2 text-sm ${agreement.hard_copy_shared ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900"}`}>
            <span aria-hidden="true">{agreement.hard_copy_shared ? "✔" : "!"}</span>
            <div className="min-w-0 flex-1">
              <b>{agreement.hard_copy_shared ? "Shown in the partner's documents" : "Kept in the CRM only"}</b>
              <div className="text-xs opacity-80">{agreement.hard_copy_shared ? "The partner sees it next to their GST, PAN and other documents, and cannot change it." : "The partner does not see this file."}</div>
            </div>
            {canEdit && <button type="button" disabled={busy} onClick={() => run(() => partnerRegistrationsApi.shareHardCopy(registrationId, !agreement.hard_copy_shared))} className="rounded-md border border-current px-3 py-1 text-xs font-semibold disabled:opacity-50">{agreement.hard_copy_shared ? "Hide from the partner" : "Show to the partner"}</button>}
          </div>
        </>
      ) : canEdit ? (
        <>
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload the signed hard copy"
            onClick={() => input.current?.click()}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") input.current?.click(); }}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files?.[0]); }}
            className={`s-lift mt-3 cursor-pointer rounded-xl border-2 border-dashed px-4 py-5 text-center transition-colors ${over ? "border-indcool-blue bg-sky-50" : "border-slate-400 bg-slate-50 hover:bg-sky-50"}`}
          >
            <div className="text-sm font-semibold text-slate-800">{file ? file.name : "Upload the signed hard copy"}</div>
            <div className="text-xs text-slate-500">{file ? `${sizeText(file.size)} · ready to save. Click to choose another file.` : `Drop the scanned PDF or photo here, or click to choose. PDF, JPG or PNG, up to ${MAX_MB} MB.`}</div>
            <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }} />
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600" htmlFor="hc-date">Date the hard copy was received
              <input id="hc-date" type="date" value={receivedOn} max={today()} onChange={(e) => setReceivedOn(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-normal text-slate-800" />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600" htmlFor="hc-note">Note (optional)
              <input id="hc-note" value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="For example: received by courier, 3 pages" className="rounded-md border border-slate-300 px-3 py-2 text-sm font-normal text-slate-800" />
            </label>
          </div>
          <label className="mt-3 flex items-start gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sm text-slate-800">
            <input type="checkbox" className="mt-1" checked={share} onChange={(e) => setShare(e.target.checked)} />
            <span><b>Also show it in the partner's documents</b><span className="block text-xs text-slate-500">Keeps one set of papers: the file appears next to their GST, PAN and other documents.</span></span>
          </label>
          <div className="mt-3 flex items-center gap-3">
            <button type="button" disabled={busy || !file} onClick={save} className="s-press rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">{busy ? "Saving..." : "Save hard copy"}</button>
            {!file && <span className="text-xs text-slate-500">Choose the signed file first.</span>}
          </div>
        </>
      ) : (
        <p className="mt-3 text-sm text-slate-500">No hard copy has been uploaded yet.</p>
      )}

      {agreement.hard_copy_events?.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
          {agreement.hard_copy_events.slice().reverse().map((e, i) => (
            <li key={`${e.at}-${i}`} className="flex gap-2"><span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indcool-blue" /><span>{e.text}<span className="block text-[11px] text-slate-400">{fmtAt(e.at)}</span></span></li>
          ))}
        </ul>
      )}
    </div>
  );
}
