import { useEffect, useMemo, useState } from "react";
import { servicesApi } from "../../api/services.js";
import WarrantyBadge from "../../components/WarrantyBadge.jsx";
import { formatApiError } from "../../utils/apiError.js";
import { ENGINEER_ASSIGNMENT_HINT, formatEngineerOptionLabel } from "../../utils/engineerAssignment.js";
import EngineerSelect from "../../components/EngineerSelect.jsx";

function serialCell(value) {
  return value ? <span className="font-mono text-xs">{value}</span> : <span className="text-slate-400">—</span>;
}

export default function ServiceUnitAssignmentPanel({
  service,
  engineers,
  isServiceTeam,
  isEngineer,
  onRefresh,
  run,
  workflowUnlocked = true,
  pendingOrderVerifyNo = "",
  onServiceUpdated,
  parentBusy = false,
}) {
  const [orderVerifyInput, setOrderVerifyInput] = useState(service?.order_no || "");
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [verifyErr, setVerifyErr] = useState("");
  const [orderSearchResults, setOrderSearchResults] = useState([]);
  const [selectedItemCode, setSelectedItemCode] = useState("");
  const [selectedUnitIds, setSelectedUnitIds] = useState(new Set());
  const [assignEngineerId, setAssignEngineerId] = useState("");
  const [assignBillingType, setAssignBillingType] = useState("Free");
  const [assignRemarks, setAssignRemarks] = useState("");
  const orderItems = service?.order_items || [];
  const allUnits = service?.units || [];
  const orderVerified = (orderItems.length > 0)
    || (allUnits.length > 0 && Boolean(service?.order_id));

  useEffect(() => {
    if (orderVerified && service?.order_no) {
      setOrderVerifyInput(service.order_no);
      return;
    }
    if (!orderVerified) {
      setSelectedItemCode("");
      setSelectedUnitIds(new Set());
    }
  }, [service?.id, service?.order_id, service?.order_no, orderVerified]);

  useEffect(() => {
    const next = (pendingOrderVerifyNo || "").trim();
    if (next) setOrderVerifyInput(next);
  }, [pendingOrderVerifyNo]);

  useEffect(() => {
    const search = orderVerifyInput.trim();
    if (!search || orderVerified) {
      setOrderSearchResults([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      servicesApi.searchCustomers({
        mobile: search,
        name: search,
        order_no: search,
        serial: search,
      })
        .then((results) => setOrderSearchResults((results || []).filter((result) => result.order_id)))
        .catch(() => setOrderSearchResults([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [orderVerifyInput, orderVerified]);

  const visibleUnits = useMemo(() => {
    if (!selectedItemCode) return [];
    return allUnits.filter((unit) => unit.item_code === selectedItemCode);
  }, [allUnits, selectedItemCode]);

  const engineerUnits = useMemo(() => {
    if (!isEngineer) return [];
    return allUnits;
  }, [allUnits, isEngineer]);

  const engineerGroups = useMemo(() => {
    const map = new Map();
    engineerUnits.forEach((unit) => {
      const key = unit.item_code || "UNASSIGNED";
      if (!map.has(key)) {
        map.set(key, {
          item_code: unit.item_code,
          item_name: unit.item_name,
          serial_count: unit.serial_count,
          serial_labels: unit.serial_labels || [],
          units: [],
        });
      }
      map.get(key).units.push(unit);
    });
    return Array.from(map.values());
  }, [engineerUnits]);

  const selectedItem = orderItems.find((item) => item.item_code === selectedItemCode);
  const unassignedVisible = visibleUnits.filter((unit) => !unit.assigned_engineer_id);
  const allUnassignedSelected = unassignedVisible.length > 0
    && unassignedVisible.every((unit) => selectedUnitIds.has(unit.id));

  function toggleUnit(unitId) {
    setSelectedUnitIds((current) => {
      const next = new Set(current);
      if (next.has(unitId)) next.delete(unitId);
      else next.add(unitId);
      return next;
    });
  }

  function toggleSelectAllUnassigned() {
    if (allUnassignedSelected) {
      setSelectedUnitIds(new Set());
      return;
    }
    setSelectedUnitIds(new Set(unassignedVisible.map((unit) => unit.id)));
  }

  async function verifyOrder() {
    const trimmed = orderVerifyInput.trim();
    if (!trimmed || orderVerified || verifyBusy || parentBusy) return;
    const body = /^\d+$/.test(trimmed) ? { order_id: Number(trimmed) } : { order_no: trimmed };
    if (service?.serial_no?.trim() && service?.order_item_id) {
      body.serial_no = service.serial_no.trim();
    }
    setVerifyBusy(true);
    setVerifyErr("");
    try {
      const updated = await servicesApi.verifyOrder(service.id, body);
      onServiceUpdated?.(updated);
      await onRefresh?.();
      const orderLabel = updated?.order_no || trimmed;
      const unitCount = updated?.units?.length ?? 0;
      window.alert(
        `Order ${orderLabel} is verified.\n\n${unitCount} installed unit(s) loaded. Use the table below to assign engineers.`,
      );
      setSelectedItemCode("");
      setSelectedUnitIds(new Set());
    } catch (error) {
      const message = formatApiError(error, "Order verification failed");
      setVerifyErr(message);
      window.alert(message);
    } finally {
      setVerifyBusy(false);
      window.requestAnimationFrame(() => {
        document.getElementById("service-order-items-table")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  async function assignSelectedUnits() {
    if (!assignEngineerId || selectedUnitIds.size === 0) return;
    const engineer = engineers.find((row) => String(row.id) === String(assignEngineerId));
    await run(
      () => servicesApi.assignUnits(service.id, {
        unit_ids: Array.from(selectedUnitIds),
        engineer_id: Number(assignEngineerId),
        remarks: assignRemarks || null,
        billing_type: assignBillingType,
      }),
      { successMessage: `Assigned ${selectedUnitIds.size} unit(s) to ${engineer?.name || "engineer"}.` },
    );
    setSelectedUnitIds(new Set());
    setAssignRemarks("");
    onRefresh?.();
  }

  if (isEngineer) {
    return (
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">Your assigned units</h2>
        {engineerGroups.length === 0 ? (
          <p className="text-sm text-slate-500">No units assigned to you on this service request yet.</p>
        ) : (
          <div className="space-y-4">
            {engineerGroups.map((group) => (
              <div key={group.item_code} className="rounded-md border border-slate-200">
                <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm">
                  <div className="font-medium text-slate-800">{group.item_code} — {group.item_name}</div>
                  <div className="text-slate-500">Assigned quantity: {group.units.length}</div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-100 text-left text-slate-700">
                      <tr>
                        <th className="px-3 py-2">#</th>
                        {(group.serial_labels.length ? group.serial_labels : ["Serial Number"]).map((label) => (
                          <th key={label} className="px-3 py-2">{label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {group.units.map((unit, idx) => (
                        <tr key={unit.id}>
                          <td className="px-3 py-2">{idx + 1}</td>
                          {(unit.serial_values?.length ? unit.serial_values : [unit.serial_no]).map((value, colIdx) => (
                            <td key={colIdx} className="px-3 py-2">{serialCell(value)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (!isServiceTeam) return null;

  return (
    <section className="rounded-lg bg-white p-6 shadow-sm space-y-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Order verify & unit assignment</h2>

      {!workflowUnlocked && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Approve customer documents above before verifying the order or assigning units to engineers.
          {service.status === "Admin Review Document" && (
            <span className="mt-1 block">Current status: <strong>Admin Review Document</strong></span>
          )}
        </div>
      )}

      {workflowUnlocked && service.serial_no && service.order_item_id && (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
          Customer serial linked: <span className="font-mono font-medium">{service.serial_no}</span>.
          {" "}Order verification will load only this serial from the order (not all units).
        </div>
      )}
      {workflowUnlocked && service.serial_no && !service.order_item_id && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          Request serial on file: <span className="font-mono font-medium">{service.serial_no}</span>.
          {" "}Verify order loads <strong>all installed units</strong> on the order (not filtered to this serial unless already linked to a line).
        </div>
      )}

      <div className={`grid gap-3 md:grid-cols-[1fr_auto] ${!workflowUnlocked ? "opacity-50 pointer-events-none" : ""}`}>
        <input
          value={orderVerifyInput}
          onChange={(e) => {
            setOrderVerifyInput(e.target.value);
            setOrderSearchResults([]);
          }}
          placeholder="Search name, order number, mobile, or serial number"
          disabled={orderVerified}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500"
        />
        <button
          type="button"
          onClick={verifyOrder}
          disabled={orderVerified || verifyBusy || parentBusy || !orderVerifyInput.trim()}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {orderVerified ? "Order verified" : verifyBusy ? "Verifying…" : "Verify Order"}
        </button>
      </div>
      {verifyErr && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{verifyErr}</p>
      )}

      {workflowUnlocked && !orderVerified && orderSearchResults.length > 0 && (
        <div className="-mt-2 space-y-2 rounded-md border border-slate-200 bg-white p-2 shadow-sm">
          {orderSearchResults.map((result) => (
            <div
              key={`${result.order_id}-${result.order_no}`}
              className="flex flex-col gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm hover:bg-sky-50 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <a
                  href={`/orders/${result.order_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-sky-700 underline underline-offset-2 hover:text-sky-900"
                >
                  Order {result.order_no || `#${result.order_id}`}
                </a>
                <span className="ml-2 text-slate-500">
                  {[result.customer_name, result.customer_mobile].filter(Boolean).join("  ")}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setOrderVerifyInput(result.order_no || String(result.order_id));
                  setOrderSearchResults([]);
                }}
                className="self-start rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-white sm:self-auto"
              >
                Use for verify
              </button>
            </div>
          ))}
        </div>
      )}

      {orderVerified && service.order_id && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Order verified and linked
          <span>
            {" — "}
            <a
              href={`/orders/${service.order_id}`}
              target="_blank"
              rel="noreferrer"
              className="font-mono font-medium text-emerald-900 underline underline-offset-2 hover:text-emerald-700"
            >
              {service.order_no || `order #${service.order_id}`}
            </a>
          </span>
          {isServiceTeam && service.status === "Service Team Review" && (
            <div className="mt-2 border-t border-emerald-200 pt-2 text-amber-900">
              <p className="text-xs">
                This order was linked in an earlier pass. Clear it to continue step by step from document review.
              </p>
              <button
                type="button"
                className="mt-2 rounded-md border border-amber-400 bg-white px-3 py-1.5 text-xs font-medium text-amber-900 hover:bg-amber-50"
                onClick={() => {
                  if (!window.confirm(
                    "Clear order verification and engineer assignment for this step? Customer documents will stay approved.",
                  )) {
                    return;
                  }
                  run(
                    () => servicesApi.restartTeamReview(service.id),
                    { successMessage: "Service team review restarted. Verify the order again, then assign the engineer." },
                  ).then(() => onRefresh?.());
                }}
              >
                Clear order and continue step by step
              </button>
            </div>
          )}
        </div>
      )}

      {workflowUnlocked && service.order_no && !orderVerified && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Linked order:{" "}
          {service.order_id ? (
            <a
              href={`/orders/${service.order_id}`}
              target="_blank"
              rel="noreferrer"
              className="font-mono font-medium text-emerald-900 underline underline-offset-2 hover:text-emerald-700"
            >
              {service.order_no}
            </a>
          ) : (
            <span className="font-mono">{service.order_no}</span>
          )}
        </div>
      )}

      {workflowUnlocked && (
        <p className="text-sm text-slate-600">
          Only serial numbers with <strong>completed installation</strong> are eligible for service assignment.
        </p>
      )}

      {workflowUnlocked && orderItems.length > 0 && (
        <div id="service-order-items-table" className="overflow-x-auto rounded-md border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-700">
              <tr>
                <th className="px-3 py-2">Item Code</th>
                <th className="px-3 py-2">Item Name</th>
                <th className="px-3 py-2">Order Qty</th>
                <th className="px-3 py-2">Installed</th>
                <th className="px-3 py-2">Pending Install</th>
                <th className="px-3 py-2">Service Eligible</th>
                <th className="px-3 py-2">Assigned</th>
                <th className="px-3 py-2">Unassigned</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orderItems.map((item) => (
                <tr key={item.id} className={selectedItemCode === item.item_code ? "bg-sky-50" : ""}>
                  <td className="px-3 py-2 font-mono text-xs">{item.item_code}</td>
                  <td className="px-3 py-2">{item.item_name || "—"}</td>
                  <td className="px-3 py-2 text-center">{item.ordered_quantity}</td>
                  <td className="px-3 py-2 text-center">{item.installed_quantity ?? item.units_count}</td>
                  <td className="px-3 py-2 text-center">{item.pending_installation_quantity ?? 0}</td>
                  <td className="px-3 py-2 text-center">{item.units_count}</td>
                  <td className="px-3 py-2 text-center">{item.assigned_count}</td>
                  <td className="px-3 py-2 text-center">{item.unassigned_count}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      disabled={(item.units_count ?? 0) === 0}
                      onClick={() => {
                        setSelectedItemCode(item.item_code);
                        setSelectedUnitIds(new Set());
                      }}
                      className="rounded-md border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50"
                    >
                      View units
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedItemCode && (
        <div className="space-y-3 rounded-md border border-slate-200 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-sm font-medium text-slate-800">Units for {selectedItemCode}</div>
              <div className="text-xs text-slate-500">{selectedItem?.item_name || ""}</div>
            </div>
            <div className="text-sm text-slate-600">
              Selected: {selectedUnitIds.size}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100 text-left text-slate-700">
                <tr>
                  <th className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={allUnassignedSelected}
                      onChange={toggleSelectAllUnassigned}
                      disabled={unassignedVisible.length === 0}
                    />
                  </th>
                  <th className="px-3 py-2">#</th>
                  {(selectedItem?.serial_labels || ["Serial Number"]).map((label) => (
                    <th key={label} className="px-3 py-2">{label}</th>
                  ))}
                  <th className="px-3 py-2">Warranty Status</th>
                  <th className="px-3 py-2">Free Service</th>
                  <th className="px-3 py-2">Paid Service</th>
                  <th className="px-3 py-2">Part Warranty</th>
                  <th className="px-3 py-2">Assigned Engineer</th>
                  <th className="px-3 py-2">Billing</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {visibleUnits.map((unit, idx) => {
                  const isAssigned = Boolean(unit.assigned_engineer_id);
                  return (
                    <tr key={unit.id} className={isAssigned ? "bg-slate-50" : ""}>
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={selectedUnitIds.has(unit.id)}
                          disabled={isAssigned}
                          onChange={() => toggleUnit(unit.id)}
                        />
                      </td>
                      <td className="px-3 py-2">{idx + 1}</td>
                      {(unit.serial_values?.length ? unit.serial_values : [unit.serial_no]).map((value, colIdx) => (
                        <td key={colIdx} className="px-3 py-2">{serialCell(value)}</td>
                      ))}
                      <td className="px-3 py-2"><WarrantyBadge value={unit.warranty_status} /></td>
                      <td className="px-3 py-2 text-center">{unit.free_service_count ?? "—"}</td>
                      <td className="px-3 py-2 text-center">{unit.paid_service_count ?? "—"}</td>
                      <td className="px-3 py-2"><WarrantyBadge value={unit.part_warranty_status} /></td>
                      <td className="px-3 py-2">{unit.assigned_engineer_name || "—"}</td>
                      <td className="px-3 py-2">{unit.admin_billing_type || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <EngineerSelect engineers={engineers} value={assignEngineerId} onChange={(e) => setAssignEngineerId(e.target.value)} emptyLabel="— Choose engineer —" selectClassName="rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <select
              value={assignBillingType}
              onChange={(e) => setAssignBillingType(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="Free">Free service</option>
              <option value="Paid">Paid service</option>
            </select>
            <textarea
              value={assignRemarks}
              onChange={(e) => setAssignRemarks(e.target.value)}
              rows={2}
              placeholder="Assignment remarks"
              className="rounded-md border border-slate-300 px-3 py-2 text-sm md:col-span-1"
            />
          </div>
          <p className="text-xs text-slate-500">{ENGINEER_ASSIGNMENT_HINT}</p>
          <button
            type="button"
            onClick={assignSelectedUnits}
            disabled={!assignEngineerId || selectedUnitIds.size === 0}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            Assign Engineer ({selectedUnitIds.size})
          </button>
        </div>
      )}
    </section>
  );
}
