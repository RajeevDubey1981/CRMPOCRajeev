import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { couriersApi } from "../../api/couriers.js";

function inputClass() {
  return "w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm";
}

/** The whole rate card is edited as one object and saved in one PUT -- matches how a courier's
 * own rate-card document works (one sheet, a handful of numbers change when they revise rates). */
export default function CourierRateCard() {
  const { id } = useParams();
  const courierId = Number(id);
  const [courier, setCourier] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [savedMsg, setSavedMsg] = useState("");

  const [calcForm, setCalcForm] = useState({
    destination_state: "", destination_pincode: "",
    weight_only: false, two_box: false,
    weight_kg: "", length_cm: "", width_cm: "", height_cm: "",
    box2_weight_kg: "", box2_length_cm: "", box2_width_cm: "", box2_height_cm: "",
    single_length_cm: "", single_width_cm: "", single_height_cm: "",
    is_oda: false,
  });
  const [calcResult, setCalcResult] = useState(null);
  const [calcErr, setCalcErr] = useState("");
  const [calcBusy, setCalcBusy] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([couriersApi.get(courierId), couriersApi.getRateProfile(courierId)])
      .then(([c, p]) => {
        setCourier(c);
        setProfile(p.profile);
      })
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load rate card"))
      .finally(() => setLoading(false));
  }, [courierId]);

  function update(field, value) {
    setProfile((p) => ({ ...p, [field]: value }));
  }

  function updateZoneRate(fromZone, toZone, value) {
    setProfile((p) => {
      const rates = p.zone_rates.filter((r) => !(r.from_zone === fromZone && r.to_zone === toZone));
      rates.push({ from_zone: fromZone, to_zone: toZone, rate_per_kg: Number(value) || 0 });
      return { ...p, zone_rates: rates };
    });
  }

  function rateFor(fromZone, toZone) {
    const row = profile.zone_rates.find((r) => r.from_zone === fromZone && r.to_zone === toZone);
    return row ? row.rate_per_kg : "";
  }

  function updateZoneStates(zone, value) {
    setProfile((p) => ({
      ...p,
      zone_states: { ...p.zone_states, [zone]: value.split(",").map((s) => s.trim()).filter(Boolean) },
    }));
  }

  function addZone() {
    const zone = window.prompt("New zone code (e.g. NW):");
    if (!zone || profile.zones.includes(zone)) return;
    setProfile((p) => ({ ...p, zones: [...p.zones, zone], zone_states: { ...p.zone_states, [zone]: [] } }));
  }

  function addOdaSlab() {
    setProfile((p) => ({
      ...p,
      oda_slabs: [...p.oda_slabs, { weight_from: 0, weight_to: 0, rate_per_kg: 0, min_amount: 0 }],
    }));
  }

  function updateOdaSlab(idx, field, value) {
    setProfile((p) => {
      const slabs = [...p.oda_slabs];
      slabs[idx] = { ...slabs[idx], [field]: Number(value) || 0 };
      return { ...p, oda_slabs: slabs };
    });
  }

  function removeOdaSlab(idx) {
    setProfile((p) => ({ ...p, oda_slabs: p.oda_slabs.filter((_, i) => i !== idx) }));
  }

  async function save() {
    setSaving(true);
    setErr("");
    setSavedMsg("");
    try {
      const saved = await couriersApi.saveRateProfile(courierId, profile);
      setProfile(saved.profile);
      setSavedMsg("Rate card saved.");
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to save rate card");
    } finally {
      setSaving(false);
    }
  }

  async function runCalc() {
    setCalcErr("");
    setCalcResult(null);
    if (!calcForm.destination_state.trim() || !calcForm.weight_kg) {
      setCalcErr("Destination state and weight are required");
      return;
    }
    setCalcBusy(true);
    try {
      const result = await couriersApi.calculateFreight(courierId, {
        destination_state: calcForm.destination_state.trim(),
        destination_pincode: calcForm.destination_pincode.trim() || null,
        weight_kg: Number(calcForm.weight_kg),
        weight_only: calcForm.weight_only,
        length_cm: calcForm.weight_only || !calcForm.length_cm ? null : Number(calcForm.length_cm),
        width_cm: calcForm.weight_only || !calcForm.width_cm ? null : Number(calcForm.width_cm),
        height_cm: calcForm.weight_only || !calcForm.height_cm ? null : Number(calcForm.height_cm),
        box2_weight_kg: calcForm.two_box && calcForm.box2_weight_kg ? Number(calcForm.box2_weight_kg) : null,
        box2_length_cm: calcForm.two_box && calcForm.box2_length_cm ? Number(calcForm.box2_length_cm) : null,
        box2_width_cm: calcForm.two_box && calcForm.box2_width_cm ? Number(calcForm.box2_width_cm) : null,
        box2_height_cm: calcForm.two_box && calcForm.box2_height_cm ? Number(calcForm.box2_height_cm) : null,
        single_length_cm: calcForm.two_box && calcForm.single_length_cm ? Number(calcForm.single_length_cm) : null,
        single_width_cm: calcForm.two_box && calcForm.single_width_cm ? Number(calcForm.single_width_cm) : null,
        single_height_cm: calcForm.two_box && calcForm.single_height_cm ? Number(calcForm.single_height_cm) : null,
        is_oda: calcForm.is_oda,
      });
      setCalcResult(result);
    } catch (e) {
      setCalcErr(e.response?.data?.detail || "Calculation failed");
    } finally {
      setCalcBusy(false);
    }
  }

  if (loading) return <div className="text-sm text-slate-500">Loading…</div>;
  if (err && !profile) return <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>;
  if (!profile) return null;

  return (
    <div className="space-y-5">
      <div>
        <Link to={`/couriers/${courierId}`} className="text-sm text-brand-600 hover:underline">← Back to {courier?.courier_name}</Link>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{courier?.courier_name} — Rate Card</h1>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      {savedMsg && <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{savedMsg}</div>}

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Our warehouse zone</h2>
        <div className="max-w-xs">
          <label className="mb-1 block text-xs font-medium text-slate-700">Source zone (where shipments originate)</label>
          <select value={profile.source_zone || ""} onChange={(e) => update("source_zone", e.target.value)} className={inputClass()}>
            <option value="">— Select —</option>
            {profile.zones.map((z) => <option key={z} value={z}>{z}</option>)}
          </select>
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Zone definition</h2>
          <button type="button" onClick={addZone} className="text-xs text-brand-600 hover:underline">+ Add zone</button>
        </div>
        <div className="space-y-2">
          {profile.zones.map((zone) => (
            <div key={zone} className="flex items-center gap-2">
              <span className="w-16 shrink-0 font-mono text-xs font-semibold text-slate-700">{zone}</span>
              <input
                value={(profile.zone_states[zone] || []).join(", ")}
                onChange={(e) => updateZoneStates(zone, e.target.value)}
                placeholder="States, comma-separated"
                className={inputClass()}
              />
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Zone-to-zone rate matrix (₹/kg)</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-slate-200 bg-slate-50 px-2 py-1.5 text-left">From \ To</th>
                {profile.zones.map((z) => (
                  <th key={z} className="border border-slate-200 bg-slate-50 px-2 py-1.5">{z}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {profile.zones.map((fromZone) => (
                <tr key={fromZone}>
                  <td className="border border-slate-200 bg-slate-50 px-2 py-1.5 font-semibold">{fromZone}</td>
                  {profile.zones.map((toZone) => (
                    <td key={toZone} className="border border-slate-200 p-0.5">
                      <input
                        type="number" step="0.01"
                        value={rateFor(fromZone, toZone)}
                        onChange={(e) => updateZoneRate(fromZone, toZone, e.target.value)}
                        className="w-16 rounded border-0 px-1.5 py-1 text-center text-xs focus:bg-brand-50 focus:outline-none"
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Overhead charges</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            ["docket_charge", "Docket charge (₹ per LR)"],
            ["fsc_percent", "Fuel surcharge (%)"],
            ["volumetric_divisor", "Volumetric divisor (per cu.ft)"],
            ["handling_rate_per_kg", "Handling rate (₹/kg)"],
            ["handling_min_weight_kg", "Handling applies above (kg)"],
            ["demurrage_rate_per_kg", "Demurrage rate (₹/kg)"],
            ["demurrage_min_amount", "Demurrage minimum (₹)"],
            ["free_storage_days", "Free storage (days)"],
            ["min_chargeable_weight_kg", "Minimum chargeable weight (kg)"],
            ["min_chargeable_amount", "Minimum chargeable amount (₹)"],
            ["base_diesel_rate", "Base diesel rate (₹/litre)"],
            ["fuel_hike_percent_per_rupee", "Fuel-hike % per ₹1/L change"],
          ].map(([field, label]) => (
            <div key={field}>
              <label className="mb-1 block text-xs font-medium text-slate-700">{label}</label>
              <input
                type="number" step="0.01"
                value={profile[field] ?? ""}
                onChange={(e) => update(field, Number(e.target.value))}
                className={inputClass()}
              />
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">ODA charges (by weight slab)</h2>
          <button type="button" onClick={addOdaSlab} className="text-xs text-brand-600 hover:underline">+ Add slab</button>
        </div>
        <div className="space-y-2">
          {profile.oda_slabs.map((slab, idx) => (
            <div key={idx} className="flex flex-wrap items-center gap-2">
              <input type="number" value={slab.weight_from} onChange={(e) => updateOdaSlab(idx, "weight_from", e.target.value)} placeholder="From kg" className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm" />
              <span className="text-xs text-slate-400">to</span>
              <input type="number" value={slab.weight_to} onChange={(e) => updateOdaSlab(idx, "weight_to", e.target.value)} placeholder="To kg" className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm" />
              <input type="number" step="0.01" value={slab.rate_per_kg} onChange={(e) => updateOdaSlab(idx, "rate_per_kg", e.target.value)} placeholder="₹/kg" className="w-20 rounded-md border border-slate-300 px-2 py-1 text-sm" />
              <input type="number" value={slab.min_amount} onChange={(e) => updateOdaSlab(idx, "min_amount", e.target.value)} placeholder="Min ₹" className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm" />
              <button type="button" onClick={() => removeOdaSlab(idx)} className="text-xs text-rose-600 hover:underline">Remove</button>
            </div>
          ))}
          {profile.oda_slabs.length === 0 && <p className="text-xs text-slate-400">No ODA slabs yet.</p>}
        </div>
      </section>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="rounded-md bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save rate card"}
        </button>
      </div>

      <section className="rounded-lg border-2 border-dashed border-brand-300 bg-brand-50/30 p-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Try a freight calculation</h2>

        <div className="mb-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setCalcForm((f) => ({ ...f, weight_only: false }))}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${!calcForm.weight_only ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600"}`}
          >
            I know L × W × H
          </button>
          <button
            type="button"
            onClick={() => setCalcForm((f) => ({ ...f, weight_only: true }))}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${calcForm.weight_only ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600"}`}
          >
            I only know the weight
          </button>
          <button
            type="button"
            onClick={() => setCalcForm((f) => ({ ...f, two_box: !f.two_box }))}
            disabled={calcForm.weight_only}
            className={`rounded-full px-3 py-1 text-xs font-semibold disabled:opacity-40 ${calcForm.two_box ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600"}`}
          >
            Packed as 2 boxes (e.g. Split AC indoor + outdoor)
          </button>
        </div>
        {calcForm.weight_only && (
          <p className="mb-3 text-xs text-slate-500">
            No measuring tape needed — charges on actual weight only, no volumetric check. Flag this entry for an office review once the real box size is known.
          </p>
        )}

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Destination state</label>
            <input
              value={calcForm.destination_state}
              onChange={(e) => setCalcForm((f) => ({ ...f, destination_state: e.target.value }))}
              placeholder="e.g. Maharashtra"
              className="w-48 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Pincode (optional, for ODA)</label>
            <input
              value={calcForm.destination_pincode}
              onChange={(e) => setCalcForm((f) => ({ ...f, destination_pincode: e.target.value }))}
              placeholder="e.g. 800001"
              className="w-32 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>
          <label className="flex items-center gap-1.5 pb-2 text-sm text-slate-700">
            <input type="checkbox" checked={calcForm.is_oda} onChange={(e) => setCalcForm((f) => ({ ...f, is_oda: e.target.checked }))} />
            This pincode is ODA
          </label>
        </div>

        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">{calcForm.two_box ? "Box 1 weight (kg)" : "Actual weight (kg)"}</label>
            <input
              type="number"
              value={calcForm.weight_kg}
              onChange={(e) => setCalcForm((f) => ({ ...f, weight_kg: e.target.value }))}
              className="w-28 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>
          {!calcForm.weight_only && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">{calcForm.two_box ? "Box 1 L × W × H (cm)" : "Box L × W × H (cm, optional)"}</label>
              <div className="flex gap-1">
                <input type="number" value={calcForm.length_cm} onChange={(e) => setCalcForm((f) => ({ ...f, length_cm: e.target.value }))} placeholder="L" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                <input type="number" value={calcForm.width_cm} onChange={(e) => setCalcForm((f) => ({ ...f, width_cm: e.target.value }))} placeholder="W" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                <input type="number" value={calcForm.height_cm} onChange={(e) => setCalcForm((f) => ({ ...f, height_cm: e.target.value }))} placeholder="H" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
            </div>
          )}
        </div>

        {calcForm.two_box && !calcForm.weight_only && (
          <>
            <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md bg-white/60 p-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">Box 2 weight (kg)</label>
                <input type="number" value={calcForm.box2_weight_kg} onChange={(e) => setCalcForm((f) => ({ ...f, box2_weight_kg: e.target.value }))} className="w-28 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">Box 2 L × W × H (cm)</label>
                <div className="flex gap-1">
                  <input type="number" value={calcForm.box2_length_cm} onChange={(e) => setCalcForm((f) => ({ ...f, box2_length_cm: e.target.value }))} placeholder="L" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                  <input type="number" value={calcForm.box2_width_cm} onChange={(e) => setCalcForm((f) => ({ ...f, box2_width_cm: e.target.value }))} placeholder="W" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                  <input type="number" value={calcForm.box2_height_cm} onChange={(e) => setCalcForm((f) => ({ ...f, box2_height_cm: e.target.value }))} placeholder="H" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                </div>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-end gap-3 rounded-md bg-white/60 p-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">If packed as 1 combined box instead — L × W × H (cm)</label>
                <div className="flex gap-1">
                  <input type="number" value={calcForm.single_length_cm} onChange={(e) => setCalcForm((f) => ({ ...f, single_length_cm: e.target.value }))} placeholder="L" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                  <input type="number" value={calcForm.single_width_cm} onChange={(e) => setCalcForm((f) => ({ ...f, single_width_cm: e.target.value }))} placeholder="W" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                  <input type="number" value={calcForm.single_height_cm} onChange={(e) => setCalcForm((f) => ({ ...f, single_height_cm: e.target.value }))} placeholder="H" className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
                </div>
              </div>
              <p className="pb-2 text-xs text-slate-500">Fill this in to compare — the calculator will say which packing is cheaper.</p>
            </div>
          </>
        )}

        <div className="mt-3">
          <button type="button" onClick={runCalc} disabled={calcBusy} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50">
            {calcBusy ? "Calculating…" : "Calculate freight"}
          </button>
        </div>

        {calcErr && <p className="mt-2 text-sm text-rose-700">{calcErr}</p>}
        {calcResult && (
          <div className="mt-4 rounded-md border border-slate-200 bg-white p-4">
            <p className="mb-2 text-xs text-slate-500">
              {calcResult.source_zone || "?"} → {calcResult.destination_zone || "?"} · chargeable weight {calcResult.chargeable_weight_kg}kg
            </p>
            {calcResult.lines.map((l, i) => (
              <div key={i} className="flex justify-between border-b border-slate-100 py-1 text-sm">
                <span className="text-slate-600">{l.label}</span>
                {l.amount !== 0 && <span className="font-mono">₹{l.amount.toLocaleString("en-IN")}</span>}
              </div>
            ))}
            <div className="mt-2 flex justify-between text-sm font-bold">
              <span>Total freight {calcResult.single_box_total != null ? "— 2 boxes" : ""}</span>
              <span>₹{calcResult.total.toLocaleString("en-IN")}</span>
            </div>
            {calcResult.single_box_total != null && (
              <>
                <div className="mt-1 flex justify-between text-sm">
                  <span className="text-slate-600">Total freight — 1 combined box</span>
                  <span className="font-mono">₹{calcResult.single_box_total.toLocaleString("en-IN")}</span>
                </div>
                <p className="mt-2 rounded-md bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700">
                  Recommended: {calcResult.recommended === "one_box" ? "pack as 1 combined box" : "pack as 2 boxes"}
                  {calcResult.recommended !== "one_box" && calcResult.total === calcResult.single_box_total ? " (same freight, safer handling)" : ""}
                </p>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
