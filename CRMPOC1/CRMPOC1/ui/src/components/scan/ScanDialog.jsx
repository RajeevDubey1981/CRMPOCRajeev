import { useEffect, useRef, useState } from "react";

import Modal from "../Modal.jsx";
import CameraScan from "./CameraScan.jsx";

const MODES = [["scanner", "Barcode scanner"], ["camera", "Phone camera"], ["type", "Type it"]];

function isPhone() {
  return typeof navigator !== "undefined" && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
}

// One scan, then the dialog hands the code back. A USB or Bluetooth scanner types the code and presses Enter by itself.
export default function ScanDialog({ open, onClose, onCode, title = "Scan a serial number" }) {
  const [mode, setMode] = useState(isPhone() ? "camera" : "scanner");
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    setText("");
    const t = setTimeout(() => inputRef.current?.focus(), 60);
    return () => clearTimeout(t);
  }, [open, mode]);

  function submit(raw) {
    const value = String(raw || "").trim();
    if (!value) return;
    onCode(value.toUpperCase());
  }

  return (
    <Modal open={open} onClose={onClose} title={title} maxWidth="max-w-md">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {MODES.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setMode(key)}
              className={`rounded-full px-3 py-1 text-sm ${mode === key ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
            >
              {label}
            </button>
          ))}
        </div>
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
          placeholder={mode === "type" ? "Type the serial and press Enter" : "Click here, then scan. The scanner presses Enter by itself."}
          autoComplete="off"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <p className="text-xs text-slate-500">Works with a barcode scanner, a QR code, an EAN barcode, or the phone camera.</p>
      </div>
    </Modal>
  );
}
