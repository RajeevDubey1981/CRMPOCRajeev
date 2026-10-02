import { Fragment, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { installationsApi } from "../../api/installations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";
import BulkAssignModal from "./BulkAssignModal.jsx";
import BulkInstallationEditModal from "./BulkInstallationEditModal.jsx";
import { isBulkWorkflowEligibleRow } from "../../utils/installationWorkflowSteps.js";

const STATUSES = ["Pending", "Submitted", "Assigned", "In Progress", "Serial Pending Verification", "Completion Pending Approval", "Installation Completed", "Payment Pending", "Completed", "Settlement Pending", "Settlement Approved", "Returned", "Rejected"];
const BULK_ASSIGNABLE_STATUSES = new Set(["Submitted", "Assigned"]);

function fmtDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return value;
  }
}

function isCompletedStatus(status) {
  return status === "Completed";
}

function summarizeGroupValue(rows, key) {
  const values = Array.from(new Set(rows.map((row) => row[key]).filter(Boolean)));
  if (values.length === 0) return "-";
  if (values.length === 1) return values[0];
  return "Mixed";
}

function canAdminBulkAssign(row) {
  return BULK_ASSIGNABLE_STATUSES.has(row.status);
}

function canAdminBulkEdit(row) {
  return row.status !== "Submitted";
}

function isEngineerEditable(row) {
  return row.status !== "Completed";
}

