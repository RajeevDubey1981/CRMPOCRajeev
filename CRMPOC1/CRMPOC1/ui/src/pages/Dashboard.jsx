import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import Modal from "../components/Modal.jsx";
import Pagination from "../components/Pagination.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ComplaintQuickViewModal from "../components/complaints/ComplaintQuickViewModal.jsx";
import LinkedRequestCell from "../components/complaints/LinkedRequestCell.jsx";
import { api } from "../api/client.js";
import { complaintsApi } from "../api/complaints.js";
import { partnerRegistrationsApi } from "../api/partnerRegistrations.js";
import { servicesApi } from "../api/services.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../utils/roles.js";
import ComplaintEdit from "./complaints/ComplaintEdit.jsx";
import { getComplaintOpenPath } from "../utils/complaintLinks.js";
import {
  getComplaintWorkflowAction,
  getComplaintWorkflowStatus,
  WORKFLOW_ACTION_STYLE,
} from "../utils/complaintWorkflowAction.js";

/* ─── constants ─────────────────────────────────────────────────── */

const STAT_CARDS = [
  { key: "pending",       label: "Pending",       bg: "bg-amber-400",   statusFilter: "Pending"       },
  { key: "resolved",      label: "Resolved",      bg: "bg-emerald-600", statusFilter: "Resolved"      },
  { key: "under_process", label: "Under Process", bg: "bg-sky-400",     statusFilter: "Under Process" },
  { key: "rejected",      label: "Rejected",      bg: "bg-rose-600",    statusFilter: "Rejected"      },
  { key: "in_process",    label: "In Process",    bg: "bg-slate-500",   statusFilter: "In Process"    },
];

const CHART_FILL = {
  Pending: "#fbbf24", Resolved: "#059669",
  "Under Process": "#38bdf8", Rejected: "#f43f5e", "In Process": "#64748b",
};

const QUICK_LINKS = [
  { to: "/complaints",       label: "📋 Complaints",    bg: "bg-amber-400 hover:bg-amber-500"     },
  { to: "/services",         label: "🛠 Service Requests", bg: "bg-cyan-600 hover:bg-cyan-700"    },
  { to: "/installations",    label: "🔧 Installations", bg: "bg-sky-400 hover:bg-sky-500"         },
  { to: "/vendor-dashboard", label: "📦 Vendor Orders", bg: "bg-emerald-600 hover:bg-emerald-700" },
  { to: "/orders",           label: "🗒 Order List",   bg: "bg-blue-500 hover:bg-blue-600"       },
  { to: "/claims",           label: "📄 Claims",        bg: "bg-purple-500 hover:bg-purple-600"   },
];

