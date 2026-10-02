import { useEffect, useMemo, useState } from "react";
import { marketApi } from "../../api/market.js";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

const ORDER_STATUSES = ["Pending", "Processing", "Delivered", "Cancelled"];

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN"); } catch { return s; }
}

function fmtRupee(v) {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function StatusBadge({ value }) {
  const colors = {
    Pending: "bg-amber-100 text-amber-700",
    Processing: "bg-blue-100 text-blue-700",
    Delivered: "bg-green-100 text-green-700",
    Cancelled: "bg-rose-100 text-rose-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colors[value] || "bg-slate-100 text-slate-500"}`}>
      {value}
    </span>
  );
}

const EMPTY_LINE = { item_id: "", qty: 1, unit_price: "" };

function OrderCreateModal({ open, onClose, onCreated, marketUsers, marketItems }) {
  const [form, setForm] = useState({
    retailer_id: "",
    distributor_id: "",
    status: "Pending",
    notes: "",
  });
  const [lines, setLines] = useState([{ ...EMPTY_LINE }]);
  const [err, setErr] = useState("");

  function reset() {
    setForm({ retailer_id: "", distributor_id: "", status: "Pending", notes: "" });
    setLines([{ ...EMPTY_LINE }]);
    setErr("");
  }

  function addLine() {
    setLines((l) => [...l, { ...EMPTY_LINE }]);
  }

  function removeLine(idx) {
    setLines((l) => l.filter((_, i) => i !== idx));
  }

  function updateLine(idx, patch) {
    setLines((l) => l.map((line, i) => (i === idx ? { ...line, ...patch } : line)));
  }

  const clientTotal = lines.reduce((sum, l) => {
    const qty = parseInt(l.qty) || 0;
    const up = parseFloat(l.unit_price) || 0;
    return sum + qty * up;
  }, 0);

  async function doSubmit() {
    setErr("");
    try {
      const body = {
        retailer_id: form.retailer_id ? parseInt(form.retailer_id) : null,
        distributor_id: form.distributor_id ? parseInt(form.distributor_id) : null,
        status: form.status,
        notes: form.notes || null,
        items: lines
          .filter((l) => l.item_id || l.qty)
          .map((l) => ({
            item_id: l.item_id ? parseInt(l.item_id) : null,
            qty: parseInt(l.qty) || 1,
            unit_price: l.unit_price ? parseFloat(l.unit_price) : null,
          })),
      };
      await marketApi.createOrder(body);
      reset();
      onCreated();
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to create order");
    }
  }

  return (
    <Modal open={open} onClose={() => { reset(); onClose(); }} title="New Order" maxWidth="max-w-3xl">
      {err && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={labelClass}>Retailer</label>
            <select
              value={form.retailer_id}
              onChange={(e) => setForm((f) => ({ ...f, retailer_id: e.target.value }))}
              className={fieldClass}
            >
              <option value="">— None —</option>
              {marketUsers.filter((u) => u.role === "Retailer" || u.role === "Admin").map((u) => (
                <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Distributor</label>
            <select
              value={form.distributor_id}
              onChange={(e) => setForm((f) => ({ ...f, distributor_id: e.target.value }))}
              className={fieldClass}
            >
              <option value="">— None —</option>
              {marketUsers.filter((u) => u.role === "Distributor" || u.role === "Admin").map((u) => (
                <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Status</label>
            <select
              value={form.status}
              onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
              className={fieldClass}
            >
              {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className={labelClass}>Notes</label>
          <textarea
            rows={2}
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            className={fieldClass}
          />
        </div>

        {/* Line items */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">Line Items</span>
            <button
              type="button"
              onClick={addLine}
              className="rounded-md border border-brand-600 px-2 py-1 text-xs text-brand-600 hover:bg-brand-50"
            >
              + Add Item
            </button>
          </div>
          <div className="space-y-2">
            {lines.map((line, idx) => (
              <div key={idx} className="flex gap-2 items-center">
                <select
                  value={line.item_id}
                  onChange={(e) => updateLine(idx, { item_id: e.target.value })}
                  className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">— Select Item —</option>
                  {marketItems.map((i) => (
                    <option key={i.id} value={i.id}>{i.sku} — {i.name}</option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="Qty"
                  value={line.qty}
                  onChange={(e) => updateLine(idx, { qty: e.target.value })}
                  className="w-20 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Unit Price"
                  value={line.unit_price}
                  onChange={(e) => updateLine(idx, { unit_price: e.target.value })}
                  className="w-28 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                />
                <span className="w-24 text-right text-sm text-slate-600">
                  {fmtRupee((parseInt(line.qty) || 0) * (parseFloat(line.unit_price) || 0))}
                </span>
                {lines.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeLine(idx)}
                    className="rounded p-1 text-rose-500 hover:bg-rose-50"
                  >✕</button>
                )}
              </div>
            ))}
          </div>
          <div className="mt-2 text-right text-sm font-semibold text-slate-700">
            Total: {fmtRupee(clientTotal)}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => { reset(); onClose(); }}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >Cancel</button>
          <button
            type="button"
            onClick={doSubmit}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >Create Order</button>
        </div>
      </div>
    </Modal>
  );
}

function OrderDetailModal({ open, onClose, order }) {
  if (!order) return null;
  return (
    <Modal open={open} onClose={onClose} title={`Order ${order.order_no}`} maxWidth="max-w-2xl">
      <div className="space-y-4 text-sm">
        <div className="grid grid-cols-2 gap-3">
          {[
            ["Order #", order.order_no],
            ["Status", order.status],
            ["Retailer", order.retailer_name || "—"],
            ["Distributor", order.distributor_name || "—"],
            ["Total Amount", fmtRupee(order.total_amount)],
            ["Created", fmtDate(order.created_at)],
          ].map(([label, val]) => (
            <div key={label}>
              <div className="text-xs text-slate-500">{label}</div>
              <div className="font-medium text-slate-800">{val}</div>
            </div>
          ))}
        </div>
        {order.notes && (
          <div>
            <div className="text-xs text-slate-500">Notes</div>
            <div className="text-slate-700">{order.notes}</div>
          </div>
        )}
        {order.items && order.items.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-semibold text-slate-600 uppercase tracking-wide">Line Items</div>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-2 py-1 text-left text-slate-600">Item</th>
                  <th className="px-2 py-1 text-right text-slate-600">Qty</th>
                  <th className="px-2 py-1 text-right text-slate-600">Unit Price</th>
                  <th className="px-2 py-1 text-right text-slate-600">Subtotal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {order.items.map((oi) => (
                  <tr key={oi.id}>
                    <td className="px-2 py-1">{oi.item_name || `Item #${oi.item_id}`}</td>
                    <td className="px-2 py-1 text-right">{oi.qty}</td>
                    <td className="px-2 py-1 text-right">{fmtRupee(oi.unit_price)}</td>
                    <td className="px-2 py-1 text-right">{fmtRupee(oi.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >Close</button>
        </div>
      </div>
    </Modal>
  );
}

export default function MarketOrders() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({ search: "", status: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const [marketUsers, setMarketUsers] = useState([]);
  const [marketItems, setMarketItems] = useState([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [detailOrder, setDetailOrder] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [statusOrder, setStatusOrder] = useState(null);
  const [statusForm, setStatusForm] = useState({ status: "Pending", notes: "" });
  const [statusErr, setStatusErr] = useState("");

  const [confirmDelete, setConfirmDelete] = useState(null);

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
      setData(await marketApi.listOrders(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load orders");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    marketApi.lookupUsers()
      .then(setMarketUsers)
      .catch(() => {});
    marketApi.listItems({ per_page: 200 })
      .then((r) => setMarketItems(r.items || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  async function openDetail(order) {
    setDetailLoading(true);
    try {
      const full = await marketApi.getOrder(order.id);
      setDetailOrder(full);
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to load order detail");
    } finally {
      setDetailLoading(false);
    }
  }

  function openStatus(order) {
    setStatusOrder(order);
    setStatusForm({ status: order.status, notes: "" });
    setStatusErr("");
  }

  async function doStatusUpdate() {
    setStatusErr("");
    try {
      await marketApi.updateOrder(statusOrder.id, {
        status: statusForm.status,
        notes: statusForm.notes || null,
      });
      setStatusOrder(null);
      load();
    } catch (e) {
      setStatusErr(e.response?.data?.detail || "Failed to update status");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await marketApi.deleteOrder(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete order");
    }
  }

  const pending = data.items.filter((o) => o.status === "Pending").length;
  const delivered = data.items.filter((o) => o.status === "Delivered").length;
  const cancelled = data.items.filter((o) => o.status === "Cancelled").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Market Orders</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Total: {data.total} | Pending: {pending} | Delivered: {delivered} | Cancelled: {cancelled}
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New Order
        </button>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            type="text"
            placeholder="Search order #…"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={filters.status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">Order #</th>
              <th className="px-3 py-2">Retailer</th>
              <th className="px-3 py-2">Distributor</th>
              <th className="px-3 py-2">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No orders found.</td></tr>
            )}
            {!loading && data.items.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs text-slate-700">{o.order_no}</td>
                <td className="px-3 py-2">{o.retailer_name || "—"}</td>
                <td className="px-3 py-2">{o.distributor_name || "—"}</td>
                <td className="px-3 py-2">{fmtRupee(o.total_amount)}</td>
                <td className="px-3 py-2"><StatusBadge value={o.status} /></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(o.created_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View Detail"
                      onClick={() => openDetail(o)}
                      disabled={detailLoading}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >👁</button>
                    <button
                      title="Update Status"
                      onClick={() => openStatus(o)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >✏️</button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(o)}
                      className="rounded p-1 text-rose-600 hover:bg-rose-50"
                    >🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(n) => { setPerPage(n); setPage(1); }}
      />

      <OrderCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => { setCreateOpen(false); load(); }}
        marketUsers={marketUsers}
        marketItems={marketItems}
      />

      <OrderDetailModal
        open={!!detailOrder}
        onClose={() => setDetailOrder(null)}
        order={detailOrder}
      />

      {/* Status Update Modal */}
      <Modal open={!!statusOrder} onClose={() => setStatusOrder(null)} title="Update Order Status">
        {statusErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{statusErr}</div>}
        <div className="space-y-3">
          <div>
            <label className={labelClass}>Status</label>
            <select
              value={statusForm.status}
              onChange={(e) => setStatusForm((f) => ({ ...f, status: e.target.value }))}
              className={fieldClass}
            >
              {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Notes (optional)</label>
            <textarea
              rows={2}
              value={statusForm.notes}
              onChange={(e) => setStatusForm((f) => ({ ...f, notes: e.target.value }))}
              className={fieldClass}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setStatusOrder(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              onClick={doStatusUpdate}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >Update</button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirm */}
      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete Order?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete order <span className="font-mono">{confirmDelete?.order_no}</span>? This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >Delete</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
