import { useEffect, useMemo, useRef, useState } from "react";

import Modal from "../Modal.jsx";
import CameraScan from "../scan/CameraScan.jsx";

const SERIAL_RE = /^[A-Z0-9][A-Z0-9\-_/.]{2,99}$/;
const MODES = [["scanner", "Barcode scanner"], ["camera", "Phone camera"], ["type", "Type it"]];
const norm = (v) => String(v || "").trim().toUpperCase();

function isPhone() {
  return typeof navigator !== "undefined" && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
}

/**
 * Scan serial numbers into the empty Serial boxes of an order's line items.
 * It does not save by itself: "Review and save" hands the changed rows to the same CSV import preview,
 * so every existing duplicate and ownership check still runs before anything is stored.
 */
export default function ScanSerialsModal({ open, onClose, scopeLabel, items, allItems, isLocked, onReview }) {
  const [mode, setMode] = useState(isPhone() ? "camera" : "scanner");
  const [slots, setSlots] = useState({});
  const [target, setTarget] = useState(null);
  const [log, setLog] = useState([]);
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  const editable = useMemo(() => (items || []).filter((it) => !isLocked(it)), [items, isLocked]);
  const lockedCount = (items || []).length - editable.length;

  useEffect(() => {
    if (!open) return;
    const next = {};
    (items || []).forEach((it) => { next[it.id] = { a: it.serial_no || "", b: it.serial_no_2 || "" }; });
    setSlots(next);
    setTarget(null);
    setLog([]);
    setText("");
  }, [open, items]);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 80);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [open, mode]);

  const slotOrder = useMemo(() => {
    const out = [];
    editable.forEach((it) => {
      const count = Number(it.serial_count ?? 1);
      if (count >= 1) out.push([it.id, "a"]);
      if (count >= 2) out.push([it.id, "b"]);
    });
    return out;
  }, [editable]);

  const itemCodes = useMemo(() => new Set((items || []).map((it) => norm(it.item_code)).filter(Boolean)), [items]);
  const editableIds = useMemo(() => new Set(editable.map((it) => it.id)), [editable]);

  function note(kind, message) {
    setLog((cur) => [...cur.slice(-3), { kind, message }]);
  }

  function handleCode(raw) {
    const v = norm(raw);
    if (!v) return;
    if (itemCodes.has(v)) {
      note("info", `${v} is the item barcode, not a serial number. Nothing was filled.`);
      return;
    }
    if (!SERIAL_RE.test(v)) {
      note("bad", `${v} is not a valid serial. Use letters, numbers, dash, slash or dot (3 to 100 characters).`);
      return;
    }
    const used = new Set();
    (allItems || []).forEach((it) => {
      if (editableIds.has(it.id)) return;
      [it.serial_no, it.serial_no_2].forEach((s) => { if (s) used.add(norm(s)); });
    });
    Object.entries(slots).forEach(([id, pair]) => {
      if (!editableIds.has(Number(id))) return;
      ["a", "b"].forEach((k) => {
        if (target && String(target.id) === id && target.slot === k) return;
        if (pair[k]) used.add(norm(pair[k]));
      });
    });
    if (used.has(v)) {
      note("bad", `${v} is already on this order. A serial can only be on one unit.`);
      return;
    }
    const spot = target ? [target.id, target.slot] : slotOrder.find(([id, k]) => !slots[id]?.[k]);
    if (!spot) {
      note("warn", "Every serial box is already filled.");
      return;
    }
    const [id, k] = spot;
    setSlots((cur) => ({ ...cur, [id]: { ...cur[id], [k]: v } }));
    const rowNo = editable.findIndex((it) => it.id === id) + 1;
    note("ok", `${v} added to row ${rowNo}, Serial ${k === "a" ? 1 : 2}.`);
    setTarget(null);
  }

  function setBox(id, k, value) {
    setSlots((cur) => ({ ...cur, [id]: { ...cur[id], [k]: value.toUpperCase() } }));
  }

  const changed = editable.filter((it) => {
    const s = slots[it.id] || {};
    return norm(s.a) !== norm(it.serial_no) || norm(s.b) !== norm(it.serial_no_2);
  });

  const filled = slotOrder.filter(([id, k]) => slots[id]?.[k]).length;

  function review() {
    const serialColumnCount = Math.max(1, ...editable.map((it) => Number(it.serial_count ?? 1)));
    onReview(
      changed.map((it) => ({ item: it, serial1: norm(slots[it.id]?.a), serial2: norm(slots[it.id]?.b) })),
      Math.min(2, serialColumnCount),
    );
  }

  const badge = { ok: "bg-emerald-100 text-emerald-800", bad: "bg-rose-100 text-rose-800", info: "bg-sky-100 text-sky-800", warn: "bg-amber-100 text-amber-800" };
  const badgeText = { ok: "Added", bad: "Refused", info: "Item", warn: "Note" };

  return (
    <Modal open={open} onClose={onClose} title={`Scan serial numbers${scopeLabel ? `: ${scopeLabel}` : ""}`} maxWidth="max-w-4xl">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
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
          <span className="text-sm text-slate-600">{filled} of {slotOrder.length} serial boxes filled</span>
        </div>

        {mode === "camera" && <CameraScan onCode={handleCode} />}
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleCode(text);
              setText("");
            }
          }}
          placeholder={mode === "type" ? "Type a serial and press Enter" : "Click here, then scan. A scanner presses Enter by itself."}
          autoComplete="off"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <p className="text-xs text-slate-500">
          Each scan fills the next empty serial box, top to bottom.{target ? " The next scan goes into the box you picked." : " Click a box to choose where the next scan goes."}
          {lockedCount > 0 ? ` ${lockedCount} row(s) are locked because an installation was already requested.` : ""}
        </p>

        {log.length > 0 && (
          <div className="space-y-1">
            {log.map((entry, i) => (
              <div key={i} className="text-sm">
                <span className={`mr-2 rounded px-2 py-0.5 text-xs font-medium ${badge[entry.kind]}`}>{badgeText[entry.kind]}</span>
                {entry.message}
              </div>
            ))}
          </div>
        )}

        <div className="max-h-80 space-y-2 overflow-y-auto">
          {editable.map((it, idx) => {
            const count = Number(it.serial_count ?? 1);
            const s = slots[it.id] || { a: "", b: "" };
            const box = (k, orig, label) => {
              const isTarget = target && target.id === it.id && target.slot === k;
              const isNew = norm(s[k]) !== norm(orig);
              return (
                <label className="block text-xs text-slate-500">
                  {label}
                  <input
                    value={s[k]}
                    onChange={(e) => setBox(it.id, k, e.target.value)}
                    onFocus={() => setTarget({ id: it.id, slot: k })}
                    placeholder="-"
                    className={`mt-1 w-full rounded-md border px-2 py-1.5 font-mono text-sm ${isTarget ? "border-brand-500 ring-1 ring-brand-500" : isNew ? "border-emerald-400 bg-emerald-50" : "border-slate-300"}`}
                  />
                </label>
              );
            };
            return (
              <div key={it.id} className="rounded-md border border-slate-200 p-2">
                <div className="mb-1 text-sm text-slate-700">
                  <span className="mr-2 text-slate-400">{idx + 1}</span>
                  {it.item_name || it.item_code}
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {count >= 1 && box("a", it.serial_no, "Serial 1")}
                  {count >= 2 && box("b", it.serial_no_2, "Serial 2")}
                </div>
              </div>
            );
          })}
          {editable.length === 0 && (
            <div className="rounded-md border border-slate-200 px-3 py-4 text-center text-sm text-slate-500">There are no rows here that can take serial numbers.</div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="mr-auto text-sm text-slate-600">{changed.length} row(s) changed. You review them before anything is saved.</span>
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-3 py-2 text-sm">Cancel</button>
          <button
            type="button"
            onClick={review}
            disabled={changed.length === 0}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            Review and save
          </button>
        </div>
      </div>
    </Modal>
  );
}