const STATUSES   = ["Pending", "Under Process", "In Process", "Resolved", "Rejected"];
const QUERY_TYPES = ["Service", "Installation", "Sales", "Others"];
const SERVICE_TYPES = ["Free Service", "Warranty Service", "Paid Service"];
const SOURCES    = [{ value: "callcenter", label: "callcenter" }, { value: "public", label: "Public User" }];
const EMPTY_PARTNER_INVITE = {
  partner_type: "Gem Partner",
  email: "",
  contact_person_name: "",
  mobile: "",
  name: "",
};

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  catch { return s; }
}
function trunc(s, n = 26) {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

const SERVICE_SUMMARY_TONES = [
  ["assigned", "Assigned", "bg-sky-500"],
  ["in_progress", "In Progress", "bg-cyan-600"],
  ["pending_approval", "Pending Approval", "bg-orange-500"],
  ["payment_pending", "Payment Pending", "bg-amber-500"],
  ["completed", "Completed", "bg-emerald-600"],
  ["closed", "Closed", "bg-slate-600"],
];

const ENGINEER_GRID_COLUMNS = [
  { key: "service_request_no", label: "Service Request" },
  { key: "comp_no", label: "Complaint Ref" },
  { key: "customer_name", label: "Customer" },
  { key: "customer_mobile", label: "Mobile" },
  { key: "query_type", label: "Type" },
  { key: "status", label: "Status" },
  { key: "service_type", label: "Service Type" },
  { key: "linked_request", label: "Linked Request" },
];

const GRID_COLUMNS = [
  { key: "id", label: "Id" },
  { key: "comp_no", label: "Ref No" },
  { key: "customer_name", label: "Customer Name" },
  { key: "status", label: "Status" },
  { key: "query_type", label: "Query Type" },
  { key: "linked_request", label: "Linked Request" },
  { key: "workflow_action", label: "Action" },
  { key: "remark", label: "Remark", gridHidden: true },
  { key: "assigned_engineer_name", label: "Assigned Engineer" },
  { key: "customer_mobile", label: "Mobile" },
  { key: "model_details", label: "Model Details", gridHidden: true },
  { key: "problem_description", label: "Problem Description", gridHidden: true },
  { key: "status_date", label: "Status Date", gridHidden: true },
  { key: "customer_email", label: "Email" },
  { key: "customer_address", label: "Customer Address", gridHidden: true },
  { key: "created_by_name", label: "Created By", gridHidden: true },
  { key: "created_at", label: "Created At", gridHidden: true },
  { key: "row_actions", label: "" },
];

const GRID_COLUMN_CELL_CLASS = {
  status: "min-w-[11rem] whitespace-nowrap align-middle",
  workflow_action: "min-w-[10.5rem] whitespace-nowrap align-middle",
};

/* ─── component ─────────────────────────────────────────────────── */

export default function Dashboard() {
  const navigate = useNavigate();
  const dashboardRef = useRef(null);
  const { user } = useAuth();
  const rawRole = user?.role || "";
  const role = rawRole.toString().trim().toLowerCase();
  const isCallcenter = role === "callcenter";
  const isEngineer = role === "engineer";
  const isSales = role === "sales";
  // Only operations/admin-like roles can delete complaints from dashboard
  const isAdminLike = isOperationsAdminRole(role) && !isSales;

  // summary / chart
  const [summary, setSummary]   = useState(null);
  const [installs, setInstalls] = useState(null);
  const [dashErr, setDashErr]   = useState("");

  // grid
  const [complaints, setComplaints] = useState({ items: [], total: 0 });
  const [loading, setLoading]       = useState(false);
  const [gridErr, setGridErr]       = useState("");
  const [filters, setFilters]       = useState({
    id: "", comp_no: "", customer_name: "", status: "",
    query_type: "", service_type: "", mobile: "", source: "", date_from: "", date_to: "",
  });
  const [page, setPage]     = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [viewTarget, setViewTarget] = useState(null);
  const [editTarget, setEditTarget] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [dashboardPanelOpen, setDashboardPanelOpen] = useState(true);
  const [serviceSummary, setServiceSummary] = useState(null);
  const [serviceRequests, setServiceRequests] = useState({ items: [], total: 0 });
  const [serviceErr, setServiceErr] = useState("");
  const [partnerInviteOpen, setPartnerInviteOpen] = useState(false);
  const [partnerInviteMeta, setPartnerInviteMeta] = useState({ partner_types: [] });
  const [partnerInviteForm, setPartnerInviteForm] = useState(EMPTY_PARTNER_INVITE);
  const [partnerInviteSaving, setPartnerInviteSaving] = useState(false);
  const [partnerInviteResult, setPartnerInviteResult] = useState(null);
  const [partnerInviteError, setPartnerInviteError] = useState("");

  const visibleColumns = useMemo(() => (
    isEngineer
      ? ENGINEER_GRID_COLUMNS
      : GRID_COLUMNS.filter((col) => !col.gridHidden && col.key !== "workflow_status")
  ), [isEngineer]);

  const serviceById = useMemo(() => {
    const map = new Map();
    serviceRequests.items.forEach((row) => map.set(row.id, row));
    return map;
  }, [serviceRequests.items]);

  const engineerGridRows = useMemo(() => {
    if (!isEngineer) return [];
    const linkedServiceIds = new Set();
    const rows = complaints.items.map((complaint) => {
      const service = complaint.service_request_id
        ? serviceById.get(complaint.service_request_id)
        : null;
      if (complaint.service_request_id) linkedServiceIds.add(complaint.service_request_id);
      return { key: `complaint-${complaint.id}`, complaint, service };
    });
    serviceRequests.items.forEach((service) => {
      if (linkedServiceIds.has(service.id)) return;
      rows.push({ key: `service-${service.id}`, complaint: null, service });
    });
    if (filters.service_type) {
      return rows.filter((row) => row.service?.service_type === filters.service_type);
    }
    return rows;
  }, [isEngineer, complaints.items, serviceRequests.items, serviceById, filters.service_type]);

  useEffect(() => {
    if (!isEngineer) return;
    setServiceErr("");
    Promise.all([
      api.get("/api/dashboard/services-summary"),
      servicesApi.list({
        page: 1,
        per_page: 100,
        service_type: filters.service_type || undefined,
      }),
    ])
      .then(([summaryRes, listRes]) => {
        setServiceSummary(summaryRes.data);
        setServiceRequests(listRes);
      })
      .catch((e) => setServiceErr(e.response?.data?.detail || "Failed to load service requests"));
  }, [isEngineer, filters.service_type]);

  useEffect(() => {
    if (!isSales) return;
    partnerRegistrationsApi.meta()
      .then(setPartnerInviteMeta)
      .catch(() => setPartnerInviteMeta({
        partner_types: ["Gem Partner", "CSD Dealer", "Distributor", "Service Partner", "Retailer", "Partner"],
      }));
  }, [isSales]);

  useEffect(() => {
    function closeQuickLinksOnScroll() {
      const scrollContainer = dashboardRef.current?.closest("main");
      if (scrollContainer && scrollContainer.scrollTop >= scrollContainer.clientHeight / 2) {
        setDashboardPanelOpen(false);
      }
    }

    const scrollContainer = dashboardRef.current?.closest("main");
    if (!scrollContainer) return undefined;
    closeQuickLinksOnScroll();
    scrollContainer.addEventListener("scroll", closeQuickLinksOnScroll, { passive: true });
    return () => scrollContainer.removeEventListener("scroll", closeQuickLinksOnScroll);
  }, []);

  /* load summary cards */
  useEffect(() => {
    Promise.all([
      api.get("/api/dashboard/complaints-summary"),
      api.get("/api/dashboard/installation-summary"),
    ])
      .then(([s, i]) => { setSummary(s.data); setInstalls(i.data); })
      .catch((e) => setDashErr(e.response?.data?.detail || "Failed to load summary"));
  }, []);

  /* load complaint grid */
  const params = useMemo(() => {
    const search = [filters.customer_name, filters.mobile].filter(Boolean).join(" ");
    return {
      page, per_page: perPage,
      id:       filters.id ? parseInt(filters.id, 10) : undefined,
      comp_no:  filters.comp_no  || undefined,
      search:   search           || undefined,
      status:   filters.status   || undefined,
      query_type: filters.query_type || undefined,
      source:   filters.source   || undefined,
      date_from:filters.date_from || undefined,
      date_to:  filters.date_to  || undefined,
    };
  }, [page, perPage, filters]);

  async function loadGrid() {
    setLoading(true); setGridErr("");
    try { setComplaints(await complaintsApi.list(params)); }
    catch (e) { setGridErr(e.response?.data?.detail || "Failed to load complaints"); }
    finally { setLoading(false); }
  }
  useEffect(() => { loadGrid(); /* eslint-disable-next-line */ }, [params]);

  function patch(k, v) { setFilters(f => ({ ...f, [k]: v })); setPage(1); }
  function resetFilters() {
    setFilters({ id: "", comp_no: "", customer_name: "", status: "", query_type: "", service_type: "", mobile: "", source: "", date_from: "", date_to: "" });
    setPage(1);
  }

  async function rejectComplaint(complaint) {
    if (!window.confirm(`Reject complaint ${complaint.comp_no}?`)) return;
    try {
      const fd = new FormData();
      fd.append("new_status", "Rejected");
      fd.append("remark", "Rejected by admin");
      await complaintsApi.updateStatus(complaint.id, fd);
      setViewTarget(null);
      loadGrid();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to reject complaint");
    }
  }

  async function deleteComplaint() {
    if (!confirmDelete) return;
    try {
      await complaintsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      setViewTarget(null);
      loadGrid();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete complaint");
    }
  }

  async function sendPartnerInvite(event) {
    event.preventDefault();
    setPartnerInviteSaving(true);
    setPartnerInviteError("");
    setPartnerInviteResult(null);
    try {
      const result = await partnerRegistrationsApi.invite({
        partner_type: partnerInviteForm.partner_type,
        email: partnerInviteForm.email,
        contact_person_name: partnerInviteForm.contact_person_name || null,
        mobile: partnerInviteForm.mobile || null,
        name: partnerInviteForm.name || null,
      });
      setPartnerInviteResult(result);
      setPartnerInviteForm(EMPTY_PARTNER_INVITE);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setPartnerInviteError(Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : detail || "Failed to send onboarding invite");
    } finally {
      setPartnerInviteSaving(false);
    }
  }

  /* stat-card click → pre-filter grid */
  function clickCard(statusFilter) {
    setFilters(f => ({ ...f, status: f.status === statusFilter ? "" : statusFilter }));
    setPage(1);
  }

  async function handleWorkflowAction(complaint) {
    const workflowAction = getComplaintWorkflowAction(complaint);
    const queryType = (complaint.query_type || "").toLowerCase();

    if (workflowAction === "Ask for Invoice" && !isCallcenter) {
      try {
        if (queryType === "installation") {
          await complaintsApi.requestInstallationUploadLink(complaint.id);
          loadGrid();
          return;
        }
        if (queryType === "service") {
          await complaintsApi.requestCustomerUploadLink(complaint.id);
          loadGrid();
          return;
        }
      } catch (e) {
        alert(e.response?.data?.detail || "Failed to request customer documents");
        return;
      }
    }

    navigate(getComplaintOpenPath(complaint, { preferInstallationWorkflow: !isCallcenter }));
  }

  /* chart data */
  const chartData = summary
    ? STAT_CARDS.map(c => ({ name: c.label, value: summary[c.key] ?? 0, fill: CHART_FILL[c.label] ?? "#94a3b8" }))
    : [];
  const total = summary ? Object.values(summary).reduce((s, v) => s + (v ?? 0), 0) : 0;

  function rowOpenPath(row) {
    if (row.service?.id) return `/services/${row.service.id}`;
    if (row.complaint) return getComplaintOpenPath(row.complaint, { preferInstallationWorkflow: true });
    return "/dashboard";
  }

  function renderEngineerCell(column, row) {
    const { complaint, service } = row;
    const statusValue = service?.status
      || (complaint ? (getComplaintWorkflowStatus(complaint) || complaint.status) : "—");

    switch (column.key) {
      case "service_request_no":
        return service?.request_no || complaint?.service_request_no
          ? (
            <span className="font-mono text-brand-700">
              {service?.request_no || complaint?.service_request_no}
            </span>
          )
          : "—";
      case "comp_no":
        return complaint?.comp_no
          ? (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setViewTarget(complaint); }}
              className="font-mono text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700"
            >
              {complaint.comp_no}
            </button>
          )
          : "—";
      case "customer_name":
        return complaint?.customer_name || service?.customer_name || "—";
      case "customer_mobile":
        return complaint?.customer_mobile || service?.customer_mobile || "—";
      case "query_type":
        return complaint?.query_type || (service ? "Service" : "—");
      case "status":
        return <StatusBadge value={statusValue} />;
      case "service_type":
        return service?.service_type || "—";
      case "linked_request":
        return complaint
          ? <LinkedRequestCell complaint={complaint} plainInstallationLink={isCallcenter} />
          : "—";
      default:
        return "—";
    }
  }

  function renderCell(column, c) {
    const workflowAction = getComplaintWorkflowAction(c);
    switch (column.key) {
      case "id":
        return <span className="font-medium text-slate-700">{c.id}</span>;
      case "comp_no":
        return (
          <button
            type="button"
            onClick={() => setViewTarget(c)}
            className="font-mono text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700"
          >
            {c.comp_no}
          </button>
        );
      case "customer_name":
        return <span className="max-w-[110px] truncate" title={c.customer_name}>{c.customer_name || "—"}</span>;
      case "status":
        return <StatusBadge value={getComplaintWorkflowStatus(c) || c.status} />;
      case "query_type":
        return c.query_type || "—";
      case "linked_request":
        return <LinkedRequestCell complaint={c} plainInstallationLink={isCallcenter} />;
      case "workflow_action":
        return (
          <button
            type="button"
            onClick={() => handleWorkflowAction(c)}
            className={`inline-block whitespace-nowrap rounded border px-2.5 py-1 text-xs font-medium leading-snug hover:opacity-80 ${WORKFLOW_ACTION_STYLE[workflowAction] || "bg-slate-100 text-slate-600 border-slate-200"}`}
          >
            {workflowAction}
          </button>
        );
      case "remark":
        return <span className="max-w-[120px] truncate" title={c.remark || ""}>{trunc(c.remark)}</span>;
      case "assigned_engineer_name":
        return <span className="whitespace-nowrap">{c.assigned_engineer_name || "—"}</span>;
      case "customer_mobile":
        return c.customer_mobile || "—";
      case "model_details":
        return <span className="max-w-[100px] truncate" title={c.model_details || ""}>{trunc(c.model_details, 20)}</span>;
      case "problem_description":
        return <span className="max-w-[120px] truncate" title={c.problem_description || ""}>{trunc(c.problem_description)}</span>;
      case "status_date":
        return <span className="whitespace-nowrap">{fmtDate(c.status_date)}</span>;
      case "customer_email":
        return <span className="max-w-[120px] truncate" title={c.customer_email || ""}>{c.customer_email || "—"}</span>;
      case "customer_address":
        return <span className="max-w-[120px] truncate" title={c.customer_address || ""}>{trunc(c.customer_address)}</span>;
      case "created_by_name":
        return c.created_by_name || "—";
      case "created_at":
        return <span className="whitespace-nowrap">{fmtDate(c.created_at)}</span>;
      case "row_actions":
        return (
          <div className="flex items-center gap-1 whitespace-nowrap">
            <button title="View" onClick={() => setViewTarget(c)}
              className="rounded p-1 text-slate-500 hover:text-brand-600">👁</button>
            {isAdminLike && (
              <>
                <button title="Edit" onClick={() => setEditTarget(c)}
                  className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-50">Edit</button>
                <button title="Delete" onClick={() => setConfirmDelete(c)}
                  className="rounded border border-rose-300 px-2 py-0.5 text-xs text-rose-700 hover:bg-rose-50">Delete</button>
              </>
            )}
          </div>
        );
      default:
        return "—";
    }
  }

  /* ── render ── */
  return (
    <div ref={dashboardRef} className="space-y-5">

      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <button
          type="button"
          onClick={() => setDashboardPanelOpen((open) => !open)}
          aria-expanded={dashboardPanelOpen}
          className="flex items-center gap-2 text-left text-xl font-semibold text-slate-800"
        >
          <span>{dashboardPanelOpen ? "▾" : "▸"}</span>
          <span>
            {isEngineer ? "My Dashboard" : "Complaint Dashboard"}
            <span className="ml-2 text-sm font-normal text-slate-400">Overview</span>
          </span>
        </button>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="text-brand-600">🏠</span>
          <span>/</span>
          <span>Dashboard</span>
        </nav>
      </div>

      {dashboardPanelOpen && (
        <>
          {(dashErr || serviceErr) && (
            <div className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {dashErr || serviceErr}
            </div>
          )}

          {isEngineer && serviceSummary && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              {SERVICE_SUMMARY_TONES.map(([key, label, tone]) => (
                <div key={key} className={`rounded-lg p-3 text-white shadow-sm ${tone}`}>
                  <div className="text-xs font-medium opacity-90">{label}</div>
                  <div className="mt-1 text-2xl font-semibold">{serviceSummary[key] ?? 0}</div>
                </div>
              ))}
            </div>
          )}

          {!isEngineer && (
          <div className="flex flex-wrap gap-3">
            {STAT_CARDS.map(card => (
              <div
                key={card.key}
                onClick={() => clickCard(card.statusFilter)}
                className={`flex-1 min-w-[130px] cursor-pointer overflow-hidden rounded shadow transition-transform hover:-translate-y-0.5 hover:shadow-md ${card.bg} ${filters.status === card.statusFilter ? "ring-2 ring-offset-1 ring-white/50" : ""}`}
              >
                <div className="bg-black/10 px-3 py-2 text-xs font-semibold text-white/90">{card.label}</div>
                <div className="px-3 py-3">
                  <p className="text-2xl font-bold text-white">{summary?.[card.key] ?? "—"}</p>
                  <p className="mt-0.5 text-xs text-white/70">Complaints</p>
                </div>
              </div>
            ))}
          </div>
          )}

           {/* Quick Links */}
           {!isEngineer && (
          <div className="rounded bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-600">Quick Links</h3>
            <div className="mt-3 flex flex-wrap gap-2">
               {isSales && (
                <button
                  type="button"
                  onClick={() => {
                    setPartnerInviteOpen(true);
                    setPartnerInviteResult(null);
                    setPartnerInviteError("");
                  }}
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                >
                  Send onboarding invite
                 </button>
               )}
              {QUICK_LINKS.map(ql => (
                <Link key={ql.to} to={ql.to}
                  className={`rounded px-4 py-2 text-sm font-medium text-white transition-colors ${ql.bg}`}>
                  {ql.label}
                </Link>
              ))}
            </div>
          </div>
          )}

          {/* Filter */}
          <div className="rounded bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-600">Filter</h3>
          {!isEngineer && (
            <Link to="/complaints/new"
              className="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
              + New Complaint
            </Link>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {/* ID */}
          <Field label="ID"><input type="text" value={filters.id} onChange={e => patch("id", e.target.value)} placeholder="ID" /></Field>
          {/* Ref No */}
          <Field label="Service Request Number"><input type="text" value={filters.comp_no} onChange={e => patch("comp_no", e.target.value)} placeholder="Ref No" /></Field>
          {/* Customer Name */}
          <Field label="Customer Name"><input type="text" value={filters.customer_name} onChange={e => patch("customer_name", e.target.value)} placeholder="Customer Name" /></Field>
          {/* Status */}
          <Field label="Select Status">
            <select value={filters.status} onChange={e => patch("status", e.target.value)}>
              <option value="">-- Select --</option>
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          {/* Query Type */}
          <Field label="Query Type">
            <select value={filters.query_type} onChange={e => patch("query_type", e.target.value)}>
              <option value="">-- Select --</option>
              {QUERY_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          {isEngineer && (
            <Field label="Service Type">
              <select value={filters.service_type} onChange={e => patch("service_type", e.target.value)}>
                <option value="">-- Select --</option>
                {SERVICE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
          )}
          {/* Mobile */}
          <Field label="Customer Mobile Number"><input type="text" value={filters.mobile} onChange={e => patch("mobile", e.target.value)} placeholder="Mobile" /></Field>
          {/* Source */}
          <Field label="Select Created By">
            <select value={filters.source} onChange={e => patch("source", e.target.value)}>
              <option value="">-- Select --</option>
              {SOURCES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </Field>
          {/* Date from */}
          <Field label="Created Date (From)"><input type="date" value={filters.date_from} onChange={e => patch("date_from", e.target.value)} /></Field>
          {/* Date to */}
          <Field label="Created Date (To)"><input type="date" value={filters.date_to} onChange={e => patch("date_to", e.target.value)} /></Field>
        </div>
        <div className="mt-3 flex gap-2">
          <button onClick={loadGrid}
            className="inline-flex items-center gap-1.5 rounded bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
            🔍 Search
          </button>
          <button onClick={resetFilters}
            className="inline-flex items-center gap-1.5 rounded border border-slate-300 bg-white px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
            ↺ Reset
          </button>
        </div>
          </div>
        </>
      )}

      {gridErr && <div className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{gridErr}</div>}

      {/* Complaint Grid */}
      <div className="overflow-x-auto rounded bg-white shadow-sm">
        <table className="w-full min-w-[1280px] text-xs">
          <thead className="border-b-2 border-slate-200 bg-slate-50">
            <tr>
              {visibleColumns.map((column) => (
                <th
                  key={column.key}
                  className={`whitespace-nowrap px-3 py-2.5 text-left font-semibold text-slate-600 ${GRID_COLUMN_CELL_CLASS[column.key] || ""}`}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={visibleColumns.length} className="py-10 text-center text-slate-400">Loading…</td></tr>
            )}
            {!loading && isEngineer && engineerGridRows.length === 0 && (
              <tr><td colSpan={visibleColumns.length} className="py-10 text-center text-slate-400">No assigned work found.</td></tr>
            )}
            {!loading && isEngineer && engineerGridRows.map((row) => (
              <tr
                key={row.key}
                onClick={() => navigate(rowOpenPath(row))}
                className="cursor-pointer transition-colors hover:bg-sky-50/40"
              >
                {visibleColumns.map((column) => (
                  <td key={column.key} className={`px-3 py-2 ${GRID_COLUMN_CELL_CLASS[column.key] || ""}`}>
                    {renderEngineerCell(column, row)}
                  </td>
                ))}
              </tr>
            ))}
            {!loading && !isEngineer && complaints.items.length === 0 && (
              <tr><td colSpan={visibleColumns.length} className="py-10 text-center text-slate-400">No complaints found.</td></tr>
            )}
            {!loading && !isEngineer && complaints.items.map((c) => (
              <tr key={c.id} className="transition-colors hover:bg-sky-50/40">
                {visibleColumns.map((column) => (
                  <td key={column.key} className={`px-3 py-2 ${GRID_COLUMN_CELL_CLASS[column.key] || ""}`}>
                    {renderCell(column, c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page} perPage={perPage} total={complaints.total}
        onPageChange={setPage}
        onPerPageChange={n => { setPerPage(n); setPage(1); }}
      />

      {/* Installation Pending */}
      <div className="rounded bg-white p-5 shadow-sm">
        <h3 className="mb-4 border-b border-slate-100 pb-2 text-base font-semibold text-slate-700">
          Installation Pending
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Total pending", val: installs?.total_pending, color: "text-slate-700",  bg: "bg-slate-50"  },
            { label: "> 7 days",      val: installs?.gt7days,       color: "text-amber-600",  bg: "bg-amber-50"  },
            { label: "> 15 days",     val: installs?.gt15days,      color: "text-orange-600", bg: "bg-orange-50" },
            { label: "> 30 days",     val: installs?.gt30days,      color: "text-rose-600",   bg: "bg-rose-50"   },
          ].map(({ label, val, color, bg }) => (
            <div key={label} className={`rounded p-3 ${bg}`}>
              <p className="text-xs text-slate-500">{label}</p>
              <p className={`mt-1 text-2xl font-bold ${color}`}>{val ?? "—"}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Complaint Status Chart */}
      {!isEngineer && (
      <div className="rounded bg-white p-5 shadow-sm">
        <h3 className="mb-4 border-b border-slate-100 pb-2 text-base font-semibold text-slate-700">
          Complaint Status Chart
          {total > 0 && <span className="ml-2 text-sm font-normal text-slate-400">— {total.toLocaleString()} total</span>}
        </h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip formatter={val => [val.toLocaleString(), "Complaints"]} labelStyle={{ fontWeight: 600 }} />
              <Bar dataKey="value" name="Complaints" radius={[3, 3, 0, 0]} maxBarSize={64}>
                {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      )}

      <ComplaintQuickViewModal
        complaint={viewTarget}
        open={!!viewTarget}
        onClose={() => setViewTarget(null)}
        isAdminLike={isAdminLike}
        isCallcenter={isCallcenter}
        onEdit={(c) => { setEditTarget(c); setViewTarget(null); }}
        onDelete={(c) => { setConfirmDelete(c); setViewTarget(null); }}
        onReject={rejectComplaint}
      />

      {editTarget && (
        <ComplaintEdit
          complaint={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => { setEditTarget(null); loadGrid(); }}
        />
      )}

      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete complaint?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete complaint <span className="font-mono">{confirmDelete?.comp_no}</span>.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setConfirmDelete(null)} className="rounded border border-slate-300 px-3 py-2 text-sm">Cancel</button>
            <button onClick={deleteComplaint} className="rounded bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700">Delete</button>
          </div>
        </div>
      </Modal>

      <Modal
        open={partnerInviteOpen}
        onClose={() => setPartnerInviteOpen(false)}
        title="Send onboarding invite"
        maxWidth="max-w-lg"
      >
        <form onSubmit={sendPartnerInvite} className="space-y-4">
          {partnerInviteResult && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              Invite sent to {partnerInviteResult.email}. Registration no: {partnerInviteResult.registration_no}
            </div>
          )}
          {partnerInviteError && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {partnerInviteError}
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Partner type</label>
            <select
              value={partnerInviteForm.partner_type}
              onChange={(event) => setPartnerInviteForm((form) => ({ ...form, partner_type: event.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {(partnerInviteMeta.partner_types.length ? partnerInviteMeta.partner_types : ["Gem Partner"]).map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Partner email *</label>
            <input
              type="email"
              required
              value={partnerInviteForm.email}
              onChange={(event) => setPartnerInviteForm((form) => ({ ...form, email: event.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Firm name</label>
            <input
              value={partnerInviteForm.name}
              onChange={(event) => setPartnerInviteForm((form) => ({ ...form, name: event.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Contact person</label>
              <input
                value={partnerInviteForm.contact_person_name}
                onChange={(event) => setPartnerInviteForm((form) => ({ ...form, contact_person_name: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Mobile *</label>
              <input
                type="tel"
                required
                minLength={10}
                maxLength={20}
                value={partnerInviteForm.mobile}
                onChange={(event) => setPartnerInviteForm((form) => ({ ...form, mobile: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setPartnerInviteOpen(false)} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button type="submit" disabled={partnerInviteSaving} className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {partnerInviteSaving ? "Sending..." : "Send onboarding invite"}
            </button>
          </div>
        </form>
      </Modal>

    </div>
  );
}

/* tiny helper to keep filter fields DRY */
function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</label>
      <div className="[&_input]:w-full [&_input]:rounded [&_input]:border [&_input]:border-slate-300 [&_input]:px-2.5 [&_input]:py-1.5 [&_input]:text-sm [&_input]:text-slate-700 [&_select]:w-full [&_select]:rounded [&_select]:border [&_select]:border-slate-300 [&_select]:px-2.5 [&_select]:py-1.5 [&_select]:text-sm [&_select]:text-slate-700">
        {children}
      </div>
    </div>
  );
}
