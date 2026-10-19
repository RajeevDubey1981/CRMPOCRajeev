import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../auth/AuthContext.jsx";
import Modal from "../../components/Modal.jsx";
import { partsApi } from "../../api/parts.js";
import { itemsApi } from "../../api/items.js";
import { hasPermission } from "../../utils/permissions.js";

const CATEGORIES = [
  "Compressor",
  "PCB / Electronics",
  "Motor",
  "Fan / Blower",
  "Gasket / Seal",
  "Filter",
  "Remote / Accessory",
  "Pipe / Fitting",
  "Miscellaneous",
];

function fmtPrice(v) {
  return v === null || v === undefined ? "—" : `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function emptyForm() {
  return { part_code: "", part_name: "", part_ean: "", category: "", price: "", engineer_visible: true, fits: [] };
}

// Autocomplete for "fits item codes": shows matching item codes while you type, picked from the real Item Master
// list, so the exact code never has to be typed out in full.
function ItemCodeAutocomplete({ fits, onAdd, onRemove }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!query.trim()) { setSuggestions([]); return; }
    timer.current = setTimeout(async () => {
      try {
        const res = await itemsApi.list({ search: query.trim(), per_page: 8 });
        const already = new Set(fits.map((f) => f.item_code));
        setSuggestions((res.items || []).filter((i) => !already.has(i.item_code)));
      } catch {
        setSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  function pick(item) {
    onAdd({ item_code: item.item_code, item_name: item.item_name });
    setQuery("");
    setSuggestions([]);
    setOpen(false);
  }

  return (
    <div className="relative">
      <div className="flex min-h-[42px] flex-wrap items-center gap-1 rounded-md border border-slate-300 px-2 py-1.5">
        {fits.map((f) => (
          <span key={f.item_code} className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-mono text-brand-800">
            {f.item_code}
            <button type="button" onClick={() => onRemove(f.item_code)} className="text-brand-500 hover:text-brand-800">×</button>
          </span>
        ))}
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={fits.length ? "" : "Type an item code or name…"}
          className="min-w-[140px] flex-1 border-0 text-sm outline-none focus:ring-0"
        />
      </div>
      {open && suggestions.length > 0 && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg">
          {suggestions.map((i) => (
            <button
              key={i.item_code}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(i)}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-50"
            >
              <span className="font-mono text-xs text-slate-500">{i.item_code}</span>
              <span className="ml-2 text-slate-800">{i.item_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SparePartsCatalogue() {
  const { user } = useAuth();
  const canEdit = hasPermission(user, "items", "can_edit");
  const canCreate = hasPermission(user, "items", "can_create");
  const [parts, setParts] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // existing part, or null for new
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setParts(await partsApi.catalogue({ search: search || undefined }));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load the catalogue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [search]);

  function openNew() {
    setEditing(null);
    setForm(emptyForm());
    setFormErr("");
    setModalOpen(true);
  }

  function openEdit(part) {
    setEditing(part);
    setForm({
      part_code: part.part_code, part_name: part.part_name, part_ean: part.part_ean || "",
      category: part.category || "", price: part.price ?? "", engineer_visible: part.engineer_visible,
      fits: (part.fits || []).map((code) => ({ item_code: code, item_name: "" })),
    });
    setFormErr("");
    setModalOpen(true);
  }

  async function save() {
    if (!form.part_name.trim() || (!editing && !form.part_code.trim())) {
      setFormErr("Part name is required" + (editing ? "" : ", and part code"));
      return;
    }
    setSaving(true);
    setFormErr("");
    try {
      if (editing) {
        await partsApi.updatePart(editing.id, {
          part_name: form.part_name.trim(), part_ean: form.part_ean.trim() || null, category: form.category.trim() || null,
          price: form.price === "" ? null : Number(form.price), engineer_visible: form.engineer_visible,
        });
        for (const f of form.fits) {
          if (!(editing.fits || []).includes(f.item_code)) await partsApi.addFitment(editing.id, f.item_code, f.item_name).catch(() => {});
        }
      } else {
        await partsApi.createPart({
          part_code: form.part_code.trim(), part_name: form.part_name.trim(), part_ean: form.part_ean.trim() || null,
          category: form.category.trim() || null, price: form.price === "" ? null : Number(form.price),
          engineer_visible: form.engineer_visible, fits: form.fits.map((f) => f.item_code),
        });
      }
      setModalOpen(false);
      load();
    } catch (e) {
      setFormErr(e.response?.data?.detail || "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          type="text"
          placeholder="Search part name, code or EAN"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-72 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        {canCreate && (
          <button
            type="button"
            onClick={openNew}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + Add part
          </button>
        )}
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Part name</th>
              <th className="px-3 py-2">Part code</th>
              <th className="px-3 py-2">EAN</th>
              <th className="px-3 py-2">Fits item codes</th>
              <th className="px-3 py-2">Price</th>
              {canEdit && <th className="px-3 py-2">Engineers see it</th>}
              {canEdit && <th className="px-3 py-2 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>}
            {!loading && parts.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No spare parts yet.</td></tr>}
            {!loading && parts.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-800">{p.part_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{p.part_code}</td>
                <td className="px-3 py-2 font-mono text-xs">{p.part_ean || "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">{(p.fits || []).join(", ") || "—"}</td>
                <td className="px-3 py-2">{fmtPrice(p.price)}</td>
                {canEdit && (
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${p.engineer_visible ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                      {p.engineer_visible ? "Yes" : "Hidden"}
                    </span>
                  </td>
                )}
                {canEdit && (
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => openEdit(p)} className="rounded p-1 text-slate-600 hover:bg-slate-100" title="Edit">✏️</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit spare part" : "Add a spare part"}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Part code{!editing && " *"}</label>
              <input
                value={form.part_code}
                disabled={!!editing}
                onChange={(e) => setForm((f) => ({ ...f, part_code: e.target.value }))}
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Part EAN</label>
              <input value={form.part_ean} onChange={(e) => setForm((f) => ({ ...f, part_ean: e.target.value }))} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Part name *</label>
            <input value={form.part_name} onChange={(e) => setForm((f) => ({ ...f, part_name: e.target.value }))} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Category</label>
              <select value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option value="">Select category</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs uppercase tracking-wide text-slate-500">Price</label>
              <input value={form.price} onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))} placeholder="₹" className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Fits item codes</label>
            <div className="mt-1">
              <ItemCodeAutocomplete
                fits={form.fits}
                onAdd={(f) => setForm((cur) => ({ ...cur, fits: [...cur.fits, f] }))}
                onRemove={(code) => setForm((cur) => ({ ...cur, fits: cur.fits.filter((f) => f.item_code !== code) }))}
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={form.engineer_visible} onChange={(e) => setForm((f) => ({ ...f, engineer_visible: e.target.checked }))} />
            Engineers can see this part when raising a request
          </label>
          {formErr && <p className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-700">{formErr}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setModalOpen(false)} className="rounded-md border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button onClick={save} disabled={saving} className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
