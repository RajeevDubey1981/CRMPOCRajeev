import { hasPermission } from "../../utils/permissions.js";
import { useEffect, useMemo, useState } from "react";
import PriorityBadge from "../../components/complaints/PriorityBadge.jsx";
import { BOUNCED_BUTTON, BounceBadge } from "../../components/EmailBounceNotice.jsx";
import { Link, useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import ComplaintQuickViewModal from "../../components/complaints/ComplaintQuickViewModal.jsx";
import LinkedRequestCell from "../../components/complaints/LinkedRequestCell.jsx";
import ReferenceChip from "../../components/complaints/ReferenceChip.jsx";
import PageLoader from "../../components/PageLoader.jsx";
import { complaintsApi } from "../../api/complaints.js";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";
import ComplaintEdit from "./ComplaintEdit.jsx";
import { getComplaintWorkflowStatus } from "../../utils/complaintWorkflowAction.js";

const STATUSES   = ["Pending", "Under Process", "In Process", "Resolved", "Rejected"];
const QUERY_TYPES = ["Service", "Installation", "Sales", "Others"];
const ACTIONS    = ["Ask for Invoice", "Request Sent", "Documents Received"];

const ACTION_STYLE = {
  "Ask for Invoice":    "bg-orange-500 text-white border-orange-500",
  "Request Sent":       "bg-blue-500 text-white border-blue-500",
  "Email Already Sent": "bg-blue-500 text-white border-blue-500",
  "Documents Received": "bg-emerald-600 text-white border-emerald-600",
};

// Default action button shown when no prior action recorded, keyed by query_type
// Default action button shown when no prior action recorded, keyed by query_type.
// Business decision: for all complaint types (including legacy imports),
// show "Ask for Invoice" as the default starting action.
const DEFAULT_ACTION = {
  Installation: "Ask for Invoice",
  Service:      "Ask for Invoice",
  Sales:        "Ask for Invoice",
  Others:       "Ask for Invoice",
};

const STAT_CARDS = [
  { key: "pending",       label: "Pending",       edge: "border-t-[#E0A415]",   ring: "ring-amber-300",  filter: "Pending"       },
  { key: "resolved",      label: "Resolved",      edge: "border-t-[#1D9E75]", ring: "ring-emerald-400", filter: "Resolved"      },
  { key: "under_process", label: "Under Process", edge: "border-t-[#378ADD]",     ring: "ring-sky-300",    filter: "Under Process" },
  { key: "rejected",      label: "Rejected",      edge: "border-t-[#D64545]",    ring: "ring-rose-400",   filter: "Rejected"      },
  { key: "in_process",    label: "In Process",    edge: "border-t-[#1E3A78]",   ring: "ring-slate-400",  filter: "In Process"    },
];

const CHART_FILL = {
  Pending: "#fbbf24", Resolved: "#059669",
  "Under Process": "#38bdf8", Rejected: "#e11d48", "In Process": "#64748b",
};

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  catch { return s; }
}

