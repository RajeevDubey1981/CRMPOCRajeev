import { useEffect, useMemo, useState } from "react";
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
  { key: "pending",       label: "Pending",       bg: "bg-amber-400",   ring: "ring-amber-300",  filter: "Pending"       },
  { key: "resolved",      label: "Resolved",      bg: "bg-emerald-600", ring: "ring-emerald-400", filter: "Resolved"      },
  { key: "under_process", label: "Under Process", bg: "bg-sky-400",     ring: "ring-sky-300",    filter: "Under Process" },
  { key: "rejected",      label: "Rejected",      bg: "bg-rose-600",    ring: "ring-rose-400",   filter: "Rejected"      },
  { key: "in_process",    label: "In Process",    bg: "bg-slate-500",   ring: "ring-slate-400",  filter: "In Process"    },
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
        className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
      />
    </div>
  );
}

export default function ComplaintList() {
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
    mobile: "", source: "", date_from: "", date_to: "",
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
    setFilters({ id: "", comp_no: "", customer_name: "", status: "", mobile: "", source: "", date_from: "", date_to: "" });
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
      </div>

      {/* ── Stat Cards ── */}
      <div className="flex flex-wrap gap-3">
        {STAT_CARDS.map((card) => (
          <div
            key={card.key}
            onClick={() => clickStatCard(card.filter)}
            className={`flex-1 min-w-[130px] cursor-pointer overflow-hidden rounded shadow transition-transform hover:-translate-y-0.5 hover:shadow-md ${card.bg} ${filters.status === card.filter ? `ring-2 ring-offset-1 ${card.ring}` : ""}`}
          >
            <div className="bg-black/10 px-3 py-2 text-xs font-semibold text-white/90">
              {card.label}
            </div>
            <div className="px-3 py-3">
              <p className="text-2xl font-bold text-white">{summary?.[card.key] ?? "—"}</p>
              <p className="mt-0.5 text-xs text-white/70">Complaints</p>
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
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700"
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
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700"
              >
                <option value="">-- Select --</option>
                <option value="callcenter">callcenter</option>
                <option value="indcool">indcool</option>
                <option value="public">Public User</option>
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

      {/* ── Table ── */}
      <div className="overflow-x-auto rounded bg-white shadow-sm">
        <table className="w-full min-w-[1280px] text-xs">
          <thead className="border-b-2 border-slate-200 bg-slate-50 text-left">
          <tr>
              {[
                "Id", "Ref No", "Customer Name", "Status", "Query Type",
                "Linked Request", "Remark", "Assigned Engineer", "Mobile", "Model Details",
                "Action", // move action column next to model details
                "Problem Description", "Status Date", "Email",
                "Customer Address", "Created By", "Created At",
              ].map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2.5 font-semibold text-slate-600">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={17} className="py-10 text-center text-slate-400">Loading…</td>
              </tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={17} className="py-10 text-center text-slate-400">No complaints found.</td>
              </tr>
            )}
            {!loading && data.items.map((c) => {
              // For legacy-imported rows where last_action_taken was stored as
              // "Legacy import", treat that as "no previous action" so that
              // the button shows the normal default (Ask for Invoice).
              const lastAction = c.last_action_taken === "Legacy import" ? null : c.last_action_taken;
              const defaultAct = DEFAULT_ACTION[c.query_type] || "Ask for Invoice";
              const shownAction = lastAction || defaultAct;

              return (
                <tr key={c.id} className="transition-colors hover:bg-sky-50/40">
                  <td className="w-14 whitespace-nowrap px-3 py-2 font-medium tabular-nums text-slate-700">{c.id}</td>
                  <td className="min-w-[10.5rem] whitespace-nowrap px-3 py-2">
                    <ReferenceChip
                      label={c.comp_no}
                      title={`Complaint ${c.comp_no}`}
                      asButton
                      onClick={() => setViewTarget(c)}
                    />
                  </td>
                  <td className="max-w-[110px] truncate px-3 py-2" title={c.customer_name}>
                    {c.customer_name || "—"}
                  </td>
                  <td className="min-w-[11rem] whitespace-nowrap px-3 py-2 align-middle">
                    <StatusBadge value={getComplaintWorkflowStatus(c) || c.status} />
                  </td>
                  <td className="px-3 py-2">{c.query_type || "—"}</td>
                  <td className="min-w-[10.5rem] whitespace-nowrap px-3 py-2">
                    <LinkedRequestCell complaint={c} />
                  </td>
                  <td className="max-w-[120px] truncate px-3 py-2" title={c.remark || ""}>
                    {trunc(c.remark)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{c.assigned_engineer_name || "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{c.customer_mobile}</td>
                  <td className="max-w-[110px] truncate px-3 py-2" title={c.model_details || ""}>
                    {trunc(c.model_details, 22)}
                  </td>
                  {/* Action column moved to immediately follow Model Details */}
                  <td className="min-w-[12rem] whitespace-nowrap px-3 py-2 align-middle">
                    <div className="flex flex-nowrap items-center gap-1">
                      <button
                        title="View"
                        onClick={() => setViewTarget(c)}
                        className="rounded p-1 text-slate-500 hover:text-brand-600"
                      >
                        👁
                      </button>
                      {canEditComplaints && !c.document_link_sent && (
                        <button
                          title="Edit"
                          onClick={() => setEditTarget(c)}
                          className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-50"
                        >
                          Edit
                        </button>
                      )}
                      <button
                        title="Delete"
                        onClick={() => setConfirmDelete(c)}
                        className="rounded border border-rose-300 px-2 py-0.5 text-xs text-rose-700 hover:bg-rose-50"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => { setActionTarget(c); setActionType(shownAction); }}
                        className={`inline-block whitespace-nowrap rounded border px-2.5 py-1 text-xs font-medium leading-snug transition-opacity hover:opacity-80 ${ACTION_STYLE[shownAction] || "bg-slate-100 text-slate-600 border-slate-200"}`}
                      >
                        {shownAction}
                      </button>
                    </div>
                  </td>
                  <td className="max-w-[120px] truncate px-3 py-2" title={c.problem_description || ""}>
                    {trunc(c.problem_description)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{fmtDate(c.status_date)}</td>
                  <td className="max-w-[120px] truncate px-3 py-2" title={c.customer_email || ""}>
                    {c.customer_email || "—"}
                  </td>
                  <td className="max-w-[120px] truncate px-3 py-2" title={c.customer_address || ""}>
                    {trunc(c.customer_address)}
                  </td>
                  <td className="px-3 py-2">{c.created_by_name || "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2">{fmtDate(c.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
        canEdit={canEditComplaints && !data.items.find((item) => item.id === viewTarget?.id)?.document_link_sent}
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
