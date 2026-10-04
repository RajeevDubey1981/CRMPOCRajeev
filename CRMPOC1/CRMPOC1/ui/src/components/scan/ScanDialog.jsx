import { useEffect, useRef, useState } from "react";

import Modal from "../Modal.jsx";
import CameraScan from "./CameraScan.jsx";
import { isSoundOn, playError, playSuccess, setSoundOn, unlockAudio } from "./scanFeedback.js";

const MODES = [["camera", "Phone camera"], ["scanner", "Barcode scanner"], ["type", "Type it"]];
const SERIAL_RE = /^[A-Z0-9][A-Z0-9\-_/.]{2,99}$/;

function isPhone() {
  return typeof navigator !== "undefined" && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
}

// One scan, then the dialog hands the code back. A good scan beeps and shows a green message, a wrong one buzzes and stays open.
export default function ScanDialog({ open, onClose, onCode, title = "Scan a serial number" }) {
  const [mode, setMode] = useState(isPhone() ? "camera" : "scanner");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [sound, setSound] = useState(isSoundOn());
  const inputRef = useRef(null);
  const done = useRef(false);

  useEffect(() => {
    if (!open) return undefined;
    setText("");
    setResult(null);
    done.current = false;
    const t = setTimeout(() => inputRef.current?.focus(), 60);
    return () => clearTimeout(t);
  }, [open, mode]);

  function submit(raw) {
    if (done.current) return;
    const value = String(raw || "").trim().toUpperCase();
    if (!value) return;
    if (!SERIAL_RE.test(value)) {
      playError();
      setResult({ ok: false, text: `${value} is not a valid serial number. Use letters, numbers, dash, slash or dot (3 to 100 characters). Try again.` });
      return;
    }
    done.current = true;
    playSuccess();
    setResult({ ok: true, text: `Scanned successfully: ${value}` });
    setTimeout(() => onCode(value), 700);
  }

  function toggleSound() {
    const next = !sound;
    setSound(next);
    setSoundOn(next);
    if (next) { unlockAudio(); playSuccess(); }
  }

  return (
    <Modal open={open} onClose={onClose} title={title} maxWidth="max-w-md">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          {MODES.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => { unlockAudio(); setMode(key); }}
              className={`rounded-full px-3 py-1 text-sm ${mode === key ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
            >
              {label}
            </button>
          ))}
          <button type="button" onClick={toggleSound} className="ml-auto text-xs text-slate-600 underline">
            Sound and vibration: {sound ? "on" : "off"}
          </button>
        </div>

        {result && (
          <div
            role="status"
            aria-live="polite"
            className={`rounded-md px-3 py-3 text-sm font-medium ${result.ok ? "bg-emerald-100 text-emerald-900" : "bg-rose-100 text-rose-900"}`}
          >
            {result.ok ? "✔ " : "✖ "}{result.text}
          </div>
        )}

        {mode === "camera" && <CameraScan onCode={submit} />}
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit(text);
              setText("");
            }
          }}
          placeholder={mode === "type" ? "Type the serial and press Enter" : "A barcode scanner types here and presses Enter by itself"}
          autoComplete="off"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <p className="text-xs text-slate-500">Works with the phone camera, a USB or Bluetooth barcode scanner, a QR code, or an EAN barcode.</p>
      </div>
    </Modal>
  );
}
