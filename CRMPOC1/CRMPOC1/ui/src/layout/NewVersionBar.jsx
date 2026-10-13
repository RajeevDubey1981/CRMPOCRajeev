import { useEffect, useRef, useState } from "react";

// Browsers sometimes keep an old copy of the CRM page, so a new version does not show until a hard refresh.
// This asks the server which build is running; when it is not the build this page started with, it offers a refresh.
const EVERY_MS = 90_000;

async function runningBuild() {
  const r = await fetch("/health", { cache: "no-store" });
  if (!r.ok) return null;
  const data = await r.json();
  return data?.build || null;
}

export default function NewVersionBar() {
  const first = useRef(null);
  const [fresh, setFresh] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    async function check() {
      try {
        const build = await runningBuild();
        if (!live || !build) return;
        if (first.current === null) first.current = build;
        else if (build !== first.current) setFresh(true);
      } catch { /* offline for a moment: try again later */ }
    }
    check();
    const timer = setInterval(check, EVERY_MS);
    const onShow = () => { if (document.visibilityState === "visible") check(); };
    document.addEventListener("visibilitychange", onShow);
    return () => { live = false; clearInterval(timer); document.removeEventListener("visibilitychange", onShow); };
  }, []);

  async function refresh() {
    setBusy(true);
    try { await fetch("/index.html", { cache: "reload" }); } catch { /* reload anyway */ }
    window.location.reload();
  }

  if (!fresh) return null;
  return (
    <div role="status" className="s-pop fixed inset-x-0 top-0 z-[80] flex flex-wrap items-center justify-center gap-3 bg-indcool-navy px-4 py-2 text-sm font-medium text-white shadow-lg">
      <span>A new version of the CRM is ready.</span>
      <button type="button" onClick={refresh} disabled={busy} className="s-press rounded-md bg-indcool-lime px-3 py-1 text-xs font-bold text-indcool-navy hover:brightness-95 disabled:opacity-60">{busy ? "Refreshing..." : "Refresh now"}</button>
    </div>
  );
}