export default function InstallationList() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isEngineer = user?.role === "engineer";
  const isAdminLike = isOperationsAdminRole(user?.role);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    search: "",
    date_from: "",
    date_to: "",
  });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [cancelBusyId, setCancelBusyId] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [selectedGroupKey, setSelectedGroupKey] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkAssignOpen, setBulkAssignOpen] = useState(false);
  const [bulkEditOpen, setBulkEditOpen] = useState(false);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: filters.status || undefined,
    search: filters.search || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  }), [page, perPage, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await installationsApi.list(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load installations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  function applyFilter(patch) {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  }

  function toggleGroup(groupKey) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  }

  function clearSelection() {
    setSelectedGroupKey(null);
    setSelectedIds(new Set());
  }

  function isRowSelectable(groupKey, row) {
    if (selectedGroupKey && selectedGroupKey !== groupKey) return false;
    return isEngineer ? isEngineerEditable(row) : canAdminBulkAssign(row) || canAdminBulkEdit(row);
  }

  function toggleSelected(groupKey, row) {
    if (!isRowSelectable(groupKey, row)) return;
    setSelectedGroupKey((prev) => prev || groupKey);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(row.id)) next.delete(row.id);
      else next.add(row.id);
      if (next.size === 0) setSelectedGroupKey(null);
      return next;
    });
  }

  const selectedRows = useMemo(
    () => data.items.filter((row) => selectedIds.has(row.id)),
    [data.items, selectedIds],
  );

  const groupedRows = useMemo(() => {
    const groups = new Map();

    for (const inst of data.items) {
      const key = [
        inst.item_code || "__missing_item_code__",
        inst.order_no || "__missing_order__",
        inst.vendor_name || "__missing_vendor__",
      ].join("::");
      const current = groups.get(key);
      if (current) {
        current.requests.push(inst);
        current.pendingCount += isCompletedStatus(inst.status) ? 0 : 1;
        current.completedCount += isCompletedStatus(inst.status) ? 1 : 0;
        current.assignedEngineerName = summarizeGroupValue(current.requests, "assigned_engineer_name");
        current.settlementRaisedByName = summarizeGroupValue(current.requests, "settlement_approved_by_name");
        continue;
      }
      groups.set(key, {
        key,
        itemCode: inst.item_code || "-",
        itemName: inst.product_name || "-",
        orderNo: inst.order_no || "-",
        vendorName: inst.vendor_name || "-",
        assignedEngineerName: summarizeGroupValue([inst], "assigned_engineer_name"),
        settlementRaisedByName: summarizeGroupValue([inst], "settlement_approved_by_name"),
        pendingCount: isCompletedStatus(inst.status) ? 0 : 1,
        completedCount: isCompletedStatus(inst.status) ? 1 : 0,
        requests: [inst],
      });
    }

    return Array.from(groups.values());
  }, [data.items]);

  async function doReject(row) {
    if (!window.confirm(`Reject installation request #${row.id}?`)) return;
    try {
      const fd = new FormData();
      fd.append("new_status", "Rejected");
      await installationsApi.updateStatus(row.id, fd);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to reject installation request");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await installationsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  }

  async function doCancel(row) {
    setCancelBusyId(row.id);
    try {
      await installationsApi.cancel(row.id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(row.id);
        return next;
      });
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to cancel submission");
    } finally {
      setCancelBusyId(null);
    }
  }

  const canOpenBulkAssign = selectedRows.length > 0 && selectedRows.every((row) => canAdminBulkAssign(row));
  const canOpenBulkWorkflow = selectedRows.length > 1
    && selectedRows.every((row) => isBulkWorkflowEligibleRow(row, {
      isAdminLike,
      userId: user?.id,
      userName: user?.name,
    }));
  const canOpenBulkEdit = !isEngineer
    && selectedRows.length > 0
    && selectedRows.every((row) => canAdminBulkEdit(row));
  const canOpenEngineerWorkflow = isEngineer
    && selectedRows.length === 1
    && isEngineerEditable(selectedRows[0]);

  function openInstallationWorkflow(row) {
    navigate(`/installations/${row.id}?edit=1`);
  }

  function editLabel(row) {
    if (isEngineer && row.assigned_engineer) return "Workflow";
    return "Edit";
  }

  function openSelectedBulkWorkflow() {
    if (!canOpenBulkWorkflow || selectedRows.length < 2) return;
    const ids = selectedRows.map((row) => row.id).join(",");
    navigate(`/installations/bulk-workflow?ids=${ids}`);
  }

  function openSelectedEdit() {
    if (!canOpenBulkEdit || selectedRows.length === 0) return;
    if (selectedRows.length === 1) {
      openInstallationWorkflow(selectedRows[0]);
      return;
    }
    setBulkEditOpen(true);
  }

  function bulkActionLabel() {
    if (selectedRows.length <= 1) return selectedRows[0] ? editLabel(selectedRows[0]) : "Edit";
    return "Bulk edit";
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Installation Requests</h1>
        <button
          onClick={() => navigate("/installations/new")}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New Request
        </button>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input
            type="text"
            placeholder="Search customer name / mobile / product"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={filters.status}
            onChange={(e) => applyFilter({ status: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => applyFilter({ date_from: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => applyFilter({ date_to: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {isAdminLike && (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          Expand a row with <strong>+</strong>, select multiple requests in the same item code, then use <strong>Bulk workflow</strong> to review each serial and status before approving completion or payment.
        </div>
      )}

      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between rounded-lg bg-brand-50 px-4 py-3">
          <span className="text-sm font-medium text-brand-700">
            {selectedIds.size} row(s) selected {selectedGroupKey ? `in ${selectedGroupKey.split("::")[0]}` : ""}
          </span>
          <div className="flex gap-2">
            {!isEngineer && (
              <button
                onClick={() => setBulkAssignOpen(true)}
                disabled={!canOpenBulkAssign}
                className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Assign Engineer
              </button>
            )}
            {isEngineer && selectedRows.length > 1 && (
              <button
                onClick={openSelectedBulkWorkflow}
                disabled={!canOpenBulkWorkflow}
                className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Bulk workflow
              </button>
            )}
            {isEngineer && selectedRows.length === 1 && (
              <button
                onClick={() => openInstallationWorkflow(selectedRows[0])}
                disabled={!canOpenEngineerWorkflow}
                className="rounded-md border border-brand-300 px-3 py-1.5 text-sm font-medium text-brand-700 disabled:opacity-50"
              >
                Workflow
              </button>
            )}
            {!isEngineer && selectedRows.length > 1 && (
              <button
                onClick={openSelectedBulkWorkflow}
                disabled={!canOpenBulkWorkflow}
                className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Bulk workflow
              </button>
            )}
            {!isEngineer && (
              <button
                onClick={openSelectedEdit}
                disabled={!canOpenBulkEdit}
                className="rounded-md border border-brand-300 px-3 py-1.5 text-sm font-medium text-brand-700 disabled:opacity-50"
              >
                {bulkActionLabel()}
              </button>
            )}
            <button
              onClick={clearSelection}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="w-12 px-3 py-2"></th>
              <th className="px-3 py-2">Item Code</th>
              <th className="px-3 py-2">Item Name</th>
              <th className="px-3 py-2">Order No</th>
              <th className="px-3 py-2">Vendor Name</th>
              <th className="px-3 py-2">Total Pending Requests</th>
              <th className="px-3 py-2">Total Completed Requests</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading...</td>
              </tr>
            )}
            {!loading && groupedRows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">No installation requests found.</td>
              </tr>
            )}
            {!loading && groupedRows.map((group) => {
              const expanded = expandedGroups.has(group.key);

              return (
                <Fragment key={group.key}>
                  <tr className="cursor-pointer hover:bg-slate-50" onClick={() => toggleGroup(group.key)}>
                    <td className="px-3 py-2 text-center text-slate-500">{expanded ? "-" : "+"}</td>
                    <td className="px-3 py-2 font-mono text-xs font-semibold text-slate-700">{group.itemCode}</td>
                    <td className="px-3 py-2 font-medium text-slate-800">{group.itemName}</td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-700">{group.orderNo}</td>
                    <td className="px-3 py-2 text-slate-700">{group.vendorName}</td>
                    <td className="px-3 py-2 font-semibold text-amber-700">{group.pendingCount}</td>
                    <td className="px-3 py-2 font-semibold text-emerald-700">{group.completedCount}</td>
                  </tr>
                  {expanded && (
                    <tr className="bg-slate-50/70">
                      <td colSpan={7} className="px-3 py-3">
                        <div className="mb-3 flex items-center justify-between rounded-md bg-brand-50 px-3 py-2">
                          <span className="text-sm font-medium text-brand-700">
                            {selectedGroupKey === group.key && selectedIds.size > 0
                              ? `${selectedIds.size} row(s) selected in ${group.itemCode}`
                              : "Select requests in this Item Code group for bulk actions"}
                          </span>
                          <div className="text-xs text-slate-500">
                            {!isEngineer && `Assigned engineer: ${group.assignedEngineerName} | Settlement raised by: ${group.settlementRaisedByName}`}
                          </div>
                        </div>

                        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
                          <table className="min-w-full text-sm">
                            <thead className="bg-slate-100 text-left text-slate-700">
                              <tr>
                                <th className="w-12 px-3 py-2"></th>
                                <th className="px-3 py-2">Request Number</th>
                                <th className="px-3 py-2">Complaint</th>
                                {!isEngineer && <th className="px-3 py-2">Vendor</th>}
                                <th className="px-3 py-2">Customer Name</th>
                                <th className="px-3 py-2">Serial Number 1</th>
                                <th className="px-3 py-2">Serial Number 2</th>
                                <th className="px-3 py-2">Current Status</th>
                                {!isEngineer && <th className="px-3 py-2">Assigned Engineer</th>}
                                {!isEngineer && <th className="px-3 py-2">Settlement Raised By</th>}
                                <th className="px-3 py-2">Assigned Date</th>
                                <th className="px-3 py-2">Install Date</th>
                                <th className="px-3 py-2 text-right">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {group.requests.map((row) => (
                                <tr key={row.id} className="hover:bg-slate-50">
                                  <td className="px-3 py-2">
                                    {isRowSelectable(group.key, row) && (
                                      <input
                                        type="checkbox"
                                        checked={selectedIds.has(row.id)}
                                        disabled={selectedGroupKey !== null && selectedGroupKey !== group.key}
                                        onChange={() => toggleSelected(group.key, row)}
                                        className="h-4 w-4"
                                      />
                                    )}
                                  </td>
                                  <td className="px-3 py-2 font-medium text-slate-700">{row.id}</td>
                                  <td className="px-3 py-2">
                                    {row.complaint_id ? (
                                      <Link
                                        to={`/complaints/${row.complaint_id}`}
                                        onClick={(event) => event.stopPropagation()}
                                        className="font-mono text-xs text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700"
                                      >
                                        {row.complaint_no || `#${row.complaint_id}`}
                                      </Link>
                                    ) : (
                                      <span className="text-slate-400">—</span>
                                    )}
                                  </td>
                                  {!isEngineer && <td className="px-3 py-2">{row.vendor_name || "-"}</td>}
                                  <td className="px-3 py-2">{row.customer_name}</td>
                                  <td className="px-3 py-2 font-mono text-xs">{row.serial_no || "-"}</td>
                                  <td className="px-3 py-2 font-mono text-xs">{row.serial_no_2 || "-"}</td>
                                  <td className="px-3 py-2"><StatusBadge value={row.status} /></td>
                                  {!isEngineer && <td className="px-3 py-2">{row.assigned_engineer_name || "-"}</td>}
                                  {!isEngineer && <td className="px-3 py-2">{row.settlement_approved_by_name || "-"}</td>}
                                  <td className="px-3 py-2 text-xs">{fmtDate(row.request_date)}</td>
                                  <td className="px-3 py-2 text-xs">{fmtDate(row.installation_date)}</td>
                                  <td className="px-3 py-2 text-right">
                                    <div className="flex justify-end gap-1">
                                      <button
                                        title="View"
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          navigate(`/installations/${row.id}`);
                                        }}
                                        className="rounded p-1 text-slate-600 hover:bg-slate-100"
                                      >
                                        View
                                      </button>
                                      <button
                                        title={editLabel(row)}
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          openInstallationWorkflow(row);
                                        }}
                                        disabled={isEngineer && !isEngineerEditable(row)}
                                        className="rounded p-1 text-slate-600 hover:bg-slate-100"
                                      >
                                        {editLabel(row)}
                                      </button>
                                      {!isEngineer && row.status !== "Rejected" && (
                                        <button
                                          title="Reject"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            doReject(row);
                                          }}
                                          className="rounded border border-rose-300 px-2 py-0.5 text-xs font-medium text-rose-700 hover:bg-rose-50"
                                        >
                                          Reject
                                        </button>
                                      )}
                                      {!isEngineer && (
                                        <button
                                          title="Delete"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            setConfirmDelete(row);
                                          }}
                                          className="rounded p-1 text-rose-600 hover:bg-rose-50"
                                        >
                                          Delete
                                        </button>
                                      )}
                                      {!isEngineer && (row.status === "Submitted" || row.status === "Assigned") && (
                                        <button
                                          title="Cancel submission"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            doCancel(row);
                                          }}
                                          disabled={cancelBusyId === row.id}
                                          className="rounded border border-rose-300 px-2 py-0.5 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                                        >
                                          {cancelBusyId === row.id ? "..." : "Cancel"}
                                        </button>
                                      )}
                                    </div>
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

      {bulkAssignOpen && (
        <BulkAssignModal
          rows={selectedRows}
          onClose={() => setBulkAssignOpen(false)}
          onSaved={() => {
            setBulkAssignOpen(false);
            clearSelection();
            load();
          }}
        />
      )}

      {bulkEditOpen && (
        <BulkInstallationEditModal
          rows={selectedRows}
          onClose={() => setBulkEditOpen(false)}
          onSaved={() => {
            setBulkEditOpen(false);
            clearSelection();
            load();
          }}
        />
      )}

      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete installation request?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will delete the installation request for <span className="font-medium">{confirmDelete?.customer_name}</span>.
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
