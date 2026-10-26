import { useMemo } from "react";

import SearchableSelect from "../SearchableSelect.jsx";

const YEAR_OPTIONS = Array.from({ length: 10 }, (_, i) => i + 1);
export const FREE_SERVICE_COUNT_OPTIONS = [0, 1, 2, 3, 4].map((value) => ({ value, label: String(value) }));

export const BLANK_VENDOR_LINE_ITEM = {
  serial_no: "",
  serial_no_2: "",
  item_id: "",
  item_qty: 1,
  pcb_warranty_years: "",
  component_warranty_years: "",
  machine_warranty_years: "",
  free_service_count: 0,
  dry_free_service_count: "",
  wet_free_service_count: "",
};

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function RequiredLabel({ children }) {
  return (
    <label className={labelClass}>
      {children} <span className="text-red-500">*</span>
    </label>
  );
}

export function collapseOrderItemsToLineItems(items) {
  if (!items?.length) return [{ ...BLANK_VENDOR_LINE_ITEM }];
  const groups = [];
  let current = null;
  for (const item of items) {
    const signature = [
      item.item_id,
      item.consignee_address_id,
      item.pcb_warranty_years,
      item.component_warranty_years,
      item.machine_warranty_years,
      item.dry_free_service_count ?? 0,
      item.wet_free_service_count ?? 0,
    ].join("|");
    if (!current || current.signature !== signature) {
      current = {
        signature,
        consignee_address_id: item.consignee_address_id ?? null,
        item_id: String(item.item_id || ""),
        serial_no: item.serial_no || "",
        serial_no_2: item.serial_no_2 || "",
        item_qty: 1,
        pcb_warranty_years: item.pcb_warranty_years ?? "",
        component_warranty_years: item.component_warranty_years ?? "",
        machine_warranty_years: item.machine_warranty_years ?? "",
        dry_free_service_count: item.dry_free_service_count ?? "",
        wet_free_service_count: item.wet_free_service_count ?? "",
        free_service_count: item.free_service_count ?? 0,
      };
      groups.push(current);
    } else {
      current.item_qty += 1;
    }
  }
  return groups;
}

export function validateVendorLineItems(lineItems) {
  if (lineItems.length === 0) return "Add at least one item.";
  for (const [idx, row] of lineItems.entries()) {
    const rowNo = idx + 1;
    if (!row.item_id) return `Item ${rowNo}: Item Name is required.`;
    if (!row.item_qty || Number(row.item_qty) < 1) return `Item ${rowNo}: Item Qty is required.`;
    if (!row.pcb_warranty_years) return `Item ${rowNo}: PCB Warranty is required.`;
    if (!row.component_warranty_years) return `Item ${rowNo}: Component Warranty is required.`;
    if (!row.machine_warranty_years) return `Item ${rowNo}: Machine Warranty is required.`;
    if (row.dry_free_service_count === "" || row.wet_free_service_count === "") {
      return `Item ${rowNo}: Dry and Wet Free Service are required.`;
    }
    if (Number(row.dry_free_service_count) + Number(row.wet_free_service_count) > 4) {
      return `Item ${rowNo}: Dry and wet free services cannot exceed 4 total.`;
    }
  }
  return "";
}

export function serializeVendorLineItems(lineItems) {
  return lineItems.map((row) => ({
    consignee_address_id: row.consignee_address_id ?? null,
    item_id: row.item_id ? Number(row.item_id) : null,
    serial_no: (row.serial_no || "").trim() || null,
    serial_no_2: (row.serial_no_2 || "").trim() || null,
    item_qty: Number(row.item_qty) || 1,
    pcb_warranty_years: row.pcb_warranty_years ? Number(row.pcb_warranty_years) : null,
    component_warranty_years: row.component_warranty_years ? Number(row.component_warranty_years) : null,
    machine_warranty_years: row.machine_warranty_years ? Number(row.machine_warranty_years) : null,
    free_service_count: Number(row.dry_free_service_count) + Number(row.wet_free_service_count),
    dry_free_service_count: Number(row.dry_free_service_count) || 0,
    wet_free_service_count: Number(row.wet_free_service_count) || 0,
  }));
}

