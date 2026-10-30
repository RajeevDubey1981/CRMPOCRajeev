import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client.js";
import { formatApiError } from "../../utils/apiError.js";

function fmtMoney(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; }
}

function todayInputValue() {
  return new Date().toISOString().slice(0, 10);
}

const URGENCY = {
  urgent: { label: "7+ days", cls: "bg-rose-100 text-rose-700", icon: "⚠ " },
  soon: { label: "3–6 days", cls: "bg-amber-100 text-amber-700", icon: "" },
  ontime: { label: "On time", cls: "bg-emerald-100 text-emerald-700", icon: "" },
};

const BUCKET_LABEL = { all: "Ready to pay", urgent: "Urgent (7+ days)", soon: "Due soon (3–6 days)", ontime: "On time" };

function payeeKey(item) {
  return item.payee_id ? `${item.payee_type}-${item.payee_id}` : null;
}

function PoolPayModal({ items, onClose, onPaid }) {
  const total = items.reduce((sum, i) => sum + i.amount, 0);
  const payeeName = items[0]?.payee_name || "—";
  const payeeType = items[0]?.payee_type || "";
  const [paymentType, setPaymentType] = useState("Cash");
  const [reference, setReference] = useState("");
  const [paidOn, setPaidOn] = useState(todayInputValue());
  const [proofFile, setProofFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function confirm() {
    if (!reference.trim()) {
      setErr("Payment reference / UTR is required");
      return;
    }
    if (paymentType === "UPI" && !proofFile) {
      setErr("Upload the payment proof / screenshot for a UPI transfer");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const refs = items.map((i) => ({
        module: i.module,
        entity_id: i.entity_id,
        payment_request_id: i.payment_request_id ?? null,
      }));
      const fd = new FormData();
      fd.append("refs", JSON.stringify(refs));
      fd.append("payment_type", paymentType);
      fd.append("payment_reference", reference.trim());
      fd.append("payment_paid_on", paidOn);
      if (proofFile) fd.append("proof_document", proofFile);
      const res = await api.post("/api/dashboard/ready-to-pay/bulk-pay", fd);
      onPaid(res.data);
    } catch (e) {
      setErr(formatApiError(e, "Failed to record this payment"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-xl">
        <h2 className="text-base font-semibold text-slate-800">Pay {payeeName} — {items.length} request{items.length === 1 ? "" : "s"} pooled</h2>
        <p className="mt-1 text-sm text-slate-500">
          One transfer settles all {items.length}. Each one still gets recorded paid for its own amount; the reference and date below apply to every one of them.
        </p>

        <div className="mt-3 max-h-36 overflow-y-auto rounded-md border border-slate-200">
          <table className="w-full text-left text-xs">
            <tbody>
              {items.map((i) => (
                <tr key={`${i.module}-${i.entity_id}-${i.payment_request_id ?? ""}`} className="border-b border-slate-100 last:border-0">
                  <td className="px-2 py-1 font-mono">{i.label}</td>
                  <td className="px-2 py-1 text-slate-500">{i.module === "installation" ? "Installation" : "Service"}</td>
                  <td className="px-2 py-1 text-right font-mono">{fmtMoney(i.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
          <span className="text-sm text-slate-600">Pooled total ({payeeType})</span>
          <span className="text-lg font-bold text-slate-800">{fmtMoney(total)}</span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Payment type</label>
            <select value={paymentType} onChange={(e) => setPaymentType(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="Cash">Cash</option>
              <option value="UPI">UPI</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Paid on</label>
            <input type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-wide text-slate-500">Payment reference / UTR</label>
            <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="e.g. the bank transfer's UTR" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-wide text-slate-500">
              Payment proof {paymentType === "UPI" && <span className="text-rose-600">*</span>}
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              onChange={(e) => setProofFile(e.target.files?.[0] || null)}
              className="mt-1 block w-full text-sm"
            />
            <p className="mt-1 text-xs text-slate-500">One receipt covers the whole pooled transfer.</p>
          </div>
        </div>

        {err && <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={busy} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
            Cancel
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={busy}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {busy ? "Paying…" : `Pay ${fmtMoney(total)}`}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Everything that's cleared Audit and is sitting at the Admin stage, across both Installations
 * and Service Requests -- a finding/prioritizing view. "Pay now" opens that single record's own
 * detail page; checking several rows for the SAME engineer or vendor pools them into one payment
 * instead -- one reference and date, each request still recorded paid for its own amount. */
export default function ReadyToPayQueue() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [engineerFilter, setEngineerFilter] = useState("");
  const [vendorFilter, setVendorFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [sortBy, setSortBy] = useState("oldest");
  const [bucket, setBucket] = useState("all");
  const [selected, setSelected] = useState(new Set());
  const [showPoolModal, setShowPoolModal] = useState(false);
  const [toast, setToast] = useState("");

  function load() {
    setLoading(true);
    api.get("/api/dashboard/ready-to-pay", {
      params: {
        search: search || undefined,
        engineer: engineerFilter || undefined,
        vendor: vendorFilter || undefined,
        module: moduleFilter || undefined,
      },
    })
      .then((r) => setItems(r.data))
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(load, [search, engineerFilter, vendorFilter, moduleFilter]);

  const counts = useMemo(() => ({
    all: items.length,
    urgent: items.filter((i) => i.urgency === "urgent").length,
    soon: items.filter((i) => i.urgency === "soon").length,
    ontime: items.filter((i) => i.urgency === "ontime").length,
  }), [items]);

  const visible = useMemo(() => {
    let rows = bucket === "all" ? items : items.filter((i) => i.urgency === bucket);
    rows = [...rows];
    if (sortBy === "oldest") rows.sort((a, b) => b.days_waiting - a.days_waiting);
    else if (sortBy === "newest") rows.sort((a, b) => a.days_waiting - b.days_waiting);
    else if (sortBy === "amount") rows.sort((a, b) => b.amount - a.amount);
    return rows;
  }, [items, bucket, sortBy]);

  const rowId = (item) => `${item.module}-${item.entity_id}-${item.payment_request_id ?? ""}`;
  const selectedItems = useMemo(() => items.filter((i) => selected.has(rowId(i))), [items, selected]);
  const activePayeeKey = selectedItems.length > 0 ? payeeKey(selectedItems[0]) : null;
  const pooledTotal = selectedItems.reduce((sum, i) => sum + i.amount, 0);

  function toggle(item) {
    const id = rowId(item);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function afterPaid(result) {
    setShowPoolModal(false);
    setSelected(new Set());
    setToast(`Recorded ${result.paid} payment${result.paid === 1 ? "" : "s"} totalling ${fmtMoney(result.total_amount)}.`);
    setTimeout(() => setToast(""), 4000);
    load();
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Ready to pay</h1>
        <p className="text-sm text-slate-500">
          Everything here has already cleared Audit. "Waiting" flags how long it's been since the request was first raised, oldest first. Tick several for the same engineer or vendor to pay them in one pooled transfer.
        </p>
      </div>

      {err && <div className="rounded bg-rose-50 p-3 text-sm text-rose-700">{err}</div>}
      {toast && <div className="rounded bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{toast}</div>}

      <div className="flex flex-wrap gap-3">
        {["all", "urgent", "soon", "ontime"].map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setBucket(key)}
            className={`min-w-[150px] flex-1 rounded-lg bg-white p-3 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${
              bucket === key ? "ring-2" : ""
            } ${key === "urgent" ? "border-l-4 border-rose-600" : key === "soon" ? "border-l-4 border-amber-500" : key === "ontime" ? "border-l-4 border-emerald-600" : "border-l-4 border-slate-700"}`}
            style={bucket === key ? { "--tw-ring-color": key === "urgent" ? "#be123c" : key === "soon" ? "#b45309" : key === "ontime" ? "#047857" : "#334155" } : undefined}
          >
            <div className={`text-xl font-extrabold ${key === "urgent" ? "text-rose-700" : key === "soon" ? "text-amber-700" : key === "ontime" ? "text-emerald-700" : "text-slate-800"}`}>
              {counts[key]}
            </div>
            <div className="text-xs uppercase tracking-wide text-slate-500">{BUCKET_LABEL[key]}</div>
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Search (ID or name)</label>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="#4821" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Engineer</label>
            <input value={engineerFilter} onChange={(e) => setEngineerFilter(e.target.value)} placeholder="Name" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Vendor</label>
            <input value={vendorFilter} onChange={(e) => setVendorFilter(e.target.value)} placeholder="Name" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Module</label>
            <select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">All</option>
              <option value="installation">Installation</option>
              <option value="service">Service</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500">Sort by</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="oldest">Oldest first (most urgent)</option>
              <option value="newest">Newest first</option>
              <option value="amount">Amount, highest first</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-3 py-2" />
              <th className="px-3 py-2">Module</th>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Paying</th>
              <th className="px-3 py-2">Requested</th>
              <th className="px-3 py-2">Waiting</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Nothing here right now.</td></tr>
            )}
            {!loading && visible.map((item) => {
              const u = URGENCY[item.urgency] || URGENCY.ontime;
              const id = rowId(item);
              const key = payeeKey(item);
              const isSelected = selected.has(id);
              const disabled = !key || (activePayeeKey !== null && key !== activePayeeKey && !isSelected);
              return (
                <tr key={id} className={`border-b border-slate-100 hover:bg-slate-50 ${disabled ? "opacity-40" : ""}`}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={disabled}
                      onChange={() => toggle(item)}
                      title={!key ? "No engineer or vendor on this one to pool by" : disabled ? "Pick rows for the same engineer or vendor to pool them" : ""}
                      className="h-4 w-4"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase text-white ${item.module === "installation" ? "bg-sky-600" : "bg-violet-600"}`}>
                      {item.module === "installation" ? "Installation" : "Service"}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono">{item.label}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-slate-800">{item.payee_name || "—"}</div>
                    {item.payee_type && <div className="text-xs text-slate-500">{item.payee_type}</div>}
                  </td>
                  <td className="px-3 py-2">{fmtDate(item.requested_at)}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${u.cls}`}>
                      {u.icon}{item.days_waiting === 0 ? "Today" : `${item.days_waiting} day${item.days_waiting === 1 ? "" : "s"}`}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(item.amount)}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => navigate(item.href)}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
                    >
                      Pay now
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">
        "Pay now" opens that record's own detail page — the real Approve &amp; Release Payment form, same as today. Ticking rows pools them instead: pick several for the same engineer or vendor and the amount below is the one transfer that covers all of them.
      </p>

      {selectedItems.length > 0 && (
        <div className="sticky bottom-4 z-20 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 shadow-lg">
          <span className="text-sm font-semibold text-emerald-900">
            {selectedItems.length} selected for {selectedItems[0].payee_name} — pooled total {fmtMoney(pooledTotal)}
          </span>
          <div className="flex gap-2">
            <button type="button" onClick={() => setSelected(new Set())} className="rounded-md border border-emerald-300 px-3 py-1.5 text-xs font-semibold text-emerald-800">
              Clear
            </button>
            <button
              type="button"
              onClick={() => setShowPoolModal(true)}
              className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              Pay pooled amount
            </button>
          </div>
        </div>
      )}

      {showPoolModal && (
        <PoolPayModal items={selectedItems} onClose={() => setShowPoolModal(false)} onPaid={afterPaid} />
      )}
    </div>
  );
}
