import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Modal from "../components/Modal.jsx";
import Pagination from "../components/Pagination.jsx";
import { ordersApi } from "../api/orders.js";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const ORDER_STATUSES = ["Pending", "In Transit", "Delivered", "Returned"];

const STATUS_BADGE = {
  Pending:    "bg-amber-400 text-white",
  "In Transit": "bg-sky-400 text-white",
  Delivered:  "bg-emerald-600 text-white",
  Returned:   "bg-rose-600 text-white",
};

const STAT_CARDS = [
  { key: "total",      label: "Total Orders",   bg: "bg-amber-400",   icon: "🛒", filter: ""           },
  { key: "pending",    label: "Pending Orders", bg: "bg-rose-600",    icon: "⏳", filter: "Pending"    },
  { key: "in_transit", label: "In Transit",     bg: "bg-emerald-600", icon: "🚚", filter: "In Transit" },
  { key: "delivered",  label: "Delivered",      bg: "bg-sky-400",     icon: "✅", filter: "Delivered"  },
];

const SORT_COLS = [
  { key: "id",                    label: "ID"           },
  { key: "order_no",              label: "Order No"     },
  { key: "order_date",            label: "Date"         },
  { key: "oem_bill_no",           label: "OEM Bill"     },
  { key: "status",                label: "Status"       },
  { key: "vendor_name",           label: "Vendor"       },
  { key: "courier_name",          label: "Courier"      },
  { key: "customer_name",         label: "Customer"     },
  { key: "customer_city",         label: "City"         },
  { key: "expected_delivery_date",label: "Exp. Delivery"},
];

function fmtDate(s) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-IN", {
      day: "2-digit", month: "2-digit", year: "numeric",
    });
  } catch { return s; }
}

// Simple client-side sort of the current page
function sortRows(rows, key, dir) {
  if (!key) return rows;
  return [...rows].sort((a, b) => {
    const va = a[key] ?? "";
    const vb = b[key] ?? "";
    const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true });
    return dir === "asc" ? cmp : -cmp;
  });
}

