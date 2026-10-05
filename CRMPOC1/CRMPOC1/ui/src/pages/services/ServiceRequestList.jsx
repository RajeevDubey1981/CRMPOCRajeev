import { useEffect, useMemo, useState } from "react";
import { BounceBadge } from "../../components/EmailBounceNotice.jsx";
import { Link, useNavigate } from "react-router-dom";

import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { servicesApi } from "../../api/services.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { canViewAllServiceRequests } from "../../utils/roles.js";

const SUMMARY_TONES = [
  ["new_requests", "New", "bg-amber-500"],
  ["unassigned", "Unassigned", "bg-rose-500"],
  ["assigned", "Assigned", "bg-sky-500"],
  ["pending_approval", "Pending Approval", "bg-orange-500"],
  ["completed", "Completed", "bg-emerald-600"],
  ["closed", "Closed", "bg-slate-600"],
];

export default function ServiceRequestList() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isEngineer = (user?.role || "").toLowerCase() === "engineer";
  const canFilterByServiceUser = canViewAllServiceRequests(user?.role);
  const [summary, setSummary] = useState(null);
  const [data, setData] = useState({ items: [], total: 0 });
  const [serviceUsers, setServiceUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({ search: "", status: "", service_type: "", service_user: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  useEffect(() => {
    servicesApi.summary().then(setSummary).catch(() => null);
  }, []);

  useEffect(() => {
    if (!canFilterByServiceUser) return;
    servicesApi.serviceUsers().then(setServiceUsers).catch(() => setServiceUsers([]));
  }, [canFilterByServiceUser]);

  const params = useMemo(() => {
    const base = {
      page,
      per_page: perPage,
      search: filters.search || undefined,
      status: filters.status || undefined,
      service_type: filters.service_type || undefined,
    };
    if (!canFilterByServiceUser || !filters.service_user) {
      return base;
    }
    if (filters.service_user === "unassigned") {
      return { ...base, service_user_unassigned: true };
    }
    return { ...base, service_user_id: Number(filters.service_user) };
  }, [page, perPage, filters, canFilterByServiceUser]);

  const tableColumnCount = canFilterByServiceUser ? 13 : 12;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setErr("");
    servicesApi.list(params)
      .then((result) => { if (active) setData(result); })
      .catch((error) => { if (active) setErr(error.response?.data?.detail || "Failed to load service requests"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [params]);

  function patch(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Service Requests</h1>
          <p className="text-sm text-slate-500">Complete service lifecycle across call center, service team, engineer, vendor, approval, and payment.</p>
        </div>
        {!isEngineer && (
          <Link to="/services/new" className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">+ New Service Request</Link>
        )}
      </div>

      {summary && (
        <div className="grid grid-cols-3 gap-2 sm:gap-3 xl:grid-cols-6">
          {SUMMARY_TONES.map(([key, label, tone]) => (
            <div key={key} className={`rounded-lg p-2.5 text-white shadow-sm sm:p-4 ${tone}`}>
              <div className="text-xs font-medium opacity-90 sm:text-sm">{label}</div>
              <div className="mt-0.5 text-2xl font-semibold sm:mt-1 sm:text-3xl">{summary[key]}</div>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className={`grid grid-cols-1 gap-3 ${canFilterByServiceUser ? "md:grid-cols-2 xl:grid-cols-4" : "md:grid-cols-3"}`}>
          <input value={filters.search} onChange={(e) => patch("search", e.target.value)} placeholder="Request no / customer / mobile / serial" className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
          <select value={filters.status} onChange={(e) => patch("status", e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            <option value="">All statuses</option>
            {["New","Service Team Review","Admin Review Document","Assigned","Engineer Visit","Serial Verified","Pending Service Approval","Approved for Service","Service In Progress","Service Completed","Payment Requested","Payment Completed","Closed","Rejected","Cancelled"].map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
          <select value={filters.service_type} onChange={(e) => patch("service_type", e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            <option value="">All service types</option>
            <option value="Free Service">Free Service</option>
            <option value="Warranty Service">Warranty Service</option>
            <option value="Paid Service">Paid Service</option>
          </select>
          {canFilterByServiceUser && (
            <select value={filters.service_user} onChange={(e) => patch("service_user", e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">All service users</option>
              <option value="unassigned">Unassigned (no service user)</option>
              {serviceUsers.map((option) => (
                <option key={option.id} value={option.id}>{option.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {/* phones: one card per request, so nothing is hidden off to the right */}
      <div className="space-y-2 md:hidden">
        {loading && <div className="rounded-lg bg-white px-4 py-8 text-center text-sm text-slate-400 shadow-sm">Loading...</div>}
        {!loading && data.items.length === 0 && <div className="rounded-lg bg-white px-4 py-8 text-center text-sm text-slate-400 shadow-sm">No service requests found.</div>}
        {!loading && data.items.map((row) => (
          <div key={row.id} onClick={() => navigate(`/services/${row.id}`)} className="cursor-pointer rounded-lg bg-white p-3 shadow-sm active:bg-sky-50">
            <div className="flex items-start justify-between gap-2">
              <span className="font-mono text-sm font-semibold text-brand-700">{row.request_no}</span>
              <StatusBadge value={row.status} />
            </div>
            <div className="mt-1 text-sm font-medium text-slate-800">{row.customer_name}</div>
            {row.customer_mobile && (
              <a href={`tel:${row.customer_mobile}`} onClick={(e) => e.stopPropagation()} className="text-sm text-brand-600 underline">{row.customer_mobile}</a>
            )}
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              <div><dt className="text-slate-400">Order</dt><dd className="break-words text-slate-700">{row.order_no || "—"}</dd></div>
              <div><dt className="text-slate-400">Serial</dt><dd className="break-words font-mono text-slate-700">{row.serial_no || "—"}</dd></div>
              <div><dt className="text-slate-400">Service type</dt><dd className="text-slate-700">{row.service_type || "—"}</dd></div>
              <div><dt className="text-slate-400">Engineer</dt><dd className="text-slate-700">{row.assigned_engineer_name || "—"}</dd></div>
            </dl>
          </div>
        ))}
        <div className="rounded-lg bg-white px-3 py-3 shadow-sm">
          <Pagination page={page} perPage={perPage} total={data.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </div>
      </div>

      <div className="hidden overflow-hidden rounded-lg bg-white shadow-sm md:block">
        <div className="crm-scroll">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                {[
                  "Request No", "Complaint", "Customer", "Mobile", "Order", "Serial", "Status",
                  ...(canFilterByServiceUser ? ["Service user"] : []),
                  "Service Type", "Warranty", "Engineer", "Vendor", "Documents",
                ].map((heading) => (
                  <th key={heading} className="whitespace-nowrap px-4 py-3 font-semibold">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && <tr><td colSpan={tableColumnCount} className="px-4 py-10 text-center text-slate-400">Loading...</td></tr>}
              {!loading && data.items.length === 0 && <tr><td colSpan={tableColumnCount} className="px-4 py-10 text-center text-slate-400">No service requests found.</td></tr>}
              {!loading && data.items.map((row) => (
                <tr key={row.id} onClick={() => navigate(`/services/${row.id}`)} className="cursor-pointer hover:bg-sky-50/50">
                  <td className="px-4 py-3 font-mono text-brand-700">{row.request_no}</td>
                  <td className="px-4 py-3">
                    {row.complaint_id ? (
                      <Link
                        to={`/complaints/${row.complaint_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="font-mono text-xs text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700"
                      >
                        {row.complaint_no || `#${row.complaint_id}`}
                      </Link>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.customer_name}
                    {row.email_bounced && <div className="mt-1"><BounceBadge reason={row.email_bounce_reason} /></div>}
                  </td>
                  <td className="px-4 py-3">{row.customer_mobile}</td>
                  <td className="px-4 py-3">{row.order_no || "—"}</td>
                  <td className="px-4 py-3">{row.serial_no || "—"}</td>
                  <td className="px-4 py-3"><StatusBadge value={row.status} /></td>
                  {canFilterByServiceUser && (
                    <td className="px-4 py-3 text-slate-700">{row.assigned_service_user_name || "—"}</td>
                  )}
                  <td className="px-4 py-3">{row.service_type || "—"}</td>
                  <td className="px-4 py-3">{row.warranty_status || "—"}</td>
                  <td className="px-4 py-3">{row.assigned_engineer_name || "—"}</td>
                  <td className="px-4 py-3">{row.assigned_vendor_name || "—"}</td>
                  <td className="px-4 py-3">{row.document_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-slate-100 px-4 py-3">
          <Pagination page={page} perPage={perPage} total={data.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </div>
      </div>
    </div>
  );
}
