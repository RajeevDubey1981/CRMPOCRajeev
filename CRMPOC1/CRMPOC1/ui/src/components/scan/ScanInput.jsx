import { useState } from "react";

import ScanDialog from "./ScanDialog.jsx";

export function BarcodeIcon({ className = "h-5 w-5" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <path d="M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2" />
      <path d="M8 8v8M11 8v8M14 8v8M17 8v8" />
    </svg>
  );
}

// A small button that opens the scan dialog and hands back one code.
export function ScanButton({ onScan, disabled = false, className = "", title = "Scan with a barcode scanner or the phone camera" }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        title={title}
        aria-label="Scan serial number"
        className={`inline-flex items-center justify-center rounded-md border border-slate-300 bg-white p-1.5 text-slate-600 hover:bg-slate-50 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
      >
        <BarcodeIcon />
      </button>
      <ScanDialog
        open={open}
        onClose={() => setOpen(false)}
        onCode={(code) => { setOpen(false); onScan(code); }}
      />
    </>
  );
}

// A text input with the scan button inside its right edge. onValue gets the new string, typed or scanned.
export default function ScanInput({ value, onValue, className = "", wrapperClassName = "", disabled = false, ...rest }) {
  return (
    <div className={`relative ${wrapperClassName}`}>
      <input
        value={value}
        onChange={(e) => onValue(e.target.value)}
        disabled={disabled}
        className={`${className} pr-12`}
        {...rest}
      />
      <ScanButton
        disabled={disabled}
        onScan={onValue}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 !p-1"
      />
    </div>
  );
}
