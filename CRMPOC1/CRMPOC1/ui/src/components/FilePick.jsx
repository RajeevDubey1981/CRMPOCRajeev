import { useRef, useState } from "react";

// A file chooser that tells the truth: the browser's own box says "No file chosen" even when a file was uploaded earlier.
export default function FilePick({ accept, disabled, uploaded, onPick, className = "" }) {
  const ref = useRef(null);
  const [name, setName] = useState("");
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <input
        ref={ref}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          const file = event.target.files?.[0] || null;
          setName(file ? file.name : "");
          onPick(file);
          event.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => ref.current?.click()}
        className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        {uploaded ? "Replace file" : "Choose file"}
      </button>
      <span className={`text-sm ${uploaded || name ? "font-medium text-emerald-700" : "text-slate-500"}`}>
        {name ? `Sent: ${name}` : uploaded ? "A file is already uploaded" : "No file chosen"}
      </span>
    </div>
  );
}
