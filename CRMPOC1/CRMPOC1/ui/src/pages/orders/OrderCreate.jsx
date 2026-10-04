import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ordersApi } from "../../api/orders.js";
import Modal from "../../components/Modal.jsx";
import SearchableSelect from "../../components/SearchableSelect.jsx";
import { INDIAN_STATES_UTS } from "../../data/indianStates.js";
import { useAuth } from "../../auth/AuthContext.jsx";

const DELIVERY_STATUSES = ["Pending", "Shipped", "In Transit", "Delivered", "Returned", "Cancelled"];
const YEAR_OPTIONS = Array.from({ length: 10 }, (_, i) => i + 1);
const FREE_SERVICE_COUNT_OPTIONS = [0, 1, 2, 3, 4].map((value) => ({ value, label: String(value) }));

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

const BLANK_CONSIGNEE = {
  consignee_name: "",
  contact: "",
  email: "",
  city: "",
  state: "",
  address: "",
};

const BLANK_ITEM = {
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
const disabledFieldClass =
  "w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function RequiredLabel({ children }) {
  return (
    <label className={labelClass}>
      {children} <span className="text-red-500">*</span>
    </label>
  );
}

export default function OrderCreate() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const isVendor = role === "vendor";

  const [vendors, setVendors] = useState([]);
  const [couriers, setCouriers] = useState([]);
  const [itemOptions, setItemOptions] = useState([]);

  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [createdOrder, setCreatedOrder] = useState(null);

  const [file, setFile] = useState(null);

  const initialForm = {
    order_no: "",
    order_date: todayStr(),
    oem_bill_no: "",
    customer_name: "",
    customer_contact: "",
    customer_email: "",
    customer_city: "",
    customer_state: "",
    customer_address: "",
    vendor_id: "",
    fulfilment: "Vendor",
    status: "Pending",
    courier_id: "",
    expected_delivery_date: "",
    lrn_no: "",
    vendor_bill_no: "",
    vendor_bill_date: "",
  };

  const [form, setForm] = useState(initialForm);
  const [consignees, setConsignees] = useState([]);
  const [lineItems, setLineItems] = useState([]);
  const fromStore = !isVendor && form.fulfilment === "Store";

  useEffect(() => {
    ordersApi.vendors().then(setVendors).catch(() => {});
    ordersApi.couriers().then(setCouriers).catch(() => {});
    ordersApi.items().then(setItemOptions).catch(() => {});
  }, []);

  const vendorOptions = useMemo(() => vendors.map((v) => ({
    value: v.id,
    label: `${v.vendor_code ?? ""} - ${v.gst_no ?? ""} - ${v.name_of_firm ?? v.name ?? ""} - ${v.state ?? ""}`,
  })), [vendors]);
  const currentVendor = useMemo(
    () => (isVendor ? vendors.find((vendor) => vendor.email === user?.email || String(vendor.id) === String(form.vendor_id)) : null),
    [form.vendor_id, isVendor, user?.email, vendors]
  );

  useEffect(() => {
    if (!isVendor || vendors.length === 0) return;
    const matchedVendor = vendors.find((vendor) => vendor.email === user?.email);
    if (!matchedVendor) return;
    setForm((prev) => (
      String(prev.vendor_id) === String(matchedVendor.id)
        ? prev
        : { ...prev, vendor_id: String(matchedVendor.id) }
    ));
  }, [isVendor, user?.email, vendors]);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function addConsignee() {
    setConsignees((prev) => [...prev, { ...BLANK_CONSIGNEE }]);
  }

  function removeConsignee(idx) {
    setConsignees((prev) => prev.filter((_, i) => i !== idx));
  }

  function setConsignee(idx, field, value) {
    setConsignees((prev) => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
  }

  function consigneeRowHasContent(row) {
    return Object.values(row).some((value) => (value || "").trim());
  }

  function validateConsignees() {
    for (const [idx, row] of consignees.entries()) {
      if (!consigneeRowHasContent(row)) continue;
      const label = consignees.length > 1 ? `Consignee address ${idx + 1}` : "Consignee address";
      if (!(row.consignee_name || "").trim()) return `${label}: Consignee name is required.`;
      if (!(row.address || "").trim()) return `${label}: Address is required.`;
    }
    return "";
  }

  function addItem() {
    setLineItems((prev) => [...prev, { ...BLANK_ITEM }]);
  }

  function removeItem(idx) {
    setLineItems((prev) => prev.filter((_, i) => i !== idx));
  }

  function itemSerialCount(itemId) {
    const master = itemOptions.find((row) => String(row.id) === String(itemId));
    return master?.serial_count ?? 1;
  }

  function setItem(idx, field, value) {
    setLineItems((prev) =>
      prev.map((row, i) => {
        if (i !== idx) return row;
        const next = { ...row, [field]: value };
        if (field === "item_id") {
          const count = itemSerialCount(value);
          if (count < 2) next.serial_no_2 = "";
        }
        if (field === "dry_free_service_count" || field === "wet_free_service_count") {
          next.free_service_count = Number(next.dry_free_service_count || 0) + Number(next.wet_free_service_count || 0);
        }
        return next;
      })
    );
  }

  function resetForm() {
    setForm(isVendor && currentVendor ? { ...initialForm, vendor_id: String(currentVendor.id) } : initialForm);
    setConsignees([]);
    setLineItems([]);
    setFile(null);
    setErr("");
    setSuccessMsg("");
  }

  function validateLineItems() {
    if (lineItems.length === 0) {
      return "Add at least one item before submitting the order.";
    }
    for (const [idx, row] of lineItems.entries()) {
      const rowNo = idx + 1;
      if (!row.item_id) return `Item ${rowNo}: Item Name is required.`;
      if (!row.item_qty || Number(row.item_qty) < 1) return `Item ${rowNo}: Item Qty is required.`;
      if (!row.pcb_warranty_years) return `Item ${rowNo}: PCB Warranty is required.`;
      if (!row.component_warranty_years) return `Item ${rowNo}: Component Warranty is required.`;
      if (!row.machine_warranty_years) return `Item ${rowNo}: Machine Warranty is required.`;
      if (row.free_service_count === "" || row.free_service_count === null || row.free_service_count === undefined) {
        return `Item ${rowNo}: Free Service is required.`;
      }
      if (row.dry_free_service_count === "" || row.dry_free_service_count === null || row.dry_free_service_count === undefined) {
        return `Item ${rowNo}: Dry Free Service is required.`;
      }
      if (row.wet_free_service_count === "" || row.wet_free_service_count === null || row.wet_free_service_count === undefined) {
        return `Item ${rowNo}: Wet Free Service is required.`;
      }
      if (Number(row.dry_free_service_count) + Number(row.wet_free_service_count) > 4) {
        return `Item ${rowNo}: Dry and wet free services cannot exceed 4 total.`;
      }
      const serialCount = itemSerialCount(row.item_id);
      if (!isVendor && !fromStore) {
        if (serialCount >= 1 && !(row.serial_no || "").trim()) {
          return `Item ${rowNo}: Serial Number 1 is required for this item code.`;
        }
        if (serialCount >= 2 && !(row.serial_no_2 || "").trim()) {
          return `Item ${rowNo}: Serial Number 2 is required for this item code (2 serials per unit).`;
        }
      }
    }
    return "";
  }

  const courierOptions = couriers.map((c) => ({ value: c.id, label: c.name }));
  const statusOptions = DELIVERY_STATUSES.map((s) => ({ value: s, label: s }));
  const stateOptions = INDIAN_STATES_UTS.map((s) => ({ value: s, label: s }));
  const itemNameOptions = itemOptions.map((i) => ({ value: i.id, label: `${i.item_code} - ${i.item_name}` }));
  const yearOptions = YEAR_OPTIONS.map((y) => ({ value: y, label: `${y} Year${y > 1 ? "s" : ""}` }));
  const freeServiceCountOptions = FREE_SERVICE_COUNT_OPTIONS;
  const vendorDisplayValue = currentVendor
    ? vendorOptions.find((option) => String(option.value) === String(currentVendor.id))?.label || currentVendor.name_of_firm || ""
    : "";

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSuccessMsg("");

    if (!form.vendor_id && !isVendor && !fromStore) {
      setErr("Vendor Name is required");
      return;
    }
    if (isVendor && !currentVendor) {
      setErr("Your vendor login is not linked to an active vendor record");
      return;
    }
    const lineItemError = validateLineItems();
    if (lineItemError) {
      setErr(lineItemError);
      return;
    }
    const consigneeError = validateConsignees();
    if (consigneeError) {
      setErr(consigneeError);
      return;
    }
    if (!file) {
      setErr("Order Document is required");
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        order_no: form.order_no.trim() || null,
        order_date: form.order_date || null,
        oem_bill_no: isVendor ? null : form.oem_bill_no || null,
        vendor_id: isVendor || fromStore ? null : (form.vendor_id ? Number(form.vendor_id) : null),
        fulfilment: fromStore ? "Store" : "Vendor",
        status: isVendor || fromStore ? "Pending" : form.status,
        courier_id: isVendor || fromStore ? null : (form.courier_id ? Number(form.courier_id) : null),
        customer_name: form.customer_name || null,
        customer_contact: form.customer_contact || null,
        customer_email: form.customer_email || null,
        customer_city: form.customer_city || null,
        customer_state: form.customer_state || null,
        customer_address: form.customer_address || null,
        consignee_addresses: consignees
          .filter(consigneeRowHasContent)
          .map((row) => ({
            consignee_name: (row.consignee_name || "").trim() || null,
            contact: (row.contact || "").trim() || null,
            email: (row.email || "").trim() || null,
            city: (row.city || "").trim() || null,
            state: (row.state || "").trim() || null,
            address: (row.address || "").trim() || null,
          })),
        expected_delivery_date: form.expected_delivery_date || null,
        lrn_no: isVendor || fromStore ? null : (form.lrn_no || null),
        items: lineItems
          .map((row) => ({
            item_id: row.item_id ? Number(row.item_id) : null,
            serial_no: fromStore ? null : (row.serial_no || "").trim() || null,
            serial_no_2: fromStore ? null : (row.serial_no_2 || "").trim() || null,
            item_qty: Number(row.item_qty) || 1,
            pcb_warranty_years: row.pcb_warranty_years ? Number(row.pcb_warranty_years) : null,
            component_warranty_years: row.component_warranty_years ? Number(row.component_warranty_years) : null,
            machine_warranty_years: row.machine_warranty_years ? Number(row.machine_warranty_years) : null,
            free_service_count: Number(row.dry_free_service_count) + Number(row.wet_free_service_count),
            dry_free_service_count: Number(row.dry_free_service_count) || 0,
            wet_free_service_count: Number(row.wet_free_service_count) || 0,
          })),
      };

      const created = await ordersApi.create(body, file);
      setSuccessMsg("Order created successfully");
      setCreatedOrder(created);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || "Failed to create order"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800">Create Order</h1>

      {err && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}
      {successMsg && (
        <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">OK {successMsg}</div>
      )}

      <form onSubmit={submit} className="space-y-6">
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Order Details
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className={labelClass}>Order No / GEM No</label>
              <input
                value={form.order_no}
                onChange={(e) => set("order_no", e.target.value)}
                placeholder="e.g. GEMC-511687730897838"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Order Date</label>
              <input
                type="date"
                value={form.order_date}
                onChange={(e) => set("order_date", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Oem Bill No</label>
              <input
                value={form.oem_bill_no}
                onChange={(e) => set("oem_bill_no", e.target.value)}
                disabled={isVendor}
                className={fieldClass}
              />
            </div>
          </div>
        </section>

        <section className="rounded-lg bg-white p-6 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Customer Information
            </h2>
            <button
              type="button"
              onClick={addConsignee}
              className="inline-flex items-center gap-1 rounded-md border border-brand-300 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-800 hover:bg-brand-100"
              title="Add another delivery location (consignee)"
            >
              <span className="text-lg leading-none">+</span>
              Consignee address
            </button>
          </div>
          <p className="mb-4 text-xs text-slate-500">
            Primary customer / billing details below. Use <strong>+ Consignee address</strong> when the order ships to additional locations.
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Customer Name</label>
              <input
                value={form.customer_name}
                onChange={(e) => set("customer_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Contact</label>
              <input
                value={form.customer_contact}
                onChange={(e) => set("customer_contact", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Email</label>
              <input
                type="email"
                value={form.customer_email}
                onChange={(e) => set("customer_email", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer City</label>
              <input
                value={form.customer_city}
                onChange={(e) => set("customer_city", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer State</label>
              <SearchableSelect
                options={stateOptions}
                value={form.customer_state}
                onChange={(v) => set("customer_state", v)}
                placeholder="Search state..."
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass}>Customer Address</label>
              <textarea
                rows={3}
                value={form.customer_address}
                onChange={(e) => set("customer_address", e.target.value)}
                className={fieldClass}
              />
            </div>
          </div>
        </section>

        {consignees.map((row, idx) => (
          <section key={`consignee-${idx}`} className="rounded-lg border border-sky-100 bg-white p-6 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-sky-900">
                Consignee address{consignees.length > 1 ? ` ${idx + 1}` : ""}
              </h2>
              <button
                type="button"
                onClick={() => removeConsignee(idx)}
                className="text-sm text-rose-600 hover:text-rose-800"
              >
                Remove
              </button>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className={labelClass}>Consignee name</label>
                <input
                  value={row.consignee_name}
                  onChange={(e) => setConsignee(idx, "consignee_name", e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>Contact</label>
                <input
                  value={row.contact}
                  onChange={(e) => setConsignee(idx, "contact", e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>Email</label>
                <input
                  type="email"
                  value={row.email}
                  onChange={(e) => setConsignee(idx, "email", e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>City</label>
                <input
                  value={row.city}
                  onChange={(e) => setConsignee(idx, "city", e.target.value)}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass}>State</label>
                <SearchableSelect
                  options={stateOptions}
                  value={row.state}
                  onChange={(v) => setConsignee(idx, "state", v)}
                  placeholder="Search state..."
                />
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>Consignee address</label>
                <textarea
                  rows={3}
                  value={row.address}
                  onChange={(e) => setConsignee(idx, "address", e.target.value)}
                  className={fieldClass}
                />
              </div>
            </div>
          </section>
        ))}

        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Vendor &amp; Delivery
          </h2>
          {!isVendor && (
            <div className="mb-4 flex flex-wrap items-center gap-4 rounded-md bg-slate-50 px-3 py-2 text-sm">
              <span className="font-medium text-slate-700">Ships from</span>
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="fulfilment" checked={form.fulfilment === "Vendor"} onChange={() => set("fulfilment", "Vendor")} />
                Vendor
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="fulfilment" checked={form.fulfilment === "Store"} onChange={() => set("fulfilment", "Store")} />
                Our store
              </label>
              {fromStore && <span className="text-xs text-slate-500">The store reserves stock, waits for the bill number and dispatches. Serial numbers come from the store.</span>}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              {fromStore ? <label className={labelClass}>Vendor Name</label> : <RequiredLabel>Vendor Name</RequiredLabel>}
              {isVendor ? (
                <>
                  <input
                    value={vendorDisplayValue}
                    readOnly
                    className={disabledFieldClass}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Vendor information is auto-filled from your logged-in account.
                  </p>
                </>
              ) : (
                <SearchableSelect
                  options={vendorOptions}
                  value={form.vendor_id}
                  onChange={(v) => set("vendor_id", v)}
                  placeholder="Search vendor..."
                />
              )}
            </div>
            <div>
              <label className={labelClass}>Delivery Status</label>
              <SearchableSelect
                options={statusOptions}
                value={form.status}
                onChange={(v) => set("status", v)}
                placeholder="Search status..."
                disabled={isVendor || fromStore}
              />
              {isVendor && (
                <p className="mt-1 text-xs text-slate-400">
                  Can be updated after the OEM Bill is available.
                </p>
              )}
            </div>
            <div>
              <label className={labelClass}>Courier</label>
              <SearchableSelect
                options={courierOptions}
                value={form.courier_id}
                onChange={(v) => set("courier_id", v)}
                placeholder="Search courier..."
                disabled={isVendor || fromStore}
              />
            </div>
            <div>
              <label className={labelClass}>Expected Date of Delivery</label>
              <input
                type="date"
                value={form.expected_delivery_date}
                onChange={(e) => set("expected_delivery_date", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>LRN No</label>
              <input
                value={form.lrn_no}
                onChange={(e) => set("lrn_no", e.target.value)}
                readOnly={isVendor}
                className={isVendor ? disabledFieldClass : fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Vendor Bill No</label>
              <input value="" disabled className={disabledFieldClass} />
              <p className="mt-1 text-xs text-slate-400">
                Auto-populated after OEM Bill is updated
              </p>
            </div>
            <div>
              <label className={labelClass}>Vendor Bill Date</label>
              <input type="date" value="" disabled className={disabledFieldClass} />
              <p className="mt-1 text-xs text-slate-400">
                Auto-populated after OEM Bill is updated
              </p>
            </div>
            <div>
              <RequiredLabel>Order Document</RequiredLabel>
              <input
                type="file"
                required
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className={fieldClass}
              />
              <p className="mt-1 text-xs text-slate-500">Admin can view and download this document from the order detail page.</p>
            </div>
          </div>
        </section>

        <section className="rounded-lg bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Add Items
            </h2>
            <button
              type="button"
              onClick={addItem}
              className="rounded-md border border-brand-500 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50"
            >
              + New
            </button>
          </div>

          {lineItems.length === 0 && (
            <p className="text-sm text-rose-500">At least one item is required. Click "+ New" to begin.</p>
          )}

          <div className="space-y-4">
            {lineItems.map((row, idx) => (
              <div key={idx} className="relative rounded-md border border-slate-200 p-4">
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
                      onChange={(v) => setItem(idx, "item_id", v)}
                      placeholder="Search item..."
                    />
                  </div>
                  <div>
                    <RequiredLabel>Item Qty</RequiredLabel>
                    <input
                      type="number"
                      min="1"
                      required
                      value={row.item_qty}
                      onChange={(e) => setItem(idx, "item_qty", e.target.value)}
                      className={fieldClass}
                    />
                  </div>
                  {(isVendor || fromStore) && (
                    <div className="md:col-span-4 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
                      {fromStore
                        ? "Serial numbers are filled in by the store when it dispatches this order."
                        : "Serial numbers are not required from vendors. Admin will add them after the order is submitted."}
                    </div>
                  )}
                  {!isVendor && !fromStore && itemSerialCount(row.item_id) >= 1 && (
                    <div>
                      <RequiredLabel>Serial Number 1</RequiredLabel>
                      <input
                        value={row.serial_no}
                        onChange={(e) => setItem(idx, "serial_no", e.target.value)}
                        placeholder="Serial Number 1"
                        className={fieldClass}
                      />
                    </div>
                  )}
                  {!isVendor && !fromStore && itemSerialCount(row.item_id) >= 2 && (
                    <div>
                      <RequiredLabel>Serial Number 2</RequiredLabel>
                      <input
                        value={row.serial_no_2}
                        onChange={(e) => setItem(idx, "serial_no_2", e.target.value)}
                        placeholder="Serial Number 2"
                        className={fieldClass}
                      />
                    </div>
                  )}
                  <div>
                    <RequiredLabel>PCB Warranty</RequiredLabel>
                    <SearchableSelect
                      options={yearOptions}
                      value={row.pcb_warranty_years}
                      onChange={(v) => setItem(idx, "pcb_warranty_years", v)}
                      placeholder="Years..."
                    />
                  </div>
                  <div>
                    <RequiredLabel>Component Warranty</RequiredLabel>
                    <SearchableSelect
                      options={yearOptions}
                      value={row.component_warranty_years}
                      onChange={(v) => setItem(idx, "component_warranty_years", v)}
                      placeholder="Years..."
                    />
                  </div>
                  <div>
                    <RequiredLabel>Machine Warranty</RequiredLabel>
                    <SearchableSelect
                      options={yearOptions}
                      value={row.machine_warranty_years}
                      onChange={(v) => setItem(idx, "machine_warranty_years", v)}
                      placeholder="Years..."
                    />
                  </div>
                  <div>
                    <RequiredLabel>Free Service</RequiredLabel>
                    <input
                      type="number"
                      value={row.free_service_count}
                      readOnly
                      className={disabledFieldClass}
                    />
                  </div>
                  <div>
                    <RequiredLabel>Dry Free Service</RequiredLabel>
                    <SearchableSelect
                      options={freeServiceCountOptions}
                      value={row.dry_free_service_count}
                      onChange={(v) => setItem(idx, "dry_free_service_count", v)}
                      placeholder="Dry count..."
                    />
                  </div>
                  <div>
                    <RequiredLabel>Wet Free Service</RequiredLabel>
                    <SearchableSelect
                      options={freeServiceCountOptions}
                      value={row.wet_free_service_count}
                      onChange={(v) => setItem(idx, "wet_free_service_count", v)}
                      placeholder="Wet count..."
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={resetForm}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm"
            >
              Reset
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting ? "Saving..." : "Submit"}
            </button>
          </div>
        </section>
      </form>

      <Modal
        open={!!createdOrder}
        onClose={() => setCreatedOrder(null)}
        title="Order Created"
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <div className="rounded-md bg-green-50 px-3 py-3 text-sm text-green-700">
            Order created successfully.
          </div>
          <div className="text-sm text-slate-700">
            Order ID: <span className="font-semibold text-slate-900">{createdOrder?.id}</span>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setCreatedOrder(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => navigate(`/orders/${createdOrder.id}`)}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              View Order
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
