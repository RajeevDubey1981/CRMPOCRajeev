import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import VendorOrderLineItemsEditor, {
  collapseOrderItemsToLineItems,
  serializeVendorLineItems,
  validateVendorLineItems,
} from "../../components/orders/VendorOrderLineItemsEditor.jsx";
import { ordersApi } from "../../api/orders.js";
import { installationsApi } from "../../api/installations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";
import {
  buildOrderItemCsvColumns,
  parseOrderItemCsvHeader,
  rowValuesToCells,
  serialColumnsForCount,
} from "../../utils/orderItemCsv.js";
import { INDIAN_STATES_UTS } from "../../data/indianStates.js";
import InstallationStatusEdit from "../installations/InstallationStatusEdit.jsx";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";

const WORK_STARTED_STATUSES = new Set([
  "In Progress", "Completed", "Settlement Pending", "Settlement Approved", "Rejected",
]);

const ORDER_STATUSES = ["Pending", "Shipped", "In Transit", "Delivered", "Returned", "Cancelled"];
const VENDOR_POST_SHIPMENT_STATUSES = new Set(["Shipped", "In Transit", "Delivered", "Returned", "Completed"]);
const VENDOR_LOCKED_SHIPMENT_STATUSES = new Set(["Shipped", "In Transit"]);

const BLANK_CONSIGNEE = {
  consignee_name: "",
  contact: "",
  email: "",
  city: "",
  state: "",
  address: "",
};

function mapConsigneesFromOrder(rows) {
  return (rows || []).map((row) => ({
    consignee_name: row.consignee_name || "",
    contact: row.contact || "",
    email: row.email || "",
    city: row.city || "",
    state: row.state || "",
    address: row.address || "",
  }));
}

function serializeConsigneesForApi(rows) {
  return (rows || [])
    .filter((row) => Object.values(row).some((value) => (value || "").trim()))
    .map((row) => ({
      consignee_name: (row.consignee_name || "").trim() || null,
      contact: (row.contact || "").trim() || null,
      email: (row.email || "").trim() || null,
      city: (row.city || "").trim() || null,
      state: (row.state || "").trim() || null,
      address: (row.address || "").trim() || null,
    }));
}

function validateConsigneesForSave(rows) {
  for (let idx = 0; idx < (rows || []).length; idx += 1) {
    const row = rows[idx];
    const hasContent = Object.values(row).some((value) => (value || "").trim());
    if (!hasContent) continue;
    const label = rows.length > 1 ? `Consignee address ${idx + 1}` : "Consignee address";
    if (!(row.consignee_name || "").trim()) return `${label}: Consignee name is required.`;
    if (!(row.address || "").trim()) return `${label}: Address is required.`;
  }
  return null;
}

function consigneeSummaryLine(addresses) {
  const rows = addresses || [];
  if (!rows.length) return null;
  const names = rows.map((row) => row.consignee_name).filter(Boolean);
  if (names.length === 1) return names[0];
  if (names.length > 1) return `${names.length} consignees (${names.slice(0, 2).join(", ")}${names.length > 2 ? ", …" : ""})`;
  return `${rows.length} consignee address(es)`;
}

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
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {value}
    </span>
  );
}

function Field({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>
        {value != null && value !== "" ? value : <span className="text-slate-400">-</span>}
      </div>
    </div>
  );
}

function fmtDate(s) {
  if (!s) return null;
  try {
    return new Date(s).toLocaleDateString();
  } catch {
    return s;
  }
}

function fmtDateTime(s) {
  if (!s) return null;
  try {
    return new Date(s).toLocaleString();
  } catch {
    return s;
  }
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

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function parseCsvText(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "\"") {
      if (inQuotes && text[i + 1] === "\"") {
        cell += "\"";
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !inQuotes) {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }

  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  return rows;
}

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, "\"\"")}"`;
  }
  return text;
}

function normalizeSerial(value) {
  return (value || "").trim().toLowerCase();
}

function normalizeItemCode(value) {
  return (value || "").trim() || "UNASSIGNED";
}

