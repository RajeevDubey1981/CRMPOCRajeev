const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

export default function ConsigneeAddressesEditor({ rows, onChange, items = [], disabled = false }) {
  function set(index, field, value) {
    onChange(rows.map((row, i) => i === index ? { ...row, [field]: value } : row));
  }

  return (
    <fieldset disabled={disabled} className="space-y-4">
      {rows.map((row, index) => {
        const selected = row.id && items.some((item) => item.consignee_address_id === row.id);
        return (
          <div key={row.id || `new-${index}`} className="space-y-3 rounded-md border border-sky-100 bg-sky-50/30 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold">Consignee {index + 1}</span>
              <button type="button" disabled={selected} title={selected ? "Clear the line item selections before removing this consignee" : "Remove consignee"}
                onClick={() => onChange(rows.filter((_, i) => i !== index))} className="text-sm text-rose-600 disabled:opacity-50">Remove</button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm">Name *
                <input required value={row.consignee_name || ""} onChange={(e) => set(index, "consignee_name", e.target.value)} className={fieldClass} />
              </label>
              <label className="text-sm">Mobile number *
                <input required type="tel" inputMode="numeric" pattern="[0-9]{10}" maxLength={10} value={row.contact || ""}
                  onChange={(e) => set(index, "contact", e.target.value.replace(/[^0-9]/g, ""))} className={fieldClass}
                  aria-describedby={`consignee-mobile-${index}`} />
                <span id={`consignee-mobile-${index}`} className="text-xs text-slate-500">Required: exactly 10 digits (0–9).</span>
              </label>
              <label className="text-sm md:col-span-2">Address *
                <textarea required rows={2} value={row.address || ""} onChange={(e) => set(index, "address", e.target.value)} className={fieldClass} />
              </label>
              {[["email", "Email"], ["city", "City"], ["state", "State"]].map(([field, label]) => (
                <label key={field} className="text-sm">{label}
                  <input type={field === "email" ? "email" : "text"} value={row[field] || ""} onChange={(e) => set(index, field, e.target.value)} className={fieldClass} />
                </label>
              ))}
            </div>
          </div>
        );
      })}
      <button type="button" onClick={() => onChange([...rows, { consignee_name: "", contact: "", address: "" }])}
        className="text-sm font-medium text-brand-700">+ Add consignee</button>
    </fieldset>
  );
}
