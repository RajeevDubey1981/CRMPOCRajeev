import { useEffect, useState } from "react";

import { api } from "../../api/client.js";

function fmtSize(bytes) {
  if (!bytes) return "";
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Files in a conversation are not public links: they are fetched with the person's own sign-in, so only the people
// in the conversation can open or download them.
async function fetchBlob(url, inline) {
  const res = await api.get(url, { params: inline ? { inline: true } : undefined, responseType: "blob" });
  return res.data;
}

function saveBlob(blob, name) {
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = name || "file";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 2000);
}

/** One attached file: a picture shows as a thumbnail (click to open it large), anything else as a download button. */
export default function QueryAttachment({ file, size = "message" }) {
  const [src, setSrc] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!file.is_image) return undefined;
    let url = "";
    let alive = true;
    fetchBlob(file.url, true)
      .then((blob) => { if (alive) { url = URL.createObjectURL(blob); setSrc(url); } })
      .catch(() => alive && setFailed(true));
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [file.url, file.is_image]);

  async function download(e) {
    e?.preventDefault();
    setBusy(true);
    try {
      saveBlob(await fetchBlob(file.url, false), file.file_name);
    } catch {
      alert("The file could not be downloaded. It may no longer be available.");
    } finally {
      setBusy(false);
    }
  }

  const thumb = size === "small" ? "h-16 w-20 object-cover" : "max-h-48 max-w-full object-contain";

  if (file.is_image && !failed) {
    return (
      <div className="group relative inline-block overflow-hidden rounded-lg border border-slate-200 bg-white" title={file.file_name}>
        {src ? (
          <a href={src} target="_blank" rel="noreferrer"><img src={src} alt={file.file_name} className={thumb} /></a>
        ) : (
          <div className={`grid place-items-center text-xs text-slate-400 ${size === "small" ? "h-16 w-20" : "h-24 w-40"}`}>Loading…</div>
        )}
        {size !== "small" && (
          <button type="button" onClick={download} disabled={busy} className="absolute bottom-1 right-1 rounded bg-slate-900/70 px-1.5 py-0.5 text-[11px] text-white opacity-0 transition group-hover:opacity-100">
            {busy ? "…" : "Download"}
          </button>
        )}
      </div>
    );
  }
  return (
    <button type="button" onClick={download} disabled={busy} title="Download" className="inline-flex max-w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-left text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-60">
      <span aria-hidden="true">📎</span>
      <span className="min-w-0 truncate">{file.file_name}</span>
      <span className="shrink-0 text-slate-400">{fmtSize(file.size_bytes)}</span>
      <span className="shrink-0 font-semibold text-brand-700">{busy ? "…" : "Download"}</span>
    </button>
  );
}