function trunc(s, n = 28) {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function FilterField({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-base text-slate-700 focus:border-brand-500 focus:outline-none sm:text-sm"
      />
    </div>
  );
}

function CellLabel({ children }) {
  return (
    <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{children}</span>
  );
}

function CardRow({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="break-words text-slate-800">{children}</dd>
    </div>
  );
}

export default function ComplaintList() {
  const { user: permUser } = useAuth();
  const navigate = useNavigate();
  const { user } = useAuth();
  const rawRole = user?.role || "";
  const role = rawRole.toString().trim().toLowerCase();
  const isCallcenter = role === "callcenter";
  const isAdminLike = isOperationsAdminRole(role);
  const isSales =
    role === "sales" ||
    role === "sale" ||
    role === "sales_team" ||
    role === "sales team";

  // Prefer explicit permission flags from backend over hard-coded role checks.
  // This ensures roles like SALES, which have "Edit" enabled for complaints in
  // the role matrix, can actually see the Edit button in the grid.
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const hasComplaintEditPermission = permissions.includes("complaints.can_edit");

  const canEditComplaints =
    hasComplaintEditPermission ||
    isCallcenter ||
    isAdminLike ||
    isSales;

  const [summary, setSummary]           = useState(null);
  const [data, setData]                 = useState({ items: [], total: 0 });
  const [loading, setLoading]           = useState(false);
  const [err, setErr]                   = useState("");
  const [filters, setFilters]           = useState({
    id: "", comp_no: "", customer_name: "", status: "",
    mobile: "", source: "", date_from: "", date_to: "", priority: "",
  });
  const [page, setPage]                 = useState(1);
  const [perPage, setPerPage]           = useState(20);
  const [editTarget, setEditTarget]     = useState(null);
  const [actionTarget, setActionTarget] = useState(null);
  const [actionType, setActionType]     = useState(null);
  const [actionRemark, setActionRemark] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [viewTarget, setViewTarget]       = useState(null);

  // Load summary counts for stat cards
  useEffect(() => {
    api.get("/api/dashboard/complaints-summary")
      .then((r) => setSummary(r.data))
      .catch(() => {});
  }, []);

  const params = useMemo(() => {
    const searchParts = [filters.customer_name, filters.mobile].filter(Boolean);
    return {
      page,
      per_page: perPage,
      id: filters.id ? parseInt(filters.id, 10) : undefined,
      comp_no: filters.comp_no || undefined,
      search: searchParts.length ? searchParts.join(" ") : undefined,
      status: filters.status || undefined,
      source: filters.source || undefined,
      priority: filters.priority || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
    };
  }, [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await complaintsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load complaints");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [params]);

  function patch(key, value) {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  }

  function resetFilters() {
    setFilters({ id: "", comp_no: "", customer_name: "", status: "", mobile: "", source: "", date_from: "", date_to: "", priority: "" });
    setPage(1);
  }

  function clickStatCard(filter) {
    setFilters((f) => ({ ...f, status: f.status === filter ? "" : filter }));
    setPage(1);
  }

  async function submitAction() {
    if (!actionTarget || !actionType) return;
    try {
      await complaintsApi.recordAction(actionTarget.id, { action_taken: actionType, remark: actionRemark || null });
      setActionTarget(null); setActionType(null); setActionRemark("");
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to record action");
    }
  }

  async function sendUploadLink(c) {
    const alreadySent = Boolean(c.document_link_sent);
    const bounceNote = c.email_bounced
      ? `WARNING: the last email to ${c.customer_email} BOUNCED (${c.email_bounce_reason || "not delivered"}).\nPlease correct the email address first (Edit).\n\n`
      : "";
    const message = bounceNote + (alreadySent
      ? `The customer upload link was already sent for ${c.comp_no}.\n\nDo you want to send it again to ${c.customer_email}?`
      : `Send the customer upload link for ${c.comp_no} to ${c.customer_email}?`);
    if (!window.confirm(message)) return;
    try {
      await complaintsApi.requestCustomerUploadLink(c.id, alreadySent);
      alert(`Upload link email ${alreadySent ? "resent" : "sent"} to ${c.customer_email}.`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to send the upload link");
    }
  }

  async function togglePriority(c) {
    const next = c.priority === "High" ? "Normal" : "High";
    try {
      await complaintsApi.setPriority(c.id, next);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Could not change the priority");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await complaintsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      setViewTarget(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  async function rejectComplaint(complaint) {
    if (!window.confirm(`Reject complaint ${complaint.comp_no}?`)) return;
    try {
      const fd = new FormData();
      fd.append("new_status", "Rejected");
      fd.append("remark", "Rejected by admin");
      await complaintsApi.updateStatus(complaint.id, fd);
      setViewTarget(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to reject complaint");
    }
  }

  function exportCsv() {
    const url = complaintsApi.exportUrl(params);
    const token = localStorage.getItem("indcool_token");
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = `complaints_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(obj);
      });
  }

  const chartData = summary
    ? STAT_CARDS.map((c) => ({
        name:  c.label,
        value: summary[c.key] ?? 0,
        fill:  CHART_FILL[c.filter] ?? "#94a3b8",
      }))
    : [];

  function shownActionFor(c) {
    // For legacy-imported rows where last_action_taken was stored as
    // "Legacy import", treat that as "no previous action" so that
    // the button shows the normal default (Ask for Invoice).
    const lastAction = c.last_action_taken === "Legacy import" ? null : c.last_action_taken;
    const defaultAct = DEFAULT_ACTION[c.query_type] || "Ask for Invoice";
    return lastAction || defaultAct;
  }

  function renderActionButtons(c, shownAction, big) {
    const size = big ? "min-h-[40px] px-3 py-2 text-sm" : "px-2 py-0.5 text-xs";
    return (
      <>
        <button
          title="View"
          onClick={() => setViewTarget(c)}
          className={big
            ? "min-h-[40px] rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:text-brand-600"
            : "rounded p-1 text-slate-500 hover:text-brand-600"}
        >
          {big ? "👁 View" : "👁"}
        </button>
        {canEditComplaints && (
          <button
            title="Edit"
            onClick={() => setEditTarget(c)}
            className={`rounded border border-slate-300 text-slate-700 hover:bg-slate-50 ${size}`}
          >
            Edit
          </button>
        )}
        {canEditComplaints && (
          <button
            title={c.priority === "High" ? "Remove the high priority mark" : "Mark as HIGH priority: it will blink and be shown first"}
            onClick={() => togglePriority(c)}
            className={`rounded border font-medium ${c.priority === "High" ? "border-orange-600 bg-orange-100 text-orange-800 hover:bg-orange-200" : "border-orange-300 text-orange-700 hover:bg-orange-50"} ${size}`}
          >
            {c.priority === "High" ? "Clear priority" : "Mark priority"}
          </button>
        )}
{hasPermission(permUser, "complaints", "can_delete", c.query_type) && (
        <button
          title="Delete"
          onClick={() => setConfirmDelete(c)}
          className={`rounded border border-rose-300 text-rose-700 hover:bg-rose-50 ${size}`}
        >
          Delete
        </button>
)}
        {canEditComplaints && (c.query_type || "").toLowerCase() === "service" && c.customer_email && (
          <button
            title={c.email_bounced ? `Email bounced: ${c.email_bounce_reason || "not delivered"}. Correct the email first.` : "Email the customer document upload link"}
            onClick={() => sendUploadLink(c)}
            className={`rounded border font-medium ${c.email_bounced ? BOUNCED_BUTTON : "border-sky-300 text-sky-800 hover:bg-sky-50"} ${size}`}
          >
            {c.email_bounced ? "Email bounced - fix & resend" : c.document_link_sent ? "Resend link" : "Send link"}
          </button>
        )}
        <button
          onClick={() => { setActionTarget(c); setActionType(shownAction); }}
          className={`inline-block rounded border font-medium leading-snug transition-opacity hover:opacity-80 ${big ? "min-h-[40px] px-3 py-2 text-sm" : "px-2.5 py-1 text-xs"} ${ACTION_STYLE[shownAction] || "bg-slate-100 text-slate-600 border-slate-200"}`}
        >
          {shownAction}
        </button>
      </>
    );
  }

  return (
    <div className="space-y-4">

      {/* ── Page Header ── */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <h1 className="text-xl font-semibold text-slate-800">
          Complaint Dashboard
          <span className="ml-2 text-sm font-normal text-slate-400">Overview</span>
        </h1>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="text-brand-600">🏠</span>
          <span>/</span>
          <span>Complaints</span>
        </nav>
        <div
          onClick={() => patch("priority", filters.priority === "High" ? "" : "High")}
          title="Click to show only the high priority complaints (click again to show all)"
          className={`min-w-[130px] flex-1 cursor-pointer overflow-hidden rounded-lg border-t-4 border-orange-500 bg-white shadow transition-transform hover:-translate-y-0.5 hover:shadow-md ${filters.priority === "High" ? "ring-2 ring-orange-400 ring-offset-1" : ""}`}
        >
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-orange-700">
              {(data.high_priority_total || 0) > 0 && <span className="prio-dot-orange" />}
              High Priority
            </div>
            <div className="text-2xl font-bold text-slate-800">{data.high_priority_total || 0}</div>
            <div className="text-xs text-slate-400">Complaints</div>
          </div>
        </div>
      </div>

      {/* ── Stat Cards ── */}
      <div className="flex flex-wrap gap-3">
        {STAT_CARDS.map((card) => (
          <div
            key={card.key}
            onClick={() => clickStatCard(card.filter)}
            className={`min-w-[130px] flex-1 cursor-pointer overflow-hidden rounded-lg border-t-4 bg-white shadow transition-transform hover:-translate-y-0.5 hover:shadow-md ${card.edge} ${filters.status === card.filter ? `ring-2 ring-offset-1 ${card.ring}` : ""}`}
          >
            <div className="px-3 pt-2 text-xs font-semibold text-slate-500">
              {card.label}
            </div>
            <div className="px-3 pb-3 pt-1">
              <p className="text-2xl font-bold text-indcool-navy">{summary?.[card.key] ?? "—"}</p>
              <p className="mt-0.5 text-xs text-slate-400">Complaints</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Filter Box (always visible) ── */}
      <div className="rounded bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <h3 className="text-sm font-semibold text-slate-600">Filter</h3>
          <div className="flex gap-2">
            <button
              onClick={exportCsv}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              Export CSV
            </button>
            <Link
              to="/complaints/new"
              className="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              + New Complaint
            </Link>
          </div>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <FilterField label="ID" value={filters.id} onChange={(v) => patch("id", v)} placeholder="ID" />
            <FilterField label="Service Request Number" value={filters.comp_no} onChange={(v) => patch("comp_no", v)} placeholder="Ref No" />
            <FilterField label="Customer Name" value={filters.customer_name} onChange={(v) => patch("customer_name", v)} placeholder="Customer Name" />
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Select Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => patch("status", e.target.value)}
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-base text-slate-700 sm:text-sm"
              >
                <option value="">-- Select --</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <FilterField label="Customer Mobile Number" value={filters.mobile} onChange={(v) => patch("mobile", v)} placeholder="Mobile" />
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Select Created By
              </label>
              <select
                value={filters.source}
                onChange={(e) => patch("source", e.target.value)}
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-base text-slate-700 sm:text-sm"
              >
                <option value="">-- Select --</option>
                <option value="callcenter">callcenter</option>
                <option value="indcool">indcool</option>
                <option value="public">Public User</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-orange-700">
                Priority
              </label>
              <select
                value={filters.priority}
                onChange={(e) => patch("priority", e.target.value)}
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-base text-slate-700 sm:text-sm"
              >
                <option value="">-- All --</option>
                <option value="High">High priority</option>
                <option value="Normal">Normal</option>
              </select>
            </div>
            <FilterField label="Created Date (From)" value={filters.date_from} onChange={(v) => patch("date_from", v)} placeholder="" type="date" />
            <FilterField label="Created Date (To)" value={filters.date_to} onChange={(v) => patch("date_to", v)} placeholder="" type="date" />
          </div>
          <div className="flex gap-2">
            <button
              onClick={load}
              className="inline-flex items-center gap-1.5 rounded bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              🔍 Search
            </button>
            <button
              onClick={resetFilters}
              className="inline-flex items-center gap-1.5 rounded border border-slate-300 bg-white px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              ↺ Reset
            </button>
          </div>
        </div>
      </div>

      {err && (
        <div className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      {/* ── Table (wide screens): every field visible, no sideways scrolling ── */}
      <div className="hidden rounded bg-white shadow-sm xl:block">
        <table className="w-full table-fixed text-xs">
          <colgroup>
            <col style={{ width: "13%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "15%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "8%" }} />
            <col style={{ width: "14%" }} />
          </colgroup>
          <thead className="text-left">
            <tr>
              {[
                "Id / Ref No",
                "Customer Name / Mobile / Email",
                "Status / Status Date",
                "Query Type / Linked Request",
                "Model Details / Problem Description / Remark",
                "Assigned Engineer / Customer Address",
                "Created By / Created At",
                "Action",
              ].map((h) => (
                <th
                  key={h}
                  className="sticky -top-6 z-20 bg-indcool-navy px-3 py-3 align-bottom text-[13px] font-bold leading-snug text-white shadow-[0_3px_6px_-1px_rgba(15,23,42,0.45)]"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={8}><PageLoader /></td>
              </tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={8} className="py-10 text-center text-slate-400">No complaints found.</td>
              </tr>
            )}
            {!loading && data.items.map((c) => {
              const shownAction = shownActionFor(c);
              return (
                <tr key={c.id} className={`align-top transition-colors ${c.email_bounced ? "bg-red-50 hover:bg-red-100/70" : "hover:bg-sky-50/40"} ${c.priority === "High" ? "prio-row" : ""}`}>
                  <td className="space-y-1 px-3 py-2">
                    <div className="font-medium tabular-nums text-slate-700">
                      <CellLabel>Id</CellLabel> {c.id}
                    </div>
                    <ReferenceChip
                      label={c.comp_no}
                      title={`Complaint ${c.comp_no}`}
                      asButton
                      onClick={() => setViewTarget(c)}
                    />
                    {c.priority === "High" && <div><PriorityBadge at={c.priority_at} /></div>}
                  </td>
                  <td className="space-y-1 break-words px-3 py-2">
                    <div className="font-medium text-slate-800">{c.customer_name || "—"}</div>
                    <div className="tabular-nums"><CellLabel>Mobile</CellLabel> {c.customer_mobile || "—"}</div>
                    <div className={`break-all ${c.email_bounced ? "font-bold text-red-700" : ""}`}><CellLabel>Email</CellLabel> {c.customer_email || "—"}</div>
                    {c.email_bounced && <BounceBadge reason={c.email_bounce_reason} />}
                    {c.email_bounced && c.email_bounce_reason && (
                      <div className="text-[11px] leading-snug text-red-700">{c.email_bounce_reason.split(". Server said")[0]}</div>
                    )}
                  </td>
                  <td className="space-y-1 px-3 py-2">
                    <StatusBadge value={getComplaintWorkflowStatus(c) || c.status} />
                    <div><CellLabel>Status date</CellLabel> {fmtDate(c.status_date)}</div>
                  </td>
                  <td className="space-y-1 px-3 py-2">
                    <div><CellLabel>Type</CellLabel> {c.query_type || "—"}</div>
                    <div>
                      <CellLabel>Linked</CellLabel>{" "}
                      <LinkedRequestCell complaint={c} />
                    </div>
                  </td>
                  <td className="space-y-1 break-words px-3 py-2">
                    <div><CellLabel>Model</CellLabel> {c.model_details || "—"}</div>
                    <div><CellLabel>Problem</CellLabel> {c.problem_description || "—"}</div>
                    <div><CellLabel>Remark</CellLabel> {c.remark || "—"}</div>
                  </td>
                  <td className="space-y-1 break-words px-3 py-2">
                    <div><CellLabel>Engineer</CellLabel> {c.assigned_engineer_name || "—"}</div>
                    <div><CellLabel>Address</CellLabel> {c.customer_address || "—"}</div>
                  </td>
                  <td className="space-y-1 break-words px-3 py-2">
                    <div><CellLabel>By</CellLabel> {c.created_by_name || "—"}</div>
                    <div><CellLabel>At</CellLabel> {fmtDate(c.created_at)}</div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap items-center gap-1">{renderActionButtons(c, shownAction, false)}</div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Cards (phones, tablets, small laptops): same fields, same buttons ── */}
      <div className="space-y-3 xl:hidden">
        {loading && (
          <div className="rounded bg-white shadow-sm"><PageLoader /></div>
        )}
        {!loading && data.items.length === 0 && (
          <div className="rounded bg-white py-10 text-center text-slate-400 shadow-sm">No complaints found.</div>
        )}
        {!loading && data.items.map((c) => {
          const shownAction = shownActionFor(c);
          return (
            <div key={c.id} className={`rounded-lg p-3 shadow-sm ${c.email_bounced ? "border border-red-300 bg-red-50" : "bg-white"} ${c.priority === "High" ? "prio-card" : ""}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium tabular-nums text-slate-500">Id {c.id}</span>
                  <ReferenceChip
                    label={c.comp_no}
                    title={`Complaint ${c.comp_no}`}
                    asButton
                    onClick={() => setViewTarget(c)}
                  />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {c.priority === "High" && <PriorityBadge at={c.priority_at} />}
                  <StatusBadge value={getComplaintWorkflowStatus(c) || c.status} />
                </div>
              </div>
              <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
                <CardRow label="Customer Name">{c.customer_name || "—"}</CardRow>
                <CardRow label="Mobile">
                  {c.customer_mobile ? (
                    <a href={`tel:${c.customer_mobile}`} className="text-brand-700 underline">{c.customer_mobile}</a>
                  ) : "—"}
                </CardRow>
                <CardRow label="Email">
                  {c.customer_email ? (
                    <a href={`mailto:${c.customer_email}`} className={`break-all underline ${c.email_bounced ? "font-bold text-red-700" : "text-brand-700"}`}>{c.customer_email}</a>
                  ) : "—"}
                  {c.email_bounced && <BounceBadge reason={c.email_bounce_reason} className="ml-2" />}
                </CardRow>
                <CardRow label="Query Type">{c.query_type || "—"}</CardRow>
                <CardRow label="Linked Request"><LinkedRequestCell complaint={c} /></CardRow>
                <CardRow label="Status Date">{fmtDate(c.status_date)}</CardRow>
                <CardRow label="Model Details">{c.model_details || "—"}</CardRow>
                <CardRow label="Problem Description">{c.problem_description || "—"}</CardRow>
                <CardRow label="Remark">{c.remark || "—"}</CardRow>
                <CardRow label="Assigned Engineer">{c.assigned_engineer_name || "—"}</CardRow>
                <CardRow label="Customer Address">{c.customer_address || "—"}</CardRow>
                <CardRow label="Created By">{c.created_by_name || "—"}</CardRow>
                <CardRow label="Created At">{fmtDate(c.created_at)}</CardRow>
              </dl>
              <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                {renderActionButtons(c, shownAction, true)}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Table Footer ── */}
      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(n) => { setPerPage(n); setPage(1); }}
      />

      {/* ── Bar Chart ── */}
      <div className="rounded bg-white p-5 shadow-sm">
        <h3 className="mb-4 border-b border-slate-100 pb-2 text-base font-semibold text-slate-700">
          Complaint Status Chart
        </h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" name="Complaints" radius={[3, 3, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <ComplaintQuickViewModal
        complaint={viewTarget}
        open={!!viewTarget}
        onClose={() => setViewTarget(null)}
        isAdminLike={isAdminLike}
        canEdit={canEditComplaints}
        isCallcenter={isCallcenter}
        onEdit={(c) => { setEditTarget(c); setViewTarget(null); }}
        onDelete={(c) => { setConfirmDelete(c); setViewTarget(null); }}
        onReject={rejectComplaint}
      />

      {/* ── Edit Status Modal ── */}
      {editTarget && (
        <ComplaintEdit
          complaint={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => { setEditTarget(null); load(); }}
        />
      )}

      {/* ── Record Action Modal ── */}
      <Modal
        open={!!actionTarget && !!actionType}
        onClose={() => { setActionTarget(null); setActionType(null); setActionRemark(""); }}
        title={`Record action: ${actionType || ""}`}
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600">
            Complaint <span className="font-mono">{actionTarget?.comp_no}</span> — {actionTarget?.customer_name}
          </p>
          <div className="flex flex-wrap gap-2">
            {ACTIONS.map((a) => (
              <button
                key={a}
                onClick={() => setActionType(a)}
                className={`rounded border px-3 py-1 text-xs font-medium transition-colors ${
                  actionType === a
                    ? ACTION_STYLE[a] || "bg-brand-600 text-white border-brand-600"
                    : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
          <textarea
            value={actionRemark}
            onChange={(e) => setActionRemark(e.target.value)}
            rows={3}
            placeholder="Optional remark"
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setActionTarget(null); setActionType(null); setActionRemark(""); }}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={submitAction}
              className="rounded bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700"
            >
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Delete Confirm Modal ── */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete complaint?"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete complaint{" "}
            <span className="font-mono">{confirmDelete?.comp_no}</span>.
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
    </div>
  );
}