export default function VendorDashboard() {
  const navigate    = useNavigate();
  const batchRef    = useRef(null);
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const isVendor = role === "vendor";

  const [summary, setSummary]               = useState(null);
  const [data, setData]                     = useState({ items: [], total: 0 });
  const [loading, setLoading]               = useState(false);
  const [err, setErr]                       = useState("");
  const [filters, setFilters]               = useState({ search: "", status: "" });
  const [page, setPage]                     = useState(1);
  const [perPage, setPerPage]               = useState(20);
  const [selected, setSelected]             = useState(new Set());
  const [sortKey, setSortKey]               = useState("id");
  const [sortDir, setSortDir]               = useState("desc");
  const [batchOpen, setBatchOpen]           = useState(false);
  const [batchStatusModal, setBatchStatusModal] = useState(false);
  const [batchNewStatus, setBatchNewStatus]     = useState("");
  const [confirmBatchDel, setConfirmBatchDel]   = useState(false);
  const [confirmDelete, setConfirmDelete]       = useState(null);
  const [toast, setToast]                   = useState("");

  // Close batch dropdown on outside click
  useEffect(() => {
    function handler(e) {
      if (batchRef.current && !batchRef.current.contains(e.target)) {
        setBatchOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function loadSummary() {
    api.get("/api/dashboard/orders-summary")
      .then((r) => setSummary(r.data))
      .catch(() => {});
  }

  useEffect(() => { loadSummary(); }, []);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: filters.status || undefined,
    search: filters.search || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const result = await ordersApi.list(params);
      setData(result);
      setSelected(new Set());
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load orders");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  // Displayed (sorted) rows
  const rows = sortRows(data.items, sortKey, sortDir);
  const showStatusColumn = !isVendor || rows.some((o) => o.oem_bill_no);
  const visibleColumns = isVendor
    ? SORT_COLS.filter((col) => !(col.key === "status" && !showStatusColumn))
    : SORT_COLS;

  // Checkbox helpers
  const allChecked = rows.length > 0 && rows.every((o) => selected.has(o.id));
  const someChecked = !allChecked && rows.some((o) => selected.has(o.id));

  function toggleAll() {
    if (allChecked) {
      setSelected(new Set());
    } else {
      setSelected(new Set(rows.map((o) => o.id)));
    }
  }

  function toggleRow(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  // Sort column click
  function handleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  // Stat card click filters
  function clickCard(filter) {
    setFilters((f) => ({ ...f, status: f.status === filter ? "" : filter }));
    setPage(1);
  }

  // Batch delete
  async function doBatchDelete() {
    const ids = [...selected];
    try {
      await Promise.all(ids.map((id) => ordersApi.remove(id)));
      setConfirmBatchDel(false);
      setSelected(new Set());
      showToast(`${ids.length} order(s) deleted`);
      load();
      loadSummary();
    } catch {
      alert("Failed to delete some orders");
    }
  }

  // Batch status update
  async function doBatchStatus() {
    if (!batchNewStatus) return;
    const ids = [...selected];
    try {
      await Promise.all(ids.map((id) => ordersApi.update(id, { status: batchNewStatus })));
      setBatchStatusModal(false);
      setBatchNewStatus("");
      setSelected(new Set());
      showToast(`${ids.length} order(s) updated to "${batchNewStatus}"`);
      load();
      loadSummary();
    } catch {
      alert("Failed to update some orders");
    }
  }

  // Single delete
  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await ordersApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      showToast("Order deleted");
      load();
      loadSummary();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  function exportCsv() {
    const url = ordersApi.exportUrl({
      status: filters.status || undefined,
      search: filters.search || undefined,
    });
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `orders_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(obj);
      });
  }

  return (
    <div className="space-y-4">

      {/* ── Page Header ── */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <h1 className="text-xl font-semibold text-slate-800">
          Vendor Order Dashboard
          <span className="ml-2 text-sm font-normal text-slate-400">Overview</span>
        </h1>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="text-brand-600">🏠</span>
          <span>/</span>
          <span>Vendor-dashboards</span>
        </nav>
      </div>

      {/* ── Stat Cards (icon layout) ── */}
      <div className="flex flex-wrap gap-4">
        {STAT_CARDS.map((card) => (
          <div
            key={card.key}
            onClick={() => clickCard(card.filter)}
            className={`flex flex-1 min-w-[160px] cursor-pointer items-center gap-4 rounded p-5 shadow transition-transform hover:-translate-y-0.5 hover:shadow-md ${card.bg} ${filters.status === card.filter && card.filter ? "ring-2 ring-offset-1 ring-white/50" : ""}`}
          >
            <div className="text-4xl opacity-90">{card.icon}</div>
            <div>
              <h5 className="text-base font-semibold text-white">{card.label}</h5>
              <p className="mt-0.5 text-sm text-white/85">
                {summary ? (summary[card.key] ?? 0) : "—"} Orders
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Search + Action bar ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded bg-white p-3 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Search order no / OEM bill / customer…"
            value={filters.search}
            onChange={(e) => { setFilters((f) => ({ ...f, search: e.target.value })); setPage(1); }}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
          />
          <select
            value={filters.status}
            onChange={(e) => { setFilters((f) => ({ ...f, status: e.target.value })); setPage(1); }}
            className="rounded border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700"
          >
            <option value="">All statuses</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <button
            onClick={exportCsv}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Export CSV
          </button>
          <Link
            to="/orders/new"
            className="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            + New Order
          </Link>
        </div>
      </div>

      {err && (
        <div className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      {/* ── Table Card ── */}
      <div className="overflow-hidden rounded bg-white shadow-sm">

        {/* Batch action bar */}
        <div className="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5">
          <div className="relative" ref={batchRef}>
            <div className="inline-flex overflow-hidden rounded">
              <button
                onClick={() => { if (selected.size > 0) setBatchOpen((o) => !o); }}
                className={`flex items-center gap-1.5 border-r border-white/30 bg-brand-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-brand-700 ${selected.size === 0 ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
              >
                ⚙ Batch Actions
              </button>
              <button
                onClick={() => { if (selected.size > 0) setBatchOpen((o) => !o); }}
                className={`bg-brand-600 px-2 py-1.5 text-sm text-white transition-colors hover:bg-brand-700 ${selected.size === 0 ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
              >
                ▾
              </button>
            </div>

            {batchOpen && selected.size > 0 && (
              <div className="absolute left-0 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded border border-slate-200 bg-white shadow-lg">
                <button
                  onClick={() => { setBatchOpen(false); setBatchStatusModal(true); }}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  ✏️ Edit Status
                </button>
                <div className="border-t border-slate-100" />
                <button
                  onClick={() => { setBatchOpen(false); setConfirmBatchDel(true); }}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-rose-600 hover:bg-rose-50"
                >
                  🗑 Delete Selected
                </button>
              </div>
            )}
          </div>

          {selected.size > 0 && (
            <span className="text-sm text-slate-500">
              {selected.size} row{selected.size !== 1 ? "s" : ""} selected
            </span>
          )}
        </div>

        {/* Table */}
        <div className="crm-scroll">
          <table className="min-w-full text-xs">
            <thead className="border-b-2 border-slate-200 bg-slate-50">
              <tr>
                <th className="w-10 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={allChecked}
                    ref={(el) => { if (el) el.indeterminate = someChecked; }}
                    onChange={toggleAll}
                    className="cursor-pointer accent-brand-600"
                  />
                </th>
                {visibleColumns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="cursor-pointer select-none whitespace-nowrap px-3 py-2.5 text-left font-semibold text-slate-600 hover:text-brand-600"
                  >
                    {col.label}
                    <span className="ml-1 text-[10px] text-slate-400">
                      {sortKey === col.key
                        ? sortDir === "asc" ? "▲" : "▼"
                        : "⇅"}
                    </span>
                  </th>
                ))}
                {!isVendor && <th className="px-3 py-2.5 text-left font-semibold text-slate-600">Action</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={visibleColumns.length + (!isVendor ? 2 : 1)} className="py-10 text-center text-slate-400">
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={visibleColumns.length + (!isVendor ? 2 : 1)} className="py-10 text-center text-slate-400">
                    No orders found.
                  </td>
                </tr>
              )}
              {!loading && rows.map((o) => {
                const isSel = selected.has(o.id);
                return (
                  <tr
                    key={o.id}
                    className={`transition-colors ${isSel ? "bg-sky-50" : "hover:bg-slate-50/60"}`}
                  >
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={isSel}
                        onChange={() => toggleRow(o.id)}
                        className="cursor-pointer accent-brand-600"
                      />
                    </td>
                    {visibleColumns.map((col) => {
                      const value = (() => {
                        switch (col.key) {
                          case "id": return o.id;
                          case "order_no": return o.order_no;
                          case "order_date": return fmtDate(o.order_date);
                          case "oem_bill_no": return o.oem_bill_no || "—";
                          case "status": return (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${STATUS_BADGE[o.status] || "bg-slate-200 text-slate-700"}`}>
                              {o.status}
                            </span>
                          );
                          case "vendor_name": return o.vendor_name || "—";
                          case "courier_name": return o.courier_name || "—";
                          case "customer_name": return o.customer_name || "—";
                          case "customer_city": return o.customer_city || "—";
                          case "expected_delivery_date": return fmtDate(o.expected_delivery_date);
                          default: return "—";
                        }
                      })();

                      return (
                        <td
                          key={col.key}
                          className={`px-3 py-2 text-slate-600 ${col.key === "order_no" ? "max-w-[160px] truncate font-mono text-slate-700" : ""} ${col.key === "order_date" || col.key === "expected_delivery_date" ? "whitespace-nowrap" : ""}`}
                          title={col.key === "order_no" ? o.order_no : undefined}
                        >
                          {col.key === "id" ? <span className="font-medium text-slate-700">{value}</span> : value}
                        </td>
                      );
                    })}
                    {!isVendor && (
                      <td className="px-3 py-2">
                        <button
                          title="View"
                          onClick={() => navigate(`/orders/${o.id}`)}
                          className="text-base text-slate-500 transition-colors hover:text-brand-600"
                        >
                          👁
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Table footer */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-3 py-2.5 text-sm text-slate-600">
          <span>
            Showing{" "}
            <strong>{data.total > 0 ? (page - 1) * perPage + 1 : 0}</strong> to{" "}
            <strong>{Math.min(page * perPage, data.total)}</strong> of{" "}
            <strong>{data.total}</strong> entries
          </span>
          <div className="flex items-center gap-2">
            Show
            <select
              value={perPage}
              onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1); }}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            >
              {[10, 20, 30, 50].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            entries
          </div>
          <Pagination
            page={page}
            perPage={perPage}
            total={data.total}
            onPageChange={setPage}
            onPerPageChange={(n) => { setPerPage(n); setPage(1); }}
          />
        </div>
      </div>

      {/* ── Batch Status Modal ── */}
      <Modal
        open={batchStatusModal}
        onClose={() => setBatchStatusModal(false)}
        title={`Update status — ${selected.size} order(s) selected`}
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">New Status</label>
            <select
              value={batchNewStatus}
              onChange={(e) => setBatchNewStatus(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">-- Select --</option>
              {ORDER_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setBatchStatusModal(false)}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doBatchStatus}
              disabled={!batchNewStatus}
              className="rounded bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Update
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Batch Delete Modal ── */}
      <Modal
        open={confirmBatchDel}
        onClose={() => setConfirmBatchDel(false)}
        title="Delete selected orders?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete <strong>{selected.size}</strong> selected order(s).
            This cannot be undone from the UI.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmBatchDel(false)}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doBatchDelete}
              className="rounded bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Single Delete Modal ── */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete order?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete order{" "}
            <span className="font-mono font-semibold">{confirmDelete?.order_no}</span>.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doDelete}
              className="rounded bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Toast ── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded bg-slate-800 px-4 py-3 text-sm text-white shadow-xl">
          {toast}
        </div>
      )}
    </div>
  );
}