export default function OrderDetail() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const isVendor = role === "vendor";
  const orderPermission = (Array.isArray(user?.permissions) ? user.permissions : [])
    .find((permission) => permission.module === "orders");
  const canUpdateOrder = Boolean(orderPermission?.can_edit);

  const [order, setOrder] = useState(null);
  const isVendorPendingOrder = isVendor && order?.status === "Pending";
  const isVendorShippedOrder = isVendor && VENDOR_POST_SHIPMENT_STATUSES.has(order?.status);
  const canManageOemBill = canUpdateOrder;
  const canVendorEditShippedFields = isVendorShippedOrder;
  const canVendorEditPendingItems = isVendorPendingOrder;
  const canManageItemCsv = canUpdateOrder;
  const canViewInstallationRequest = isOperationsAdminRole(role);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(false);
  const [installations, setInstallations] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [selectedInstIds, setSelectedInstIds] = useState(new Set());
  const [bulkEngineerPick, setBulkEngineerPick] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [instErr, setInstErr] = useState("");
  const [instMsg, setInstMsg] = useState("");
  const [progressTarget, setProgressTarget] = useState(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editErr, setEditErr] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [vendors, setVendors] = useState([]);
  const [couriers, setCouriers] = useState([]);
  const [selectedSerials, setSelectedSerials] = useState(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [submitErr, setSubmitErr] = useState("");
  const [submitMsg, setSubmitMsg] = useState("");
  const [csvBusy, setCsvBusy] = useState(false);
  const [csvMsg, setCsvMsg] = useState("");
  const [csvErr, setCsvErr] = useState("");
  const [importPreview, setImportPreview] = useState(null);
  const [collapsedItemGroups, setCollapsedItemGroups] = useState({});
  const [itemOptions, setItemOptions] = useState([]);
  const [editLineItems, setEditLineItems] = useState([]);
  const [editConsignees, setEditConsignees] = useState([]);

  async function load() {
    setErr("");
    try {
      setOrder(await ordersApi.get(id));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load order");
    }
  }

  async function loadInstallations() {
    try {
      const resp = await installationsApi.list({ order_id: id, per_page: 200 });
      setInstallations(resp.items || []);
    } catch {
      setInstallations([]);
    }
  }

  useEffect(() => {
    load();
    ordersApi.vendors().then(setVendors).catch(() => {});
    ordersApi.couriers().then(setCouriers).catch(() => {});
    if (!isVendor) {
      loadInstallations();
      installationsApi.engineerAssignmentOptions().then(setEngineers).catch(() => setEngineers([]));
    }
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [id]);

  useEffect(() => {
    if (order && searchParams.get("edit") === "1") {
      openEdit();
      const next = new URLSearchParams(searchParams);
      next.delete("edit");
      setSearchParams(next, { replace: true });
    }
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [order]);

  function toggleInstSelected(inst) {
    if (!(inst.status === "Submitted" || inst.status === "Assigned")) return;
    setSelectedInstIds((prev) => {
      const next = new Set(prev);
      if (next.has(inst.id)) next.delete(inst.id);
      else next.add(inst.id);
      return next;
    });
  }

  function installationIdsSelectableInGroup(group) {
    const ids = [];
    for (const item of group.rows) {
      const inst = installationForItem(item);
      if (inst && (inst.status === "Submitted" || inst.status === "Assigned")) {
        ids.push(inst.id);
      }
    }
    return ids;
  }

  function toggleSelectAllInstallationsInGroup(group) {
    const ids = installationIdsSelectableInGroup(group);
    if (!ids.length) return;
    const allSelected = ids.every((id) => selectedInstIds.has(id));
    setSelectedInstIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        ids.forEach((id) => next.delete(id));
      } else {
        ids.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function serialSelectionKeysForGroup(group, serialType) {
    const keys = [];
    for (const item of group.rows) {
      if (isItemLocked(item)) continue;
      if (serialType === "serial1" && item.serial_no) keys.push(`${item.id}-serial1`);
      if (serialType === "serial2" && item.serial_no_2) keys.push(`${item.id}-serial2`);
    }
    return keys;
  }

  function toggleSelectAllSerialsInGroup(group, serialType) {
    if (!canSubmitInstallationRequest) return;
    const keys = serialSelectionKeysForGroup(group, serialType);
    if (!keys.length) return;
    const allSelected = keys.every((key) => selectedSerials.has(key));
    setSubmitErr("");
    setSelectedSerials((prev) => {
      if (allSelected) {
        const next = new Set(prev);
        keys.forEach((key) => next.delete(key));
        return next;
      }
      return new Set(keys);
    });
  }

  async function openProgress(inst) {
    setInstErr("");
    setProgressLoading(true);
    try {
      setProgressTarget(await installationsApi.get(inst.id));
    } catch (e) {
      setInstErr(e.response?.data?.detail || "Failed to load installation request");
    } finally {
      setProgressLoading(false);
    }
  }

  async function bulkAssignSelected() {
    if (!bulkEngineerPick || selectedInstIds.size === 0) return;
    setInstErr("");
    setInstMsg("");
    setBulkBusy(true);
    try {
      const assignments = Array.from(selectedInstIds).map((instId) => ({
        installation_id: instId,
        engineer_id: Number(bulkEngineerPick),
      }));
      const result = await installationsApi.bulkAssign(assignments);
      setSelectedInstIds(new Set());
      setBulkEngineerPick("");
      await loadInstallations();
      setInstMsg(`${result.assigned.length} row(s) assigned`);
    } catch (e) {
      setInstErr(e.response?.data?.detail || "Failed to assign engineer");
    } finally {
      setBulkBusy(false);
    }
  }

  async function bulkCancelSelected() {
    if (selectedInstIds.size === 0) return;
    setInstErr("");
    setInstMsg("");
    setBulkBusy(true);
    try {
      const result = await installationsApi.bulkCancel(Array.from(selectedInstIds));
      setSelectedInstIds(new Set());
      await Promise.all([loadInstallations(), load()]);
      setInstMsg(`${result.cancelled.length} row(s) cancelled`);
    } catch (e) {
      setInstErr(e.response?.data?.detail || "Failed to cancel submission(s)");
    } finally {
      setBulkBusy(false);
    }
  }

  function openEdit() {
    if (!canEditOrder) return;
    if (!order) return;
    setEditForm({
      order_no: order.order_no || "",
      order_date: order.order_date || "",
      oem_bill_no: order.oem_bill_no || "",
      vendor_id: order.vendor_id ?? "",
      customer_name: order.customer_name || "",
      customer_contact: order.customer_contact || "",
      customer_email: order.customer_email || "",
      customer_city: order.customer_city || "",
      customer_state: order.customer_state || "",
      customer_address: order.customer_address || "",
      courier_id: order.courier_id ?? "",
      lrn_no: order.lrn_no || "",
      vendor_bill_no: order.vendor_bill_no || "",
      vendor_bill_date: order.vendor_bill_date || "",
      status: order.status || "Pending",
      expected_delivery_date: order.expected_delivery_date || "",
      actual_delivery_date: order.actual_delivery_date || "",
      items: (order.items || []).map((item) => ({
        id: item.id,
        item_name: item.item_name || "",
        item_code: item.item_code || "",
      })),
    });
    if (isVendor && order.status === "Pending") {
      setEditLineItems(collapseOrderItemsToLineItems(order.items || []));
      ordersApi.items().then(setItemOptions).catch(() => setItemOptions([]));
    }
    setEditConsignees(mapConsigneesFromOrder(order.consignee_addresses));
    setEditErr("");
    setEditing(true);
  }

  function setEF(field, value) {
    setEditForm((f) => ({ ...f, [field]: value }));
  }

  function setEditItemCode(itemId, value) {
    setEditForm((f) => ({
      ...f,
      items: (f.items || []).map((item) => (
        item.id === itemId ? { ...item, item_code: value } : item
      )),
    }));
  }

  function groupedItems(items) {
    const groups = new Map();
    items.forEach((item) => {
      const key = item.item_code || "UNASSIGNED";
      if (!groups.has(key)) {
        groups.set(key, {
          itemCode: item.item_code || "",
          itemName: item.item_name || "",
          serialCount: Number(item.serial_count ?? 1),
          rows: [],
        });
      }
      const group = groups.get(key);
      group.rows.push(item);
      if (!group.itemName && item.item_name) group.itemName = item.item_name;
      if (item.serial_count != null) group.serialCount = Number(item.serial_count);
    });
    return Array.from(groups.values());
  }

  function toggleItemGroup(itemCode) {
    setCollapsedItemGroups((prev) => ({ ...prev, [itemCode]: !prev[itemCode] }));
  }

  function downloadCsv(url, filename) {
    const token = localStorage.getItem("indcool_token");
    const requestUrl = url.startsWith("http") ? url : `${window.location.origin}${url}`;
    return fetch(requestUrl, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (r) => {
        if (!r.ok) {
          let detail = "Failed to export CSV";
          try {
            const data = await r.json();
            detail = data.detail || detail;
          } catch {}
          throw new Error(detail);
        }
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        const obj = URL.createObjectURL(blob);
        a.href = obj;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(obj);
      });
  }

  async function handleExport(itemCode = "") {
    setCsvErr("");
    setCsvMsg("");
    setCsvBusy(true);
    try {
      const suffix = itemCode || "all";
      await downloadCsv(
        ordersApi.exportItemsUrl(id, itemCode || undefined),
        `order_${id}_items_${suffix}_${new Date().toISOString().slice(0, 10)}.csv`
      );
      setCsvMsg(`CSV exported${itemCode ? ` for ${itemCode}` : ""}`);
    } catch (e) {
      setCsvErr(e.message || "Failed to export CSV");
    } finally {
      setCsvBusy(false);
    }
  }

  async function handleImport(file, itemCode = "") {
    if (!file) return;
    setCsvErr("");
    setCsvMsg("");
    try {
      const text = await file.text();
      const parsedRows = parseCsvText(text);
      if (parsedRows.length === 0) {
        throw new Error("CSV is empty");
      }
      const [headerRow, ...dataRows] = parsedRows;
      const parsedHeader = parseOrderItemCsvHeader(headerRow);
      if (!parsedHeader) {
        throw new Error("CSV header does not match the expected order item template");
      }

      const rows = dataRows
        .filter((cols) => cols.some((value) => (value || "").trim() !== ""))
        .map((cols, index) => {
          const cells = rowValuesToCells(parsedHeader.columns, cols);
          return {
            previewId: `${Date.now()}-${index}`,
            rowNumber: index + 2,
            cells,
            duplicateReasons: [],
          };
        });

      setImportPreview({
        itemCode,
        fileName: file.name,
        columns: parsedHeader.columns,
        serialColumnCount: parsedHeader.serialColumnCount,
        rows,
      });
    } catch (e) {
      setCsvErr(e.message || "Failed to read CSV");
    }
  }

  function closeImportPreview() {
    if (csvBusy) return;
    setImportPreview(null);
  }

  function removePreviewRow(previewId) {
    setImportPreview((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        rows: prev.rows.filter((row) => row.previewId !== previewId),
      };
    });
  }

  async function saveImportPreview() {
    if (!importPreview || !previewHasRows) {
      setCsvMsg("");
      setCsvErr("There are no rows available to import.");
      return;
    }
    if (previewHasIssues) {
      setCsvMsg("");
      setCsvErr("Please fix or delete the highlighted rows before saving.");
      return;
    }
    setCsvErr("");
    setCsvMsg("Saving import...");
    setCsvBusy(true);
    try {
      const preview = importPreview;
      const exportColumns = preview.columns || buildOrderItemCsvColumns(preview.serialColumnCount ?? 0);
      const csvLines = [
        exportColumns.map(csvEscape).join(","),
        ...preview.rows.map((row) => exportColumns.map((column) => csvEscape(row.cells[column] || "")).join(",")),
      ];
      const csvBlob = new Blob([csvLines.join("\r\n")], { type: "text/csv" });
      await ordersApi.importItemsCsv(
        id,
        csvBlob,
        preview.itemCode || undefined,
        preview.fileName || `order_${id}_items.csv`
      );
      const freshOrder = await ordersApi.get(id);
      setOrder(freshOrder);
      if (!isVendor) {
        await loadInstallations();
      }
      setImportPreview(null);
      setCsvMsg(`CSV imported${preview.itemCode ? ` for ${preview.itemCode}` : ""}`);
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    } catch (e) {
      setCsvMsg("");
      setCsvErr(e.response?.data?.detail || e.message || "Failed to import CSV");
    } finally {
      setCsvBusy(false);
    }
  }

  function isItemLocked(item) {
    return item.installation_status && item.installation_status !== "Not Requested";
  }

  function installationForItem(item) {
    const byOrderItem = installations.find((inst) => inst.order_item_id === item.id);
    if (byOrderItem) return byOrderItem;

    const itemSerials = new Set(
      [item.serial_no, item.serial_no_2].filter(Boolean).map(normalizeSerial),
    );
    if (itemSerials.size === 0) return null;

    return installations.find((inst) => {
      const instSerials = [inst.serial_no, inst.serial_no_2].filter(Boolean).map(normalizeSerial);
      return instSerials.some((serial) => itemSerials.has(serial));
    }) || null;
  }

  function installationStatusLabel(item, inst) {
    if (inst) return inst.status;
    if (item.installation_status === "Submitted") return "Locked (Submitted)";
    return item.installation_status;
  }

  function installationStatusClass(item, inst) {
    const label = installationStatusLabel(item, inst);
    if (label === "Installed" || inst?.status === "Completed") {
      return "bg-green-100 text-green-700";
    }
    if (label === "Not Requested") {
      return "bg-slate-100 text-slate-600";
    }
    return "bg-amber-100 text-amber-700";
  }

  function toggleSerial(item, serialType) {
    if (isItemLocked(item)) return;
    const key = `${item.id}-${serialType}`;
    const itemCode = normalizeItemCode(item.item_code);
    setSelectedSerials((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
        setSubmitErr("");
      } else {
        const selectedItemCodes = Array.from(next).reduce((codes, selectedKey) => {
          const [selectedItemIdStr] = selectedKey.split("-");
          const selectedItem = (order?.items || []).find((candidate) => String(candidate.id) === selectedItemIdStr);
          if (selectedItem) codes.add(normalizeItemCode(selectedItem.item_code));
          return codes;
        }, new Set());
        if (selectedItemCodes.size > 0 && !selectedItemCodes.has(itemCode)) {
          setSubmitErr(`Select serials from only one item code at a time. Current selection is for item code ${Array.from(selectedItemCodes)[0]}.`);
          return prev;
        }
        next.add(key);
        setSubmitErr("");
      }
      return next;
    });
  }

  async function submitSelectedSerials() {
    if (selectedSerials.size === 0) {
      setSubmitErr("Please select at least one serial number");
      return;
    }
    if (!canSubmitInstallationRequest) {
      setSubmitErr("Installation request submission is available only when the order is Delivered and OEM Bill No is present.");
      return;
    }
    if (selectedSubmitItemCodes.size > 1) {
      setSubmitErr("Select serials from only one item code at a time.");
      return;
    }

    setSubmitErr("");
    setSubmitMsg("");
    setSubmitting(true);

    try {
      const result = await ordersApi.submitSerials(id, {
        order_id: parseInt(id, 10),
        selected_serials: Array.from(selectedSerials),
      });

      setSelectedSerials(new Set());
      await Promise.all([
        load(),
        isVendor ? Promise.resolve() : loadInstallations(),
      ]);

      const parts = [`${result.count} row(s) submitted`];
      if (result.skipped_already_submitted?.length) {
        parts.push(`${result.skipped_already_submitted.length} already submitted`);
      }
      setSubmitMsg(parts.join(", "));
    } catch (e) {
      setSubmitErr(e.response?.data?.detail || e.message || "Failed to submit serials");
    } finally {
      setSubmitting(false);
    }
  }

  async function saveEdit(e) {
    e.preventDefault();
    setEditErr("");
    if (!canEditOrder) {
      setEditErr("Your role cannot edit orders.");
      return;
    }
    setEditSaving(true);
    try {
      const consigneeError = validateConsigneesForSave(editConsignees);
      if (consigneeError) {
        setEditErr(consigneeError);
        return;
      }
      let latestOrder = null;
      if (isVendor && canVendorEditPendingItems) {
        const lineItemError = validateVendorLineItems(editLineItems);
        if (lineItemError) {
          setEditErr(lineItemError);
          return;
        }
        latestOrder = await ordersApi.update(id, {
          order_no: editForm.order_no?.trim() || null,
          order_date: editForm.order_date || null,
          customer_name: editForm.customer_name || null,
          customer_contact: editForm.customer_contact || null,
          customer_email: editForm.customer_email || null,
          customer_city: editForm.customer_city || null,
          customer_state: editForm.customer_state || null,
          customer_address: editForm.customer_address || null,
          consignee_addresses: serializeConsigneesForApi(editConsignees),
          expected_delivery_date: editForm.expected_delivery_date || null,
        });
        await ordersApi.replaceVendorLineItems(id, {
          items: serializeVendorLineItems(editLineItems),
        });
      } else {
      if (
        isVendor
        && editForm.status === "Pending"
        && Boolean((order?.oem_bill_no || "").trim())
        && VENDOR_LOCKED_SHIPMENT_STATUSES.has(order?.status)
      ) {
        setEditErr("Cannot set status back to Pending after the order is shipped or in transit with an OEM bill.");
        return;
      }
      const body = isVendor
        ? {
            lrn_no: editForm.lrn_no || null,
            vendor_bill_no: editForm.vendor_bill_no || null,
            vendor_bill_date: editForm.vendor_bill_date || null,
            status: editForm.status,
            expected_delivery_date: editForm.expected_delivery_date || null,
            actual_delivery_date: editForm.actual_delivery_date || null,
          }
        : {
            oem_bill_no: editForm.oem_bill_no || null,
            vendor_id: editForm.vendor_id !== "" ? Number(editForm.vendor_id) : null,
            customer_name: editForm.customer_name || null,
            customer_contact: editForm.customer_contact || null,
            customer_email: editForm.customer_email || null,
            customer_city: editForm.customer_city || null,
            customer_state: editForm.customer_state || null,
            customer_address: editForm.customer_address || null,
            consignee_addresses: serializeConsigneesForApi(editConsignees),
            courier_id: editForm.courier_id !== "" ? Number(editForm.courier_id) : null,
            lrn_no: editForm.lrn_no || null,
            vendor_bill_no: editForm.vendor_bill_no || null,
            vendor_bill_date: editForm.vendor_bill_date || null,
            status: editForm.status,
            expected_delivery_date: editForm.expected_delivery_date || null,
            actual_delivery_date: editForm.actual_delivery_date || null,
            items: (editForm.items || []).map((item) => ({
              id: item.id,
              item_code: item.item_code?.trim() || null,
            })),
          };
      latestOrder = await ordersApi.update(id, body);
      }
      if (latestOrder) {
        setOrder(latestOrder);
      }
      setEditing(false);
      await load();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setEditErr(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || "Failed to save"
      );
    } finally {
      setEditSaving(false);
    }
  }

  const canEditOrder = canUpdateOrder || isVendorShippedOrder || isVendorPendingOrder;
  const canVendorEditPendingDetails = canVendorEditPendingItems;
  const vendorBlockedPendingStatus = isVendor
    && Boolean((order?.oem_bill_no || "").trim())
    && VENDOR_LOCKED_SHIPMENT_STATUSES.has(order?.status);
  const vendorStatusOptions = vendorBlockedPendingStatus
    ? ORDER_STATUSES.filter((status) => status !== "Pending")
    : ORDER_STATUSES;
  const orderDocumentUrl = buildFileUrl(order?.order_file_path);

  if (err) {
    return (
      <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
    );
  }
  if (!order) {
    return <div className="text-slate-500">Loading...</div>;
  }

  const itemGroups = groupedItems(order.items || []);
  const lineItemSummaryText = (() => {
    const totals = new Map();
    let totalItems = 0;
    (order.items || []).forEach((item) => {
      const qty = Number(item.item_qty) || 0;
      const label = (item.item_name || item.item_code || "Unassigned").trim();
      totalItems += qty;
      totals.set(label, (totals.get(label) || 0) + qty);
    });
    const parts = [`Total Items: ${totalItems}`];
    Array.from(totals.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .forEach(([label, qty]) => {
        parts.push(`${label}: ${qty}`);
      });
    return parts.join(" | ");
  })();
  const existingSerialOwners = new Map();
  const existingItemsById = new Map();
  (order.items || []).forEach((item) => {
    existingItemsById.set(String(item.id), item);
    [item.serial_no, item.serial_no_2].forEach((serial) => {
      const normalized = normalizeSerial(serial);
      if (!normalized) return;
      if (!existingSerialOwners.has(normalized)) {
        existingSerialOwners.set(normalized, new Set());
      }
      existingSerialOwners.get(normalized).add(String(item.id));
    });
  });

  const previewRowsWithDuplicates = (importPreview?.rows || []).map((row) => {
    const rowId = (row.cells["ID"] || "").trim();
    const reasons = [];
    const existingItem = existingItemsById.get(rowId);

    if (!existingItem) {
      reasons.push(`Order item ${rowId || "-"} was not found on this order`);
    } else if (importPreview?.itemCode && (existingItem.item_code || "") !== importPreview.itemCode) {
      reasons.push(
        `Order item ${rowId} belongs to item code ${existingItem.item_code || "UNASSIGNED"}, but this import is for item code ${importPreview.itemCode}`
      );
    }

    const serialCount = Number(existingItem?.serial_count ?? 1);

    const rowSerials = serialColumnsForCount(Math.max(serialCount, importPreview?.serialColumnCount ?? 0))
      .map((column) => normalizeSerial(row.cells[column]))
      .filter(Boolean);

    if (serialCount >= 1 && !normalizeSerial(row.cells["Serial Number 1"])) {
      reasons.push("Serial Number 1 is required for this item code");
    }
    if (serialCount >= 2 && !normalizeSerial(row.cells["Serial Number 2"])) {
      reasons.push("Serial Number 2 is required for this item code (2 serials per unit)");
    }
    if (serialCount < 2 && normalizeSerial(row.cells["Serial Number 2"])) {
      reasons.push("Serial Number 2 is not used for this item code");
    }

    rowSerials.forEach((serial) => {
      const occursInPreview = (importPreview?.rows || []).filter((candidate) => (
        serialColumnsForCount(Math.max(serialCount, importPreview?.serialColumnCount ?? 0))
          .map((column) => normalizeSerial(candidate.cells[column]))
          .includes(serial)
      )).length;

      if (occursInPreview > 1) {
        reasons.push(`Duplicate serial in import: ${serial}`);
      }

      const owners = existingSerialOwners.get(serial);
      if (owners) {
        const otherOwners = Array.from(owners).filter((ownerId) => ownerId !== rowId);
        if (otherOwners.length > 0) {
          reasons.push(`Serial already exists in order: ${serial}`);
        }
      }
    });

    if (serialCount >= 2 && rowSerials.length !== new Set(rowSerials).size) {
      reasons.push("Serial Number 1 and Serial Number 2 cannot be the same");
    }

    return {
      ...row,
      duplicateReasons: Array.from(new Set(reasons)),
    };
  });
  const previewSerialColumns = serialColumnsForCount(importPreview?.serialColumnCount ?? 0);
  const previewHasIssues = previewRowsWithDuplicates.some((row) => row.duplicateReasons.length > 0);
  const previewHasRows = (importPreview?.rows?.length || 0) > 0;
  // API allows vendors to submit serials on their own orders (_can_submit_serials) without orders.can_edit.
  const canSubmitInstallationRequest = Boolean(
    (canUpdateOrder || isVendor)
    && order?.status === "Delivered"
    && (order?.oem_bill_no || "").trim(),
  );
  const selectedSubmitItemCodes = Array.from(selectedSerials).reduce((codes, key) => {
    const [itemIdStr] = key.split("-");
    const item = (order?.items || []).find((candidate) => String(candidate.id) === itemIdStr);
    if (item) codes.add(normalizeItemCode(item.item_code));
    return codes;
  }, new Set());
  const selectedSubmitItemCode = selectedSubmitItemCodes.size === 1 ? Array.from(selectedSubmitItemCodes)[0] : null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/orders" className="text-sm text-brand-600 hover:underline">
            {"<- Back to Orders"}
          </Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-3 text-2xl font-semibold text-slate-800">
            <span className="font-mono">{order.order_no}</span>
            <StatusBadge value={order.status} />
          </h1>
        </div>
        {canEditOrder && (
          <button
            onClick={openEdit}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {isVendor && canVendorEditShippedFields ? "Update LRN / Bill" : "Edit Order"}
          </button>
        )}
      </div>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Order Details
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field label="Order Date" value={fmtDate(order.order_date)} />
          <Field label="OEM Bill No" value={order.oem_bill_no} />
          <Field label="Status" value={order.status} />
          <Field label="Customer" value={order.customer_name} />
          <Field label="Consignee (ship-to)" value={consigneeSummaryLine(order.consignee_addresses)} />
          <Field label="Courier" value={order.courier_name} />
          <Field label="LRN No" value={order.lrn_no} mono />
          <Field label="Vendor Bill No" value={order.vendor_bill_no} />
          <Field label="Vendor Bill Date" value={fmtDate(order.vendor_bill_date)} />
          <Field label="Expected Delivery" value={fmtDate(order.expected_delivery_date)} />
          <Field label="Actual Delivery" value={fmtDate(order.actual_delivery_date)} />
          <Field label="Created At" value={fmtDateTime(order.created_at)} />
          <Field label="Updated At" value={fmtDateTime(order.updated_at)} />
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Order Document
        </h2>
        {orderDocumentUrl ? (
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={orderDocumentUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              View Document
            </a>
            <a
              href={orderDocumentUrl}
              download={fileNameFromPath(order.order_file_path)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Download Document
            </a>
            <span className="text-xs text-slate-500">{order.order_file_path}</span>
          </div>
        ) : (
          <p className="text-sm text-slate-400">No document uploaded for this order.</p>
        )}
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Customer Information
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Customer Name" value={order.customer_name} />
          <Field label="Contact" value={order.customer_contact} mono />
          <Field label="Email" value={order.customer_email} />
          <Field label="City" value={order.customer_city} />
          <Field label="State" value={order.customer_state} />
          <Field label="Address" value={order.customer_address} full />
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm" id="order-consignee-addresses">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-sky-900">
          Consignee addresses
        </h2>
        <p className="mb-4 text-xs text-slate-500">
          Additional delivery locations besides the primary customer address above.
        </p>
        {(order.consignee_addresses || []).length === 0 ? (
          <p className="text-sm text-slate-500">
            No consignee addresses on this order yet. Use <strong>Edit Order</strong> to add ship-to locations.
          </p>
        ) : (
          <div className="space-y-6">
            {order.consignee_addresses.map((row, idx) => (
              <div
                key={row.id || idx}
                className="rounded-md border border-sky-100 bg-sky-50/40 p-4"
              >
                <div className="mb-3 text-sm font-medium text-sky-900">
                  Consignee {order.consignee_addresses.length > 1 ? idx + 1 : ""}
                  {row.consignee_name ? ` — ${row.consignee_name}` : ""}
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Consignee name" value={row.consignee_name} />
                  <Field label="Contact" value={row.contact} mono />
                  <Field label="Email" value={row.email} />
                  <Field label="City" value={row.city} />
                  <Field label="State" value={row.state} />
                  <Field label="Address" value={row.address} full />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-semibold text-slate-800">
                Line Items
              </h2>
              <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-semibold text-blue-700">
                {order.items?.length ?? 0}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-500">Items are grouped by Item Code</p>
            <p className="mt-1 text-sm text-slate-600">{lineItemSummaryText}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className={`rounded-full px-3 py-1 text-xs font-medium ${canManageItemCsv ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>
              {canManageItemCsv ? "Role: Incool Admin" : "Import/Export only for Admin"}
            </div>
            {canManageItemCsv && (
              <div className="flex gap-2">
                <label className={`cursor-pointer rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 ${csvBusy ? "pointer-events-none opacity-50" : ""}`}>
                  Import CSV
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    className="hidden"
                    onChange={(e) => {
                      handleImport(e.target.files?.[0] || null);
                      e.target.value = "";
                    }}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => handleExport()}
                  disabled={csvBusy}
                  className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  Export CSV
                </button>
              </div>
            )}
          </div>
        </div>

        {(!order.items || order.items.length === 0) ? (
          <p className="text-sm text-slate-400">No line items on this order.</p>
        ) : (
          <div className="space-y-4">
            {itemGroups.map((group) => (
              <div key={group.itemCode || "UNASSIGNED"} className="overflow-hidden rounded-xl border border-blue-100 bg-white shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-blue-100 bg-gradient-to-r from-blue-50 to-white px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggleItemGroup(group.itemCode || "UNASSIGNED")}
                    className="flex flex-wrap items-center gap-3 text-left text-sm"
                  >
                    <span className="text-slate-500">⌄</span>
                    <span className="text-slate-500">{collapsedItemGroups[group.itemCode || "UNASSIGNED"] ? ">" : "v"}</span>
                    <span className="font-semibold text-slate-800">Item Code:</span>
                    <span className="font-mono text-base font-semibold text-slate-900">{group.itemCode || "-"}</span>
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">{group.rows.length}</span>
                    <span className="border-l border-slate-200 pl-3 text-slate-600">{group.itemName || "Unnamed Item"}</span>
                  </button>
                  {canManageItemCsv && (
                    <div className="flex gap-2">
                      <label className={`cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 ${csvBusy ? "pointer-events-none opacity-50" : ""}`}>
                        Import CSV
                        <input
                          type="file"
                          accept=".csv,text/csv"
                          className="hidden"
                          onChange={(e) => {
                            handleImport(e.target.files?.[0] || null, group.itemCode);
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => handleExport(group.itemCode)}
                        disabled={csvBusy}
                        className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        Export CSV
                      </button>
                    </div>
                  )}
                </div>
                {!collapsedItemGroups[group.itemCode || "UNASSIGNED"] && <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50 text-left text-slate-600">
                      <tr>
                        {!isVendor && (
                          <th className="px-3 py-2">
                            {(() => {
                              const instIds = installationIdsSelectableInGroup(group);
                              if (!instIds.length) return null;
                              const allSelected = instIds.every((id) => selectedInstIds.has(id));
                              return (
                                <input
                                  type="checkbox"
                                  title="Select all submitted rows for engineer assignment"
                                  checked={allSelected}
                                  onChange={() => toggleSelectAllInstallationsInGroup(group)}
                                  className="h-4 w-4"
                                />
                              );
                            })()}
                          </th>
                        )}
                        <th className="px-3 py-2">#</th>
                        <th className="px-3 py-2">Item Name</th>
                        <th className="px-3 py-2">Item Code</th>
                        <th className="px-3 py-2">
                          {canSubmitInstallationRequest && serialSelectionKeysForGroup(group, "serial1").length > 0 ? (
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                title="Select all serials in this item code group"
                                checked={serialSelectionKeysForGroup(group, "serial1").every((key) => selectedSerials.has(key))}
                                onChange={() => toggleSelectAllSerialsInGroup(group, "serial1")}
                                className="h-4 w-4"
                              />
                              <span>Serial 1 <span className="text-xs">(select)</span></span>
                            </div>
                          ) : (
                            <>Serial 1 {canSubmitInstallationRequest && <span className="text-xs">(select)</span>}</>
                          )}
                        </th>
                        {group.serialCount >= 2 && (
                          <th className="px-3 py-2">
                            {canSubmitInstallationRequest && serialSelectionKeysForGroup(group, "serial2").length > 0 ? (
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  title="Select all serial 2 values in this item code group"
                                  checked={serialSelectionKeysForGroup(group, "serial2").every((key) => selectedSerials.has(key))}
                                  onChange={() => toggleSelectAllSerialsInGroup(group, "serial2")}
                                  className="h-4 w-4"
                                />
                                <span>Serial 2 <span className="text-xs">(select)</span></span>
                              </div>
                            ) : (
                              <>Serial 2 {canSubmitInstallationRequest && <span className="text-xs">(select)</span>}</>
                            )}
                          </th>
                        )}
                        <th className="px-3 py-2">PCB Warranty</th>
                        <th className="px-3 py-2">Component Warranty</th>
                        <th className="px-3 py-2">Machine Warranty</th>
                        <th className="px-3 py-2 text-center">Free Services</th>
                        <th className="px-3 py-2">Installation Status</th>
                        {!isVendor && <th className="px-3 py-2">Assigned Engineer</th>}
                        {!isVendor && <th className="px-3 py-2 text-right">Installation</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                {group.rows.map((item, idx) => {
                  const inst = !isVendor ? installationForItem(item) : null;
                  const selectable = inst && (inst.status === "Submitted" || inst.status === "Assigned");
                  const canProgress = inst && (inst.status === "Assigned" || WORK_STARTED_STATUSES.has(inst.status));
                  return (
                    <tr key={item.id} className="hover:bg-slate-50">
                      {!isVendor && (
                        <td className="px-3 py-2">
                          {selectable && (
                            <input
                              type="checkbox"
                              checked={selectedInstIds.has(inst.id)}
                              onChange={() => toggleInstSelected(inst)}
                              className="h-4 w-4"
                            />
                          )}
                        </td>
                      )}
                      <td className="px-3 py-2 text-slate-500">{idx + 1}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {item.item_name || <span className="text-slate-400">-</span>}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {item.item_code || <span className="text-slate-400">-</span>}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          {canSubmitInstallationRequest && item.serial_no ? (
                            <input
                              type="checkbox"
                              checked={selectedSerials.has(`${item.id}-serial1`)}
                              onChange={() => toggleSerial(item, "serial1")}
                              disabled={isItemLocked(item)}
                              className="h-4 w-4 disabled:cursor-not-allowed"
                            />
                          ) : null}
                          <span className="font-mono text-xs text-slate-700">
                            {item.serial_no || <span className="text-slate-400">-</span>}
                          </span>
                        </div>
                      </td>
                      {group.serialCount >= 2 && (
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            {canSubmitInstallationRequest && item.serial_no_2 ? (
                              <input
                                type="checkbox"
                                checked={selectedSerials.has(`${item.id}-serial2`)}
                                onChange={() => toggleSerial(item, "serial2")}
                                disabled={isItemLocked(item)}
                                className="h-4 w-4 disabled:cursor-not-allowed"
                              />
                            ) : null}
                            <span className="font-mono text-xs text-slate-700">
                              {item.serial_no_2 || <span className="text-slate-400">-</span>}
                            </span>
                          </div>
                        </td>
                      )}
                      <td className="px-3 py-2 whitespace-nowrap text-slate-600">
                        {item.pcb_warranty_years ? `${item.pcb_warranty_years} Years` : <span className="text-slate-400">-</span>}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-slate-600">
                        {item.component_warranty_years ? `${item.component_warranty_years} Years` : <span className="text-slate-400">-</span>}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-slate-600">
                        {item.machine_warranty_years ? `${item.machine_warranty_years} Years` : <span className="text-slate-400">-</span>}
                      </td>
                      <td className="px-3 py-2 text-center font-semibold text-slate-700">
                        {item.free_service_count === 0
                          ? "-"
                          : `${item.free_service_count} (${item.dry_free_service_count || 0} Dry / ${item.wet_free_service_count || 0} Wet)`}
                      </td>
                      <td className="px-3 py-2">
                        {inst && canViewInstallationRequest ? (
                          <Link
                            to={`/installations/${inst.id}?edit=1`}
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium underline-offset-2 hover:underline ${installationStatusClass(item, inst)}`}
                          >
                            {installationStatusLabel(item, inst)}
                          </Link>
                        ) : (
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${installationStatusClass(item, inst)}`}
                          >
                            {installationStatusLabel(item, inst)}
                          </span>
                        )}
                      </td>
                      {!isVendor && (
                        <td className="px-3 py-2">
                          {inst?.assigned_engineer_name || <span className="text-slate-400">-</span>}
                        </td>
                      )}
                      {!isVendor && (
                        <td className="px-3 py-2 text-right">
                          {inst && canViewInstallationRequest ? (
                            <div className="flex justify-end gap-2">
                              <Link
                                to={`/installations/${inst.id}?edit=1`}
                                className="rounded-md border border-sky-300 px-2 py-1 text-xs font-medium text-sky-700 hover:bg-sky-50"
                              >
                                View request
                              </Link>
                              {canProgress && (
                                <button
                                  onClick={() => openProgress(inst)}
                                  disabled={progressLoading}
                                  className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                >
                                  Progress
                                </button>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
                    </tbody>
                  </table>
                </div>}
              </div>
            ))}
          </div>
        )}

        {submitErr && (
          <div className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitErr}</div>
        )}
        {submitMsg && (
          <div className="mt-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">OK {submitMsg}</div>
        )}

        {!isVendor && (
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-brand-50 px-4 py-3">
            <span className="text-sm font-medium text-brand-700">
              {selectedInstIds.size > 0 ? `${selectedInstIds.size} row(s) selected` : "No rows selected"}
            </span>
            <select
              value={bulkEngineerPick}
              onChange={(e) => setBulkEngineerPick(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              disabled={bulkBusy || selectedInstIds.size === 0}
            >
              <option value="">- Choose engineer -</option>
              {engineers.map((eng) => (
                <option key={eng.id} value={eng.id}>{formatEngineerOptionLabel(eng)}</option>
              ))}
            </select>
            <span className="text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</span>
            <button
              onClick={bulkAssignSelected}
              disabled={bulkBusy || selectedInstIds.size === 0 || !bulkEngineerPick}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Assign
            </button>
            <button
              onClick={bulkCancelSelected}
              disabled={bulkBusy || selectedInstIds.size === 0}
              className="rounded-md border border-rose-300 px-3 py-1.5 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={() => setSelectedInstIds(new Set())}
              disabled={bulkBusy || selectedInstIds.size === 0}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            >
              Clear
            </button>
          </div>
        )}

        {!isVendor && instErr && (
          <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{instErr}</div>
        )}
        {!isVendor && instMsg && (
          <div className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">OK {instMsg}</div>
        )}
        {csvErr && (
          <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{csvErr}</div>
        )}
        {csvMsg && (
          <div className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">OK {csvMsg}</div>
        )}
        {!canManageItemCsv && (
          <div className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Import/Export is available only for admin and incool users.
          </div>
        )}

        {canSubmitInstallationRequest && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">
                {selectedSerials.size > 0 ? (
                  <span className="font-semibold text-brand-600">
                    {selectedSerials.size} serial(s) selected{selectedSubmitItemCode ? ` for item code ${selectedSubmitItemCode}` : ""}
                  </span>
                ) : (
                  <span className="text-slate-400">Select serials from one item code to submit for engineer assignment</span>
                )}
              </span>
              <button
                onClick={submitSelectedSerials}
                disabled={submitting || selectedSerials.size === 0 || selectedSubmitItemCodes.size > 1}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Submitting..." : `Submit (${selectedSerials.size})`}
              </button>
            </div>
          </div>
        )}
        {!canSubmitInstallationRequest && (
          <div className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {order.status !== "Delivered"
              ? `Installation requests can be raised only when the order is Delivered (current status: ${order.status}).`
              : !(order.oem_bill_no || "").trim()
                ? "OEM Bill No must be entered on this order before installation requests can be raised (typically set by Indcool/admin)."
                : "Installation request submission is not available for your role on this order."}
          </div>
        )}
      </section>

      <Modal
        open={editing}
        onClose={() => setEditing(false)}
        title={isVendor && canVendorEditPendingDetails ? "Edit Order" : isVendor ? "Update Shipping / Bill" : "Edit Order"}
        maxWidth={canVendorEditPendingDetails ? "max-w-5xl" : "max-w-2xl"}
      >
        <form onSubmit={saveEdit} className="space-y-4">
          {editErr && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{editErr}</div>
          )}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {canVendorEditPendingDetails && (
              <>
                <div>
                  <label className={labelClass}>Order No / GEM No</label>
                  <input
                    value={editForm.order_no}
                    onChange={(e) => setEF("order_no", e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Order Date</label>
                  <input
                    type="date"
                    value={editForm.order_date}
                    onChange={(e) => setEF("order_date", e.target.value)}
                    className={fieldClass}
                  />
                </div>
              </>
            )}
            <div>
              <label className={labelClass}>Status</label>
              {canVendorEditPendingDetails ? (
                <input value={editForm.status} readOnly className={`${fieldClass} bg-slate-50 text-slate-600`} />
              ) : (
                <select
                  value={editForm.status}
                  onChange={(e) => setEF("status", e.target.value)}
                  disabled={isVendor && !canVendorEditShippedFields && !order?.oem_bill_no}
                  className={fieldClass}
                >
                  {(isVendor && canVendorEditShippedFields ? vendorStatusOptions : ORDER_STATUSES).map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              )}
              {isVendor && !canVendorEditShippedFields && !canVendorEditPendingDetails && !order?.oem_bill_no && (
                <p className="mt-1 text-xs text-slate-400">Available after the OEM Bill is saved.</p>
              )}
              {vendorBlockedPendingStatus && (
                <p className="mt-1 text-xs text-amber-700">
                  Pending is not available once the order is shipped or in transit with an OEM bill.
                </p>
              )}
              {canVendorEditPendingDetails && (
                <p className="mt-1 text-xs text-slate-400">Status stays Pending until the order is shipped.</p>
              )}
            </div>
            <div>
              <label className={labelClass}>OEM Bill No</label>
              <input
                value={editForm.oem_bill_no}
                onChange={(e) => setEF("oem_bill_no", e.target.value)}
                disabled={isVendor || !canManageOemBill}
                className={fieldClass}
              />
              {isVendor && (
                <p className="mt-1 text-xs text-slate-400">OEM bill updates are restricted to admin or incool users.</p>
              )}
            </div>

            <div>
              <label className={labelClass}>Vendor</label>
              <select
                value={editForm.vendor_id}
                onChange={(e) => setEF("vendor_id", e.target.value)}
                disabled={isVendor}
                className={fieldClass}
              >
                <option value="">- None -</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Courier</label>
              <select
                value={editForm.courier_id}
                onChange={(e) => setEF("courier_id", e.target.value)}
                disabled={isVendor}
                className={fieldClass}
              >
                <option value="">- None -</option>
                {couriers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Customer Name</label>
              <input
                value={editForm.customer_name}
                onChange={(e) => setEF("customer_name", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Contact</label>
              <input
                value={editForm.customer_contact}
                onChange={(e) => setEF("customer_contact", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer Email</label>
              <input
                type="email"
                value={editForm.customer_email}
                onChange={(e) => setEF("customer_email", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer City</label>
              <input
                value={editForm.customer_city}
                onChange={(e) => setEF("customer_city", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Customer State</label>
              <select
                value={editForm.customer_state}
                onChange={(e) => setEF("customer_state", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              >
                <option value="">- Select -</option>
                {INDIAN_STATES_UTS.map((state) => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className={labelClass}>Customer Address</label>
              <textarea
                rows={2}
                value={editForm.customer_address}
                onChange={(e) => setEF("customer_address", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails}
                className={fieldClass}
              />
            </div>

            {(!isVendor || canVendorEditPendingDetails) && (
              <div className="md:col-span-2 space-y-4 border-t border-slate-200 pt-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-sky-900">Consignee addresses</span>
                  <button
                    type="button"
                    onClick={() => setEditConsignees((prev) => [...prev, { ...BLANK_CONSIGNEE }])}
                    className="text-sm font-medium text-brand-700 hover:text-brand-900"
                  >
                    + Add consignee
                  </button>
                </div>
                {editConsignees.map((row, idx) => (
                  <div key={`edit-consignee-${idx}`} className="rounded-md border border-sky-100 bg-sky-50/30 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-medium uppercase text-sky-800">
                        Consignee {editConsignees.length > 1 ? idx + 1 : ""}
                      </span>
                      <button
                        type="button"
                        onClick={() => setEditConsignees((prev) => prev.filter((_, i) => i !== idx))}
                        className="text-xs text-rose-600"
                      >
                        Remove
                      </button>
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <input
                        placeholder="Consignee name"
                        value={row.consignee_name}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, consignee_name: e.target.value } : r)))}
                        className={fieldClass}
                      />
                      <input
                        placeholder="Contact"
                        value={row.contact}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, contact: e.target.value } : r)))}
                        className={fieldClass}
                      />
                      <input
                        placeholder="Email"
                        value={row.email}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, email: e.target.value } : r)))}
                        className={fieldClass}
                      />
                      <input
                        placeholder="City"
                        value={row.city}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, city: e.target.value } : r)))}
                        className={fieldClass}
                      />
                      <select
                        value={row.state}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, state: e.target.value } : r)))}
                        className={fieldClass}
                      >
                        <option value="">State</option>
                        {INDIAN_STATES_UTS.map((state) => (
                          <option key={state} value={state}>{state}</option>
                        ))}
                      </select>
                      <textarea
                        rows={2}
                        placeholder="Consignee address"
                        value={row.address}
                        onChange={(e) => setEditConsignees((prev) => prev.map((r, i) => (i === idx ? { ...r, address: e.target.value } : r)))}
                        className={`${fieldClass} md:col-span-2`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div>
              <label className={labelClass}>Expected Delivery Date</label>
              <input
                type="date"
                value={editForm.expected_delivery_date}
                onChange={(e) => setEF("expected_delivery_date", e.target.value)}
                disabled={isVendor && !canVendorEditPendingDetails && !canVendorEditShippedFields}
                className={fieldClass}
              />
            </div>

            {!canVendorEditPendingDetails && (
              <>
            <div>
              <label className={labelClass}>LRN No</label>
              <input
                value={editForm.lrn_no}
                onChange={(e) => setEF("lrn_no", e.target.value)}
                disabled={isVendor && !canVendorEditShippedFields}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Vendor Bill No</label>
              <input
                value={editForm.vendor_bill_no}
                onChange={(e) => setEF("vendor_bill_no", e.target.value)}
                disabled={isVendor && !canVendorEditShippedFields}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Vendor Bill Date</label>
              <input
                type="date"
                value={editForm.vendor_bill_date}
                onChange={(e) => setEF("vendor_bill_date", e.target.value)}
                disabled={isVendor && !canVendorEditShippedFields}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Actual Delivery Date</label>
              <input
                type="date"
                value={editForm.actual_delivery_date}
                onChange={(e) => setEF("actual_delivery_date", e.target.value)}
                disabled={isVendor && !canVendorEditShippedFields}
                className={fieldClass}
              />
            </div>
              </>
            )}
          </div>

          {isVendor && canVendorEditPendingDetails && (
            <div className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
              Update order details, customer information, and line items while the order is still Pending.
            </div>
          )}

          {canVendorEditPendingDetails && (
            <VendorOrderLineItemsEditor
              lineItems={editLineItems}
              setLineItems={setEditLineItems}
              itemOptions={itemOptions}
            />
          )}

          {isVendor && canVendorEditShippedFields && (
            <div className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
              After the order is shipped, you can update LRN No, Vendor Bill No, Vendor Bill Date, delivery status, and delivery dates here.
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={editSaving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {editSaving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>

      {progressTarget && (
        <InstallationStatusEdit
          installation={progressTarget}
          onClose={() => setProgressTarget(null)}
          onSaved={() => {
            setProgressTarget(null);
            loadInstallations();
          }}
        />
      )}

      <Modal
        open={!!importPreview}
        onClose={closeImportPreview}
        title={importPreview?.itemCode ? `Review Import: ${importPreview.itemCode}` : "Review Import"}
        maxWidth="max-w-6xl"
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-slate-700">
                Review imported rows before saving. Duplicate serial rows are highlighted in red and must be removed.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Save is available only for admin and incool users.
              </p>
            </div>
            <div className="text-sm text-slate-600">
              {importPreview?.rows.length ?? 0} row(s)
            </div>
          </div>

          {csvErr && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {csvErr}
            </div>
          )}
          {csvMsg && (
            <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
              {csvMsg}
            </div>
          )}

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-3 py-2">CSV Row</th>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Item Name</th>
                  <th className="px-3 py-2">Item Code</th>
                  {previewSerialColumns.map((column) => (
                    <th key={column} className="px-3 py-2">{column}</th>
                  ))}
                  <th className="px-3 py-2">Issue</th>
                  <th className="px-3 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {previewRowsWithDuplicates.map((row) => {
                  const hasDuplicate = row.duplicateReasons.length > 0;
                  return (
                    <tr
                      key={row.previewId}
                      className={hasDuplicate ? "bg-rose-50" : "bg-white"}
                    >
                      <td className="px-3 py-2 text-slate-500">{row.rowNumber}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-700">{row.cells["ID"] || "-"}</td>
                      <td className="px-3 py-2 text-slate-700">{row.cells["Item Name"] || "-"}</td>
                      <td className="px-3 py-2 font-mono text-slate-700">{row.cells["Item Code"] || "-"}</td>
                      {previewSerialColumns.map((column) => (
                        <td key={column} className="px-3 py-2 font-mono text-xs text-slate-700">
                          {row.cells[column] || "-"}
                        </td>
                      ))}
                      <td className="px-3 py-2">
                        {hasDuplicate ? (
                          <span className="text-xs font-medium text-rose-700">
                            {row.duplicateReasons.join("; ")}
                          </span>
                        ) : (
                          <span className="text-xs text-green-700">Ready</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => removePreviewRow(row.previewId)}
                          disabled={csvBusy}
                          className="rounded-md border border-rose-200 px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {previewRowsWithDuplicates.length === 0 && (
                  <tr>
                    <td colSpan={6 + previewSerialColumns.length} className="px-3 py-6 text-center text-slate-500">
                      No rows found in the import file.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {previewRowsWithDuplicates.some((row) => row.duplicateReasons.length > 0) && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
              Remove all red rows before saving this import.
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={closeImportPreview}
              onMouseDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              onPointerUp={(e) => e.stopPropagation()}
              disabled={csvBusy}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              onPointerUp={(e) => e.stopPropagation()}
              onClick={() => { void saveImportPreview(); }}
              disabled={csvBusy || previewHasIssues || !previewHasRows || !canManageItemCsv}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {csvBusy ? "Saving..." : "Save Import"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
