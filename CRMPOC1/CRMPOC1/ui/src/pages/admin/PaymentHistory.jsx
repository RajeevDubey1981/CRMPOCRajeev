import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { installationsApi } from "../../api/installations.js";

function fmtDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return value;
  }
}

function fmtAmount(value) {
  if (value == null) return "-";
  return Number(value).toFixed(2);
}

export default function PaymentHistory() {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0 });
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [engineerSearch, setEngineerSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    search: search || undefined,
    engineer: engineerSearch || undefined,
  }), [page, perPage, search, engineerSearch]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setErr("");
      try {
        setData(await installationsApi.paymentHistory(params));
      } catch (e) {
        setErr(e.response?.data?.detail || "Failed to load payment history");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params]);

  function toggleExpanded(id) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Payment History</h1>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <input
          type="text"
          placeholder="Search customer / serial / product"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Filter by engineer name"
          value={engineerSearch}
          onChange={(e) => {
            setEngineerSearch(e.target.value);
            setPage(1);
          }}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="w-12 px-3 py-2"></th>
              <th className="px-3 py-2">Payment Batch</th>
              <th className="px-3 py-2">Engineer</th>
              <th className="px-3 py-2">Requests</th>
              <th className="px-3 py-2">Total Amount Paid</th>
              <th className="px-3 py-2">Payment Type</th>
              <th className="px-3 py-2">Paid On</th>
              <th className="px-3 py-2">Recorded By</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">No payment history found.</td></tr>
            )}
            {!loading && data.items.map((row) => {
              const expanded = expandedIds.has(row.id);
              return (
                <Fragment key={row.id}>
                  <tr className="cursor-pointer hover:bg-slate-50" onClick={() => toggleExpanded(row.id)}>
                    <td className="px-3 py-2 text-center text-slate-500">{expanded ? "-" : "+"}</td>
                    <td className="px-3 py-2 font-medium text-slate-700">PAY-{row.id}</td>
                    <td className="px-3 py-2">{row.engineer_name || "-"}</td>
                    <td className="px-3 py-2">{row.request_count}</td>
                    <td className="px-3 py-2 font-semibold text-emerald-700">{fmtAmount(row.total_amount)}</td>
                    <td className="px-3 py-2">{row.payment_type}</td>
                    <td className="px-3 py-2 text-xs">{fmtDate(row.recorded_at)}</td>
                    <td className="px-3 py-2">{row.recorded_by_name || "-"}</td>
                  </tr>
                  {expanded && (
                    <tr className="bg-slate-50/70">
                      <td colSpan={8} className="px-3 py-3">
                        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
                          <table className="min-w-full text-sm">
                            <thead className="bg-slate-100 text-left text-slate-700">
                              <tr>
                                <th className="px-3 py-2">Type</th>
                                <th className="px-3 py-2">Request</th>
                                <th className="px-3 py-2">Order No</th>
                                <th className="px-3 py-2">Item Code</th>
                                <th className="px-3 py-2">Customer</th>
                                <th className="px-3 py-2">Date</th>
                                <th className="px-3 py-2">Requested</th>
                                <th className="px-3 py-2">Paid</th>
                                <th className="px-3 py-2">Status</th>
                                <th className="px-3 py-2 text-right">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {row.requests.map((request) => (
                                <tr key={`${request.source_type || "installation"}-${request.id}`} className="hover:bg-slate-50">
                                  <td className="px-3 py-2 capitalize">{request.source_type || "installation"}</td>
                                  <td className="px-3 py-2 font-medium text-slate-700">{request.id}</td>
                                  <td className="px-3 py-2 font-mono text-xs">{request.order_no || "-"}</td>
                                  <td className="px-3 py-2 font-mono text-xs">{request.item_code || "-"}</td>
                                  <td className="px-3 py-2">{request.customer_name}</td>
                                  <td className="px-3 py-2 text-xs">{fmtDate(request.installation_date)}</td>
                                  <td className="px-3 py-2">{fmtAmount(request.requested_amount)}</td>
                                  <td className="px-3 py-2">{fmtAmount(request.paid_amount)}</td>
                                  <td className="px-3 py-2"><StatusBadge value={request.status} /></td>
                                  <td className="px-3 py-2 text-right">
                                    <button
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        navigate(request.source_type === "service" ? `/services/${request.id}` : `/installations/${request.id}`);
                                      }}
                                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                                    >
                                      View
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(next) => {
          setPerPage(next);
          setPage(1);
        }}
      />
    </div>
  );
}
