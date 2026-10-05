import { useEffect, useState } from "react";

import { installationsApi } from "../../api/installations.js";
import { formatApiError } from "../../utils/apiError.js";
import ScanInput from "../scan/ScanInput.jsx";
import FieldPhotos from "../fieldphoto/FieldPhotos.jsx";
import WorkflowStepSection from "./WorkflowStepSection.jsx";

const emptySerialLine = () => ({
  serial_no: "",
  serial_no_2: "",
  observation: "",
});

function Field({ label, value, mono = false }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>{value || "—"}</div>
    </div>
  );
}

export default function InstallationEngineerSerialWorkflow({
  installationId,
  installationStatus,
  assignedEngineerId,
  serialVerifiedAt,
  engineerSiteRemarks,
  isEngineer,
  isAdminLike,
  userId,
  onUpdated,
  onError,
  onBusy,
  showAdminVerify = true,
  workflowSteps = null,
}) {
  const [serials, setSerials] = useState([]);
  const [engineerForm, setEngineerForm] = useState({
    site_remarks: engineerSiteRemarks || "",
    lines: [emptySerialLine()],
  });
  const [verifyForm, setVerifyForm] = useState({
    billing_type: "Free",
    overall_remark: "",
    lineDecisions: {},
  });

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

  const canEngineerSubmit = isEngineer
    && assignedEngineerId === userId
    && !serialVerifiedAt
    && ["Assigned", "In Progress", "Serial Pending Verification"].includes(installationStatus);

  const canAdminVerify = isAdminLike && installationStatus === "Serial Pending Verification" && serials.length > 0;

  useEffect(() => {
    if (!installationId) return;
    installationsApi.engineerSerials(installationId)
      .then((rows) => {
        setSerials(rows);
        const decisions = {};
        rows.forEach((row) => {
          decisions[row.id] = {
            decision: row.verification_status === "Rejected" ? "reject" : "approve",
            admin_remark: row.admin_remark || "",
          };
        });
        setVerifyForm((current) => ({ ...current, lineDecisions: decisions }));
        if (rows.length > 0 && canEngineerSubmit) {
          setEngineerForm((current) => ({
            ...current,
            site_remarks: engineerSiteRemarks || current.site_remarks,
            lines: rows.map((row) => ({
              serial_no: row.serial_no || "",
              serial_no_2: row.serial_no_2 || "",
              observation: row.observation || "",
            })),
          }));
        }
      })
      .catch(() => setSerials([]));
  }, [installationId, installationStatus, serialVerifiedAt, engineerSiteRemarks, canEngineerSubmit]);

  async function run(action) {
    onBusy?.(true);
    onError?.("");
    try {
      await action();
      onUpdated?.();
    } catch (error) {
      onError?.(formatApiError(error, "Action failed"));
    } finally {
      onBusy?.(false);
    }
  }

  function updateLine(index, field, value) {
    setEngineerForm((current) => ({
      ...current,
      lines: current.lines.map((line, lineIndex) => (
        lineIndex === index ? { ...line, [field]: value } : line
      )),
    }));
  }

  function addSerialLine() {
    setEngineerForm((current) => ({
      ...current,
      lines: [...current.lines, emptySerialLine()],
    }));
  }

  function removeSerialLine(index) {
    setEngineerForm((current) => ({
      ...current,
      lines: current.lines.length === 1
        ? [emptySerialLine()]
        : current.lines.filter((_, lineIndex) => lineIndex !== index),
    }));
  }

  const step5 = workflowSteps?.steps?.[5];
  const step6 = workflowSteps?.steps?.[6];

  if (!installationId) return null;

  return (
    <div className="space-y-4">
      {(canEngineerSubmit || step5?.done || (isAdminLike && !serialVerifiedAt)) && (
        <WorkflowStepSection
          title="Step 5 — Engineer site visit & serial numbers"
          done={Boolean(step5?.done)}
          locked={Boolean(step5?.locked) || (!canEngineerSubmit && !step5?.done)}
          borderClass="border-amber-200"
          bgClass="bg-white"
          summary={step5?.done
            ? (engineerSiteRemarks
              ? `Serials submitted. Site remarks: ${engineerSiteRemarks}`
              : "Engineer submitted serial numbers for admin verification.")
            : "Waiting for the assigned engineer to submit serial numbers from site."}
        >
          <div className="mt-3 space-y-3">
            {engineerForm.lines.map((line, index) => (
              <div key={`serial-line-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-600">
                    Serial #{index + 1}
                  </div>
                  {engineerForm.lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSerialLine(index)}
                      className="text-xs text-rose-700 underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <ScanInput
                    value={line.serial_no}
                    onValue={(value) => updateLine(index, "serial_no", value)}
                    placeholder="Serial number"
                    className={fieldClass}
                  />
                  <ScanInput
                    value={line.serial_no_2}
                    onValue={(value) => updateLine(index, "serial_no_2", value)}
                    placeholder="Serial number 2 (optional)"
                    className={fieldClass}
                  />
                  <input
                    value={line.observation}
                    onChange={(e) => updateLine(index, "observation", e.target.value)}
                    placeholder="Observation for this unit"
                    className={`${fieldClass} md:col-span-2`}
                  />
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={addSerialLine}
            className="mt-3 rounded-md border border-amber-300 px-3 py-2 text-sm text-amber-900"
          >
            + Add another serial number
          </button>
          <div className="mt-3">
            <label className="text-xs uppercase tracking-wide text-slate-500">Overall site remarks</label>
            <textarea
              rows={3}
              value={engineerForm.site_remarks}
              onChange={(e) => setEngineerForm((current) => ({ ...current, site_remarks: e.target.value }))}
              placeholder="Overall observation from customer site"
              className={`${fieldClass} mt-1`}
            />
          </div>
          <button
            type="button"
            onClick={() => run(() => installationsApi.submitEngineerSerials(installationId, {
              site_remarks: engineerForm.site_remarks,
              serials: engineerForm.lines.map((line) => ({
                ...line,
                unit_status: "Installed",
              })),
            }))}
            className="mt-3 rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white"
          >
            Submit serials & observations
          </button>
        </WorkflowStepSection>
      )}

      {serials.length > 0 && (
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <div className="text-sm font-medium text-slate-800">Submitted serial details</div>
          {engineerSiteRemarks && (
            <p className="mt-2 text-sm text-slate-700">
              <span className="font-medium">Site remarks:</span> {engineerSiteRemarks}
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2">#</th>
                  <th className="px-2 py-2">Serial</th>
                  <th className="px-2 py-2">Serial 2</th>
                  <th className="px-2 py-2">Unit status</th>
                  <th className="px-2 py-2">Observation</th>
                  <th className="px-2 py-2">Verification</th>
                  <th className="px-2 py-2">Photos</th>
                </tr>
              </thead>
              <tbody>
                {serials.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="px-2 py-2">{row.line_no}</td>
                    <td className="px-2 py-2 font-mono">{row.serial_no}</td>
                    <td className="px-2 py-2 font-mono">{row.serial_no_2 || "—"}</td>
                    <td className="px-2 py-2">{row.unit_status || "—"}</td>
                    <td className="px-2 py-2">{row.observation || "—"}</td>
                    <td className="px-2 py-2">{row.verification_status}</td>
                    <td className="px-2 py-2">
                      <FieldPhotos
                        kind="installation-serials"
                        id={row.id}
                        serialNo={row.serial_no}
                        canAdd={Boolean(isEngineer) && Number(assignedEngineerId) === Number(userId)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(showAdminVerify && (canAdminVerify || step6?.done || (isAdminLike && Boolean(step5?.done) && !serialVerifiedAt))) && (
        <WorkflowStepSection
          title="Step 6 — Admin verify serial numbers"
          done={Boolean(step6?.done)}
          locked={Boolean(step6?.locked)}
          borderClass="border-indigo-200"
          summary={serialVerifiedAt
            ? `Serial numbers verified.${engineerSiteRemarks ? ` Billing type recorded.` : ""}`
            : "Serial verification completed."}
        >
          <p className="text-xs text-indigo-800">
            Review each engineer-submitted serial and approve or reject. Approved serials are matched to order item codes automatically and split into separate installation requests when needed.
          </p>
          <div className="mt-3 space-y-3">
            {serials.map((row) => (
              <div key={row.id} className="rounded-md border border-slate-200 p-3">
                <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
                  <Field label="Serial" value={row.serial_no} mono />
                  <Field label="Serial 2" value={row.serial_no_2} mono />
                  <Field label="Unit status" value={row.unit_status} />
                  <Field label="Observation" value={row.observation} />
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                  <select
                    value={verifyForm.lineDecisions[row.id]?.decision || "approve"}
                    onChange={(e) => setVerifyForm((current) => ({
                      ...current,
                      lineDecisions: {
                        ...current.lineDecisions,
                        [row.id]: {
                          ...current.lineDecisions[row.id],
                          decision: e.target.value,
                        },
                      },
                    }))}
                    className={fieldClass}
                  >
                    <option value="approve">Approve</option>
                    <option value="reject">Reject</option>
                  </select>
                  <input
                    value={verifyForm.lineDecisions[row.id]?.admin_remark || ""}
                    onChange={(e) => setVerifyForm((current) => ({
                      ...current,
                      lineDecisions: {
                        ...current.lineDecisions,
                        [row.id]: {
                          ...current.lineDecisions[row.id],
                          admin_remark: e.target.value,
                        },
                      },
                    }))}
                    placeholder="Remark for this serial"
                    className={fieldClass}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            <select
              value={verifyForm.billing_type}
              onChange={(e) => setVerifyForm((current) => ({ ...current, billing_type: e.target.value }))}
              className={fieldClass}
            >
              <option value="Free">Free installation</option>
              <option value="Paid">Paid installation</option>
            </select>
          </div>
          <p className="mt-2 text-xs text-slate-600">
            Payment amount is requested by the engineer after installation is completed.
          </p>
          <textarea
            rows={2}
            value={verifyForm.overall_remark}
            onChange={(e) => setVerifyForm((current) => ({ ...current, overall_remark: e.target.value }))}
            placeholder="Overall verification remarks"
            className={`${fieldClass} mt-2`}
          />
          <button
            type="button"
            onClick={() => run(() => installationsApi.finalizeEngineerSerials(installationId, {
              lines: serials.map((row) => ({
                serial_id: row.id,
                decision: verifyForm.lineDecisions[row.id]?.decision || "approve",
                admin_remark: verifyForm.lineDecisions[row.id]?.admin_remark || "",
              })),
              billing_type: verifyForm.billing_type,
              overall_remark: verifyForm.overall_remark,
            }))}
            className="mt-3 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white"
          >
            Verify serial numbers
          </button>
        </WorkflowStepSection>
      )}

      {serialVerifiedAt && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Serial numbers verified. Installation can continue in the standard workflow.
        </div>
      )}
    </div>
  );
}
