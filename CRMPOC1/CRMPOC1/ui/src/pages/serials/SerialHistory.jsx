import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { serialApi } from "../../api/serials.js";

function EventBadge({ type }) {
  const styles = {
    ORDER: "bg-sky-100 text-sky-700",
    INSTALLATION: "bg-emerald-100 text-emerald-700",
    COMPLAINT: "bg-amber-100 text-amber-700",
    SERVICE: "bg-orange-100 text-orange-700",
    CLAIM: "bg-rose-100 text-rose-700",
    PART_REPLACEMENT: "bg-violet-100 text-violet-700",
    SYSTEM: "bg-slate-100 text-slate-700",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles[type] || styles.SYSTEM}`}>{type}</span>;
}

function fmt(value) {
  if (!value) return "-";
  try { return new Date(value).toLocaleString(); } catch { return value; }
}

function fmtDate(value) {
  if (!value) return "-";
  try { return new Date(value).toLocaleDateString(); } catch { return value; }
}

function fmtWarranty(years, endDate) {
  if (!years && !endDate) return "-";
  if (years && endDate) return `${years} Year${years === 1 ? "" : "s"} (${fmtDate(endDate)})`;
  if (years) return `${years} Year${years === 1 ? "" : "s"}`;
  return fmtDate(endDate);
}

function sortEventsDesc(items) {
  return [...items].sort((a, b) => {
    const aTime = a?.event_at ? new Date(a.event_at).getTime() : 0;
    const bTime = b?.event_at ? new Date(b.event_at).getTime() : 0;
    return bTime - aTime;
  });
}

function formatAmount(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function serviceEventBilling(event) {
  const meta = event.metadata;
  if (!meta) return null;
  let billing = meta.admin_billing_type;
  if (!billing && meta.service_type) {
    billing = meta.service_type === "Paid Service" ? "Paid" : "Free";
  }
  if (!billing) return null;
  const amount = meta.amount ?? meta.approved_amount ?? meta.final_amount;
  return { billing, amount };
}

export default function SerialHistory() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSerial = searchParams.get("serial") || "";
  const [input, setInput] = useState(initialSerial);
  const [header, setHeader] = useState(null);
  const [events, setEvents] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [err, setErr] = useState("");
  const [openSuggestions, setOpenSuggestions] = useState(false);
  const debounceRef = useRef(null);
  const rootRef = useRef(null);
  const sortedEvents = sortEventsDesc(events);

  useEffect(() => {
    const serial = searchParams.get("serial");
    if (!serial) return;
    setLoading(true);
    setErr("");
    serialApi.history(serial)
      .then(({ data }) => {
        setHeader(data.header);
        setEvents(data.events || []);
      })
      .catch((e) => {
        setHeader(null);
        setEvents([]);
        setErr(e.response?.data?.detail || "Failed to load serial history");
      })
      .finally(() => setLoading(false));
  }, [searchParams]);

  useEffect(() => {
    function onDocClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpenSuggestions(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!input.trim()) {
      setSuggestions([]);
      setOpenSuggestions(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      setSearching(true);
      serialApi.historySearch(input.trim())
        .then(({ data }) => {
          setSuggestions(data || []);
          setOpenSuggestions(true);
        })
        .catch(() => {
          setSuggestions([]);
          setOpenSuggestions(true);
        })
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [input]);

  function selectSerial(serial) {
    setInput(serial);
    setOpenSuggestions(false);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("serial", serial);
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Serial Number History</h1>
        <p className="mt-1 text-sm text-slate-500">Track the full lifecycle of a product from order through service, claims, and future events.</p>
      </div>

      <div className="rounded-xl bg-white p-5 shadow-sm" ref={rootRef}>
        <label className="mb-2 block text-sm font-medium text-slate-700">Search by Serial Number</label>
        <div className="relative">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => suggestions.length && setOpenSuggestions(true)}
            placeholder="Enter serial number..."
            className="w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {searching && <span className="absolute right-3 top-2.5 animate-spin text-slate-400">|</span>}
          {openSuggestions && (
            <div className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
              {suggestions.length === 0 && !searching && (
                <div className="px-3 py-2 text-sm text-slate-400">No serials found.</div>
              )}
              {suggestions.map((item) => (
                <button
                  key={`${item.serial_no}-${item.order_no || ""}`}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => selectSerial(item.serial_no)}
                  className="block w-full px-3 py-2 text-left hover:bg-brand-50"
                >
                  <div className="text-sm font-medium text-slate-800">{item.serial_no}</div>
                  <div className="text-xs text-slate-500">{item.item_name || "Unknown item"} {item.order_no ? `| ${item.order_no}` : ""} {item.customer_name ? `| ${item.customer_name}` : ""}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {loading && (
        <div className="rounded-xl bg-white p-6 text-center text-slate-500 shadow-sm">
          <span className="inline-flex items-center gap-2"><span className="animate-spin">|</span> Loading history...</span>
        </div>
      )}

      {!loading && header && (
        <>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Serial Number</div>
                <div className="mt-1 text-lg font-semibold text-slate-900">{header.serial_no}</div>
                {header.serial_no_2 && <div className="text-sm text-slate-500">Secondary: {header.serial_no_2}</div>}
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Product</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{header.item_name || "-"}</div>
                <div className="text-sm text-slate-500">{header.item_code || "-"}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Order</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{header.order_no || "-"}</div>
                <div className="text-sm text-slate-500">{header.vendor_name || "-"}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{header.customer_name || "-"}</div>
                <div className="text-sm text-slate-500">{header.customer_contact || "-"}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Installation Status</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{header.installation_status}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Service Balance</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{header.free_service_count} free / {header.service_consume_count} consumed</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">PCB Warranty</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{fmtWarranty(header.pcb_warranty_years, header.pcb_warranty_date)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Component Warranty</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{fmtWarranty(header.component_warranty_years, header.component_warranty_date)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Machine Warranty</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{fmtWarranty(header.machine_warranty_years, header.machine_warranty_date)}</div>
              </div>
            </div>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Lifecycle Timeline</h2>
              <div className="text-xs text-slate-500">Newest first</div>
            </div>
            {sortedEvents.length === 0 ? (
              <div className="rounded-md bg-slate-50 px-4 py-5 text-sm text-slate-500">No history events found for this serial yet.</div>
            ) : (
              <div className="space-y-4">
                {sortedEvents.map((event) => (
                  <article key={event.id} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <EventBadge type={event.event_type} />
                        {event.event_subtype && <span className="text-xs text-slate-500">{event.event_subtype.replaceAll("_", " ")}</span>}
                      </div>
                      <div className="text-xs text-slate-500">{fmt(event.event_at)}</div>
                    </div>
                    <h3 className="mt-3 text-sm font-semibold text-slate-900">{event.title}</h3>
                    {event.event_type === "SERVICE" && (() => {
                      const billingInfo = serviceEventBilling(event);
                      if (!billingInfo) return null;
                      const amountLabel = billingInfo.billing === "Paid" ? formatAmount(billingInfo.amount) : null;
                      return (
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              billingInfo.billing === "Paid"
                                ? "bg-violet-100 text-violet-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {billingInfo.billing === "Paid" ? "Paid service" : "Free service"}
                          </span>
                          {amountLabel != null && (
                            <span className="text-xs font-medium text-slate-700">
                              Amount: ₹{amountLabel}
                            </span>
                          )}
                          {billingInfo.billing === "Paid" && amountLabel == null && (
                            <span className="text-xs text-slate-500">Amount not recorded yet</span>
                          )}
                        </div>
                      );
                    })()}
                    <p className="mt-1 text-sm text-slate-700">{event.description}</p>
                    <div className="mt-2 text-xs text-slate-500">Performed By: {event.performed_by || "System"}</div>
                    {event.remarks && <div className="mt-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">{event.remarks}</div>}
                    {event.metadata && (
                      <details className="mt-2 text-xs text-slate-500">
                        <summary className="cursor-pointer">Additional details</summary>
                        <pre className="mt-2 overflow-auto rounded-md bg-slate-950 p-3 text-[11px] text-slate-100">{JSON.stringify(event.metadata, null, 2)}</pre>
                      </details>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
