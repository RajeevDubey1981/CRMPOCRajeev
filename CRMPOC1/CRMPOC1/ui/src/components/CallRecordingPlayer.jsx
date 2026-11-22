import { useEffect, useRef, useState } from "react";

import { callsApi } from "../api/calls.js";

const CLAY = "#c2410c";

function PlayIcon({ size = 11 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" aria-hidden="true">
      <path d="M4 2.2v9.6a.6.6 0 0 0 .9.5l7.6-4.8a.6.6 0 0 0 0-1L4.9 1.7A.6.6 0 0 0 4 2.2z" fill="#fff" />
    </svg>
  );
}

function PauseIcon({ size = 11 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" aria-hidden="true">
      <rect x="3" y="2" width="2.8" height="10" rx="1" fill="#fff" />
      <rect x="8.2" y="2" width="2.8" height="10" rx="1" fill="#fff" />
    </svg>
  );
}

function Bars({ className = "" }) {
  return (
    <svg width="20" height="12" viewBox="0 0 22 12" fill="currentColor" aria-hidden="true" className={className}>
      <rect x="0" y="4" width="2" height="4" rx="1" />
      <rect x="4" y="1" width="2" height="10" rx="1" />
      <rect x="8" y="3" width="2" height="6" rx="1" />
      <rect x="12" y="0" width="2" height="12" rx="1" />
      <rect x="16" y="2.5" width="2" height="7" rx="1" />
      <rect x="20" y="4" width="2" height="4" rx="1" />
    </svg>
  );
}

function fmt(sec) {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// The recording needs the login token, which an <audio src> can't send, so it is fetched as a file
// the first time it is asked for and played from memory. Nothing is loaded until someone presses play.
// `icon` gives the small waveform chip used in lists; `mini` drops the waveform for tight spots.
export default function CallRecordingPlayer({ callId, compact = false, icon = false, mini = false }) {
  const [state, setState] = useState("idle"); // idle | loading | ready | missing | error | unplayable
  const [playing, setPlaying] = useState(false);
  const [pos, setPos] = useState(0);
  const [dur, setDur] = useState(0);
  const [url, setUrl] = useState("");
  const [drive, setDrive] = useState(null); // { preview_url, open_url } when the recording is kept in Google Drive
  const urlRef = useRef("");
  const audioRef = useRef(null);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  async function load(e) {
    e?.stopPropagation?.();
    setState("loading");
    try {
      // Recordings are kept in Google Drive; only calls without a Drive link fall back to a copy held by the CRM.
      try {
        const link = await callsApi.recordingLink(callId);
        if (link?.preview_url) {
          setDrive(link);
          setState("idle");
          return;
        }
      } catch (linkErr) {
        if (linkErr?.response && linkErr.response.status !== 404) throw linkErr;
      }
      const blob = await callsApi.recording(callId);
      if (!blob || blob.size === 0) {
        setState("missing");
        return;
      }
      // Some servers send the audio without a usable type; the browser then refuses to play it.
      const typed = blob.type && blob.type.startsWith("audio/") ? blob : new Blob([blob], { type: "audio/wav" });
      const next = URL.createObjectURL(typed);
      urlRef.current = next;
      setUrl(next);
      setState("ready");
    } catch (err) {
      setState(err?.response?.status === 404 ? "missing" : "error");
    }
  }

  // Start playing as soon as the file is in place, and say so if the browser refuses.
  useEffect(() => {
    if (state !== "ready" || !audioRef.current) return;
    audioRef.current.play().catch((err) => {
      if (err?.name === "NotSupportedError") setState("unplayable");
    });
  }, [state, url]);

  function toggle(e) {
    e?.stopPropagation?.();
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => setState("unplayable"));
    else a.pause();
  }

  const failed = state === "missing" || state === "error" || state === "unplayable";
  const failTip =
    state === "missing"
      ? "The recording is not ready yet. Try again in a few minutes."
      : state === "unplayable"
        ? "This browser cannot play the recording. Try again or use another browser."
        : "Could not load the recording. Try again.";

  const driveModal = drive ? (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={(e) => { e.stopPropagation(); setDrive(null); }}>
      <div className="w-full max-w-md rounded-lg bg-white p-3 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-800">Call recording</span>
          <button type="button" onClick={() => setDrive(null)} className="rounded px-2 py-0.5 text-slate-500 hover:bg-slate-100">Close</button>
        </div>
        <iframe title="Call recording" src={drive.preview_url} allow="autoplay" className="h-24 w-full rounded border border-slate-200" />
        <p className="mt-2 text-xs text-slate-500">
          Plays from Google Drive. If it asks you to sign in, use the Google account that has access.{" "}
          <a href={drive.open_url} target="_blank" rel="noreferrer" className="text-sky-700 underline">Open in Drive</a>
        </p>
      </div>
    </div>
  ) : null;

  if (icon) {
    const base = "inline-flex items-center rounded-full border transition-colors";
    const size = mini ? "h-6 gap-0 p-[2px]" : "h-[30px] gap-1.5 py-[3px] pl-[3px] pr-2.5";
    const dot = (
      <span
        className="inline-flex shrink-0 items-center justify-center rounded-full"
        style={{ width: mini ? 20 : 24, height: mini ? 20 : 24, background: failed ? "#b45309" : CLAY }}
      >
        {state === "loading" ? (
          <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        ) : playing ? (
          <PauseIcon size={mini ? 9 : 10} />
        ) : (
          <PlayIcon size={mini ? 9 : 10} />
        )}
      </span>
    );

    return (
      <span className="inline-flex items-center" onClick={(e) => e.stopPropagation()}>
        {driveModal}
        <button
          type="button"
          onClick={state === "ready" ? toggle : load}
          disabled={state === "loading"}
          title={failed ? failTip : playing ? "Pause recording" : "Play call recording"}
          aria-label={failed ? failTip : playing ? "Pause recording" : "Play call recording"}
          className={`${base} ${size} group ${failed ? "border-amber-300 bg-amber-50 text-amber-700" : "border-slate-300 bg-white text-slate-500 hover:border-orange-300"} disabled:opacity-70`}
        >
          {dot}
          {!mini && state !== "ready" && <Bars className="text-slate-400 group-hover:text-orange-700" />}
          {!mini && state === "ready" && (
            <span className="font-mono text-[10.5px] tabular-nums text-slate-600">
              {fmt(pos)}
              {dur ? ` / ${fmt(dur)}` : ""}
            </span>
          )}
        </button>
        {state === "ready" && (
          <audio
            ref={audioRef}
            src={url}
            preload="auto"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            onTimeUpdate={(e) => setPos(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => setDur(e.currentTarget.duration)}
            onError={() => setState("unplayable")}
          />
        )}
      </span>
    );
  }

  if (state === "ready") {
    return (
      <audio
        ref={audioRef}
        controls
        src={url}
        className={compact ? "h-8 w-full max-w-xs" : "w-full max-w-md"}
        onClick={(e) => e.stopPropagation()}
        onError={() => setState("unplayable")}
      >
        Your browser cannot play this recording.
      </audio>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
      {driveModal}
      <button
        type="button"
        onClick={load}
        disabled={state === "loading"}
        className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
      >
        {state === "loading" ? "Loading recording..." : "Play recording"}
      </button>
      {failed && <span className={`text-xs ${state === "missing" ? "text-slate-500" : "text-rose-600"}`}>{failTip}</span>}
    </div>
  );
}
