import { useEffect, useRef, useState } from "react";

import { callsApi } from "../api/calls.js";

// The recording needs the login token, which an <audio src> can't send, so it is fetched as a file
// the first time it is asked for and played from memory. Nothing is loaded until someone presses play.
export default function CallRecordingPlayer({ callId, compact = false }) {
  const [state, setState] = useState("idle"); // idle | loading | ready | missing | error
  const [url, setUrl] = useState("");
  const urlRef = useRef("");

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  async function load(e) {
    e?.stopPropagation?.();
    setState("loading");
    try {
      const blob = await callsApi.recording(callId);
      const next = URL.createObjectURL(blob);
      urlRef.current = next;
      setUrl(next);
      setState("ready");
    } catch (err) {
      setState(err?.response?.status === 404 ? "missing" : "error");
    }
  }

  if (state === "ready") {
    return (
      <audio controls autoPlay src={url} className={compact ? "h-8 w-full max-w-xs" : "w-full max-w-md"} onClick={(e) => e.stopPropagation()}>
        Your browser cannot play this recording.
      </audio>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={load}
        disabled={state === "loading"}
        className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
      >
        {state === "loading" ? "Loading recording..." : "Play recording"}
      </button>
      {state === "missing" && <span className="text-xs text-slate-500">The recording is not ready yet. Try again in a few minutes.</span>}
      {state === "error" && <span className="text-xs text-rose-600">Could not load the recording.</span>}
    </div>
  );
}