export default function VendorOrderLineItemsEditor({ lineItems, setLineItems, itemOptions }) {
  const itemNameOptions = useMemo(
    () => itemOptions.map((item) => ({ value: item.id, label: `${item.item_code} - ${item.item_name}` })),
    [itemOptions]
  );
  const yearOptions = useMemo(
    () => YEAR_OPTIONS.map((year) => ({ value: year, label: `${year} Year${year > 1 ? "s" : ""}` })),
    []
  );

  function addItem() {
    setLineItems((prev) => [...prev, { ...BLANK_VENDOR_LINE_ITEM }]);
  }

  function removeItem(idx) {
    setLineItems((prev) => prev.filter((_, index) => index !== idx));
  }

  function setItem(idx, field, value) {
    setLineItems((prev) =>
      prev.map((row, index) => {
        if (index !== idx) return row;
        const next = { ...row, [field]: value };
        if (field === "dry_free_service_count" || field === "wet_free_service_count") {
          next.free_service_count = Number(next.dry_free_service_count || 0) + Number(next.wet_free_service_count || 0);
        }
        return next;
      })
    );
  }

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Line Items</h3>
        <button
          type="button"
          onClick={addItem}
          className="rounded-md border border-brand-500 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50"
        >
          + New Item
        </button>
      </div>

      {lineItems.length === 0 && (
        <p className="text-sm text-rose-600">Add at least one item.</p>
      )}

      <div className="space-y-4">
        {lineItems.map((row, idx) => (
          <div key={idx} className="relative rounded-md border border-slate-200 bg-white p-4">
            <button
              type="button"
              onClick={() => removeItem(idx)}
              className="absolute right-3 top-3 rounded-md border border-rose-300 px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
            >
              Remove
            </button>
            <div className="grid grid-cols-1 gap-3 pr-20 md:grid-cols-4">
              <div className="md:col-span-2">
                <RequiredLabel>Item Name</RequiredLabel>
                <SearchableSelect
                  options={itemNameOptions}
                  value={row.item_id}
                  onChange={(value) => setItem(idx, "item_id", value)}
                  placeholder="Search item..."
                />
              </div>
              <div>
                <RequiredLabel>Item Qty</RequiredLabel>
                <input
                  type="number"
                  min="1"
                  value={row.item_qty}
                  onChange={(e) => setItem(idx, "item_qty", e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div className="md:col-span-4 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
                Serial numbers are optional for vendors. Admin will add them after the order is processed.
              </div>
              <div>
                <RequiredLabel>PCB Warranty</RequiredLabel>
                <SearchableSelect
                  options={yearOptions}
                  value={row.pcb_warranty_years}
                  onChange={(value) => setItem(idx, "pcb_warranty_years", value)}
                  placeholder="Years..."
                />
              </div>
              <div>
                <RequiredLabel>Component Warranty</RequiredLabel>
                <SearchableSelect
                  options={yearOptions}
                  value={row.component_warranty_years}
                  onChange={(value) => setItem(idx, "component_warranty_years", value)}
                  placeholder="Years..."
                />
              </div>
              <div>
                <RequiredLabel>Machine Warranty</RequiredLabel>
                <SearchableSelect
                  options={yearOptions}
                  value={row.machine_warranty_years}
                  onChange={(value) => setItem(idx, "machine_warranty_years", value)}
                  placeholder="Years..."
                />
              </div>
              <div>
                <RequiredLabel>Dry Free Service</RequiredLabel>
                <SearchableSelect
                  options={FREE_SERVICE_COUNT_OPTIONS}
                  value={row.dry_free_service_count}
                  onChange={(value) => setItem(idx, "dry_free_service_count", value)}
                  placeholder="Dry count..."
                />
              </div>
              <div>
                <RequiredLabel>Wet Free Service</RequiredLabel>
                <SearchableSelect
                  options={FREE_SERVICE_COUNT_OPTIONS}
                  value={row.wet_free_service_count}
                  onChange={(value) => setItem(idx, "wet_free_service_count", value)}
                  placeholder="Wet count..."
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
