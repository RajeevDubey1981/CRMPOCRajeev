import { useState } from "react";

import { salesApi } from "../../api/sales.js";
import Modal from "../../components/Modal.jsx";
import { Footer } from "./LeadModals.jsx";
import { Field, Notice, btn, errText, fieldClass, useSales } from "./salesUi.jsx";

const LEAD_FIELDS = [["name", "Name"], ["company", "Company"], ["phone", "Phone"], ["email", "Email"], ["item", "Wants"], ["message", "Message"], ["place", "City"], ["state", "State"], ["country", "Country"], ["pincode", "Pin code"], ["value_lakh", "Value (lakh rupees)"]];
const PROSPECT_FIELDS = [["company", "Company"], ["name", "Contact person"], ["phone", "Phone"], ["email", "Email"], ["country", "Country"], ["place", "City"], ["kind", "Kind (importer, distributor ...)"], ["item", "Products"], ["why", "Why it matches (evidence)"]];

// mode "leads": a list of people who asked, or visitors from an expo. mode "prospects": a company list from a directory or import records.
export default function UploadModal({ mode = "leads", onClose, onDone }) {
  const { status } = useSales();
  const [file, setFile] = useState(null);
  const [pre, setPre] = useState(null);
  const [mapping, setMapping] = useState({});
  const [opts, setOpts] = useState({ lead_type: "", source_label: "", country: "", kind: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const fields = mode === "prospects" ? PROSPECT_FIELDS : LEAD_FIELDS;

  async function choose(f) {
    setFile(f); setPre(null); setError(""); setResult(null);
    if (!f) return;
    setBusy(true);
    try { const p = await salesApi.uploadPreview(f); setPre(p); setMapping(p.mapping || {}); } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  }
  async function go() {
    setBusy(true); setError("");
    try {
      setResult(await salesApi.uploadImport(file, { mode, mapping, lead_type: opts.lead_type || null, source_label: opts.source_label, country: opts.country, kind: opts.kind }));
    } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  }
  const needs = mode === "prospects" ? (mapping.company && (mapping.country || opts.country.trim())) : (mapping.phone && (mapping.name || mapping.company));

  return (
    <Modal open onClose={() => (result ? onDone?.(result) : onClose())} title={mode === "prospects" ? "Load a company list (Kompass, import records, a chamber list ...)" : "Upload leads from Excel or CSV"} maxWidth="max-w-3xl">
      {error && <Notice tone="bad">{error}</Notice>}
      {result ? (
        <div>
          <Notice tone="good">
            {mode === "prospects" ? <><b>{result.added}</b> companies added{result.duplicates ? `, ${result.duplicates} were already there` : ""}.</> : <><b>{result.created}</b> leads made{result.again ? `, ${result.again} joined a lead that is already open for the same phone` : ""}{result.skipped ? `, ${result.skipped} rows skipped` : ""}.</>}
          </Notice>
          {result.errors?.length > 0 && <div className="mb-3 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900"><b>Rows not used</b>{result.errors.map((e) => <div key={e}>{e}</div>)}</div>}
          <Footer onClose={() => onDone?.(result)}><button type="button" className={btn.primary} onClick={() => onDone?.(result)}>Done</button></Footer>
        </div>
      ) : (
        <>
          <p className="mb-2 text-sm text-slate-600">{mode === "prospects"
            ? "Export the list from the directory or the import-record service you pay for, then load the file here. The companies can then be searched, and you make a lead of the ones you want to approach. They are not leads until you do."
            : "A file of people and what they want (an expo list, a dealer list). The first row holds the column names. Each row becomes a lead; a person whose phone is already on an open lead joins that lead."}</p>
          <Field label="File (.xlsx or .csv, up to 5 MB and 5000 rows)"><input type="file" accept=".xlsx,.csv,.txt" onChange={(e) => choose(e.target.files?.[0] || null)} /></Field>
          {busy && !pre && <p className="text-sm text-slate-500">Reading the file...</p>}
          {pre && (
            <>
              <p className="mb-2 text-sm text-slate-700"><b>{pre.total}</b> rows found. Say which column is which (we guessed from the names):</p>
              <div className="mb-3 grid gap-x-3 gap-y-1 sm:grid-cols-2">
                {fields.map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 text-sm"><span className="w-44 shrink-0 text-slate-600">{label}</span>
                    <select className={fieldClass} value={mapping[k] || ""} onChange={(e) => setMapping((m) => ({ ...m, [k]: e.target.value }))}><option value="">(not in the file)</option>{pre.columns.map((c) => <option key={c} value={c}>{c}</option>)}</select>
                  </label>
                ))}
              </div>
              <div className="mb-3 overflow-x-auto rounded border border-slate-200"><table className="min-w-full text-xs"><thead className="bg-slate-50 text-left text-slate-500"><tr>{pre.columns.map((c) => <th key={c} className="px-2 py-1">{c}</th>)}</tr></thead><tbody>{pre.sample.map((r, i) => <tr key={i} className="border-t border-slate-100">{pre.columns.map((c) => <td key={c} className="px-2 py-1">{r[c]}</td>)}</tr>)}</tbody></table></div>
              <div className="grid gap-x-3 sm:grid-cols-2">
                <Field label="Source name" hint="Shown on every lead made from this file"><input className={fieldClass} value={opts.source_label} onChange={(e) => setOpts({ ...opts, source_label: e.target.value })} placeholder={mode === "prospects" ? "Kompass export, Oct 2026" : `Excel: ${file?.name || ""}`} /></Field>
                {mode === "prospects"
                  ? <Field label="Country, if the file has no country column"><input className={fieldClass} value={opts.country} onChange={(e) => setOpts({ ...opts, country: e.target.value })} placeholder="Nepal" /></Field>
                  : <Field label="Lead type" hint="Leave empty to let the words decide"><select className={fieldClass} value={opts.lead_type} onChange={(e) => setOpts({ ...opts, lead_type: e.target.value })}><option value="">Decide from the words</option>{(status?.lead_types || []).map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</select></Field>}
              </div>
              {!needs && <Notice tone="warn">{mode === "prospects" ? "Choose the company column, and the country column (or type the country)." : "Choose the phone column and the name (or company) column."}</Notice>}
            </>
          )}
          <Footer onClose={onClose}><button type="button" className={btn.go} disabled={busy || !pre || !needs} onClick={go}>{mode === "prospects" ? "Load the list" : "Make the leads"}</button></Footer>
        </>
      )}
    </Modal>
  );
}
