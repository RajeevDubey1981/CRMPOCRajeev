import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import OrderSearchBar from "../../components/orders/OrderSearchBar.jsx";
import ParcelClicks from "../../components/ParcelClicks.jsx";
import { ordersApi } from "../../api/orders.js";
import { useAuth } from "../../auth/AuthContext.jsx";

const ORDER_STATUSES = ["Pending", "Shipped", "In Transit", "Delivered", "Returned", "Cancelled"];

const STATUS_BADGE = {
  Pending: "bg-amber-100 text-amber-700",
  Shipped: "bg-indigo-100 text-indigo-700",
  "In Transit": "bg-blue-100 text-blue-700",
  Delivered: "bg-green-100 text-green-700",
  Returned: "bg-red-100 text-red-700",
  Cancelled: "bg-slate-200 text-slate-600",
};

function StatusBadge({ value }) {
  const cls = STATUS_BADGE[value] || "bg-slate-100 text-slate-600";
  return (
    <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold leading-snug ${cls}`}>
      {value}
    </span>
  );
}

const ORDER_TABLE_COL = {
  id: "w-14 whitespace-nowrap px-3 py-2",
  orderNo: "min-w-[12rem] whitespace-nowrap px-3 py-2",
  date: "whitespace-nowrap px-3 py-2",
  oem: "hidden max-w-[7rem] truncate px-3 py-2 lg:table-cell",
  status: "min-w-[7.5rem] whitespace-nowrap px-3 py-2",
  vendor: "max-w-[9rem] truncate px-3 py-2",
  courier: "hidden max-w-[6rem] truncate px-3 py-2 xl:table-cell",
  customer: "min-w-[8rem] max-w-[11rem] truncate px-3 py-2",
  city: "hidden max-w-[6rem] truncate px-3 py-2 md:table-cell",
  exp: "hidden whitespace-nowrap px-3 py-2 lg:table-cell",
  actions: "min-w-[11.5rem] whitespace-nowrap px-3 py-2 text-right",
};

function fmtDate(s) {
  if (!s) return "-";
  try { return new Date(s).toLocaleDateString(); } catch { return s; }
}

function buildFileUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return new URL(normalized, import.meta.env.VITE_API_BASE_URL || window.location.origin).toString();
}

function fileNameFromPath(path) {
  if (!path) return "order-document";
  const parts = path.split("/");
  return parts[parts.length - 1] || "order-document";
}

function SpinnerLabel({ label = "Loading..." }) {
  return (
    <span className="inline-flex items-center gap-2 text-slate-500">
      <span className="inline-block animate-spin">|</span>
      <span>{label}</span>
    </span>
  );
}

function ViewIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="m16.5 3.5 4 4L7 21l-4 1 1-4L16.5 3.5Z" />
    </svg>
  );
}

function DeleteIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

export default function OrderList() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const orderPermission = (Array.isArray(user?.permissions) ? user.permissions : [])
    .find((permission) => permission.module === "orders");
  const canCreateOrders = Boolean(orderPermission?.can_create);
  const canEditOrders = Boolean(orderPermission?.can_edit);
  const canDeleteOrders = Boolean(orderPermission?.can_delete);
  const canExportOrders = Boolean(orderPermission?.can_export);
  const listRequestRef = useRef(0);

  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [filters, setFilters] = useState({ status: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: filters.status || undefined,
    search: activeSearch || undefined,
  }), [page, perPage, filters.status, activeSearch]);

  async function load() {
    const requestId = ++listRequestRef.current;
    setLoading(true);
    setErr("");
    try {
      const result = await ordersApi.list(params);
      if (requestId !== listRequestRef.current) return;
      setData(result);
    } catch (e) {
      if (requestId !== listRequestRef.current) return;
      setErr(e.response?.data?.detail || "Failed to load orders");
    } finally {
      if (requestId === listRequestRef.current) {
        setLoading(false);
      }
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function applyStatus(value) {
    setFilters((f) => ({ ...f, status: value }));
    setPage(1);
  }

  function selectSuggestion(item, searchValue) {
    setSearchInput(searchValue);
    setActiveSearch(searchValue);
    setPage(1);
  }

  function handleDebouncedSearch(value) {
    setPage(1);
    setActiveSearch(value);
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await ordersApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  function exportCsv() {
    const url = ordersApi.exportUrl({
      status: filters.status || undefined,
      search: activeSearch || undefined,
    });
    const token = localStorage.getItem("indcool_token");
    const requestUrl = url.startsWith("http") ? url : `${window.location.origin}${url}`;
    fetch(requestUrl, { headers: { Authorization: `Bearer ${token}` } })
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
      <ParcelClicks />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Order List</h1>
        <div className="flex gap-2">
          {canExportOrders && (
            <button
              onClick={exportCsv}
              disabled={loading}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Export CSV
            </button>
          )}
          {canCreateOrders && (
            <Link
              to="/orders/new"
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              + New Order
            </Link>
          )}
        </div>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <OrderSearchBar
            className="md:col-span-2"
            value={searchInput}
            onChange={setSearchInput}
            onDebouncedSearch={handleDebouncedSearch}
            onSelect={selectSuggestion}
          />
          <select
            value={filters.status}
            onChange={(e) => applyStatus(e.target.value)}
            disabled={loading}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-50"
          >
            <option value="">All statuses</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {err && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="w-full min-w-[1040px] text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className={ORDER_TABLE_COL.id}>ID</th>
              <th className={ORDER_TABLE_COL.orderNo}>Order No</th>
              <th className={ORDER_TABLE_COL.date}>Date</th>
              <th className={ORDER_TABLE_COL.oem}>OEM Bill</th>
              <th className={ORDER_TABLE_COL.status}>Status</th>
              <th className={ORDER_TABLE_COL.vendor}>Vendor Name</th>
              <th className={ORDER_TABLE_COL.courier}>Courier</th>
              <th className={ORDER_TABLE_COL.customer}>Customer</th>
              <th className={ORDER_TABLE_COL.city}>City</th>
              <th className={ORDER_TABLE_COL.exp}>Exp. Delivery</th>
              <th className={ORDER_TABLE_COL.actions}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={11} className="px-3 py-6 text-center">
                  <SpinnerLabel label="Loading orders..." />
                </td>
              </tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={11} className="px-3 py-6 text-center text-slate-500">No orders found.</td>
              </tr>
            )}
            {!loading && data.items.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50">
                {(() => {
                  const orderDocumentUrl = buildFileUrl(o.order_file_path);
                  return (
                    <>
                <td className={`${ORDER_TABLE_COL.id} font-medium text-slate-700`}>{o.id}</td>
                <td className={ORDER_TABLE_COL.orderNo}>
                  <span className="font-mono text-xs font-bold text-slate-800">{o.order_no || "-"}</span>
                </td>
                <td className={`${ORDER_TABLE_COL.date} text-slate-600`}>{fmtDate(o.order_date)}</td>
                <td className={`${ORDER_TABLE_COL.oem} text-slate-600`} title={o.oem_bill_no || ""}>{o.oem_bill_no || "-"}</td>
                <td className={ORDER_TABLE_COL.status}><StatusBadge value={o.status} /></td>
                <td className={`${ORDER_TABLE_COL.vendor} text-slate-600`} title={o.vendor_name || ""}>{o.vendor_name || "-"}</td>
                <td className={`${ORDER_TABLE_COL.courier} text-slate-600`} title={o.courier_name || ""}>{o.courier_name || "-"}</td>
                <td className={`${ORDER_TABLE_COL.customer} text-slate-600`} title={o.customer_name || ""}>{o.customer_name || "-"}</td>
                <td className={`${ORDER_TABLE_COL.city} text-slate-600`} title={o.customer_city || ""}>{o.customer_city || "-"}</td>
                <td className={`${ORDER_TABLE_COL.exp} text-slate-600`}>{fmtDate(o.expected_delivery_date)}</td>
                <td className={ORDER_TABLE_COL.actions}>
                  <div className="flex flex-nowrap items-center justify-end gap-1">
                    {orderDocumentUrl && (
                      <>
                        <a
                          title="View document"
                          href={orderDocumentUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="whitespace-nowrap rounded px-1 py-0.5 text-xs text-sky-700 hover:bg-sky-50"
                        >
                          View Doc
                        </a>
                        <a
                          title="Download document"
                          href={orderDocumentUrl}
                          download={fileNameFromPath(o.order_file_path)}
                          className="whitespace-nowrap rounded px-1 py-0.5 text-xs text-emerald-700 hover:bg-emerald-50"
                        >
                          Download
                        </a>
                      </>
                    )}
                    <button
                      title="View"
                      onClick={() => navigate(`/orders/${o.id}`)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >
                      <ViewIcon />
                    </button>
                    {canEditOrders && (
                      <button
                        title="Edit"
                        onClick={() => navigate(`/orders/${o.id}`)}
                        className="rounded p-1 text-slate-600 hover:bg-slate-100"
                      >
                        <EditIcon />
                      </button>
                    )}
                    {canDeleteOrders && (
                      <button
                        title="Delete"
                        onClick={() => setConfirmDelete(o)}
                        className="rounded p-1 text-rose-600 hover:bg-rose-50"
                      >
                        <DeleteIcon />
                      </button>
                    )}
                  </div>
                </td>
                    </>
                  );
                })()}
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

      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete order?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete order{" "}
            <span className="font-mono font-semibold">{confirmDelete?.order_no}</span>.
            This action cannot be undone from the UI.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
