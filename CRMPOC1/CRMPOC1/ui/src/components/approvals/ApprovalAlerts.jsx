import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { partsApi } from "../../api/parts.js";
import { servicesApi } from "../../api/services.js";
import { shortageClaimsApi } from "../../api/shortageClaims.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { canApproveServiceUnits, canForwardServiceUnits, roleKey } from "../../utils/roles.js";

const APPROVAL_ROLES = new Set(["admin", "incool", "sub_admin", "service_manager", "service", "indcool", "indcool service", "indcool_service"]);
const POLL_MS = 45000;

function beep() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    [880, 660].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      osc.connect(gain);
      gain.connect(ctx.destination);
      const t = ctx.currentTime + i * 0.11;
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.exponentialRampToValueAtTime(0.18, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
      osc.start(t);
      osc.stop(t + 0.18);
    });
  } catch {
    // audio can fail silently (no gesture yet, no AudioContext support) — the popup still shows
  }
}

// Polls for new parts requests / missing-item claims waiting on this user and pops an alert card
// bottom-right (the CRM's existing toast spot) with a sound, no matter which screen they're on.
export default function ApprovalAlerts() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const canSeeApprovals = APPROVAL_ROLES.has((user?.role || "").trim().toLowerCase());
  const canForwardUnits = canForwardServiceUnits(user?.role);
  const canApproveUnits = canApproveServiceUnits(user?.role);
  const isEngineer = roleKey(user?.role) === "engineer";
  const canReceiveAlerts = canSeeApprovals || isEngineer;
  const [alerts, setAlerts] = useState([]);
  const seenRef = useRef(null); // null until the first poll has set a baseline

  const poll = useCallback(async () => {
    try {
      const [parts, claims, reviewUnits] = await Promise.all([
        partsApi.requests({ mine: true }).catch(() => []),
        shortageClaimsApi.list({}).catch(() => []),
        (canForwardUnits || canApproveUnits) ? servicesApi.reviewUnits().catch(() => []) : Promise.resolve([]),
      ]);
      const pending = [
        ...parts.filter((r) => r.can_act && (r.stage === "svm" || r.stage === "sub")).map((r) => ({
          key: `part-${r.id}`, kind: "parts request", no: r.request_no,
          what: r.part_name_cache || r.crm_item_name_cache || r.description || "Request",
          by: r.crm_raised_by_name, href: "/items?tab=approvals",
          // A request raised against a service job is time-sensitive (the job is waiting on it) —
          // alert for it even on the very first poll of the session, not only once it's "new".
          alwaysAlert: !!r.crm_service_request_id,
        })),
        ...claims.filter((c) => c.can_act && (c.stage === "svm" || c.stage === "sub")).map((c) => ({
          key: `claim-${c.id}`, kind: "missing-item claim", no: c.claim_no,
          what: c.description || "Claim", by: c.raised_by_name, href: "/claims",
        })),
        // Service Team's own forward duty, and Service Manager/Admin's approval duty, for the
        // per-serial service-unit chain — previously this queue was never polled at all.
        ...reviewUnits.filter((u) => canForwardUnits && u.unit_status === "Pending Service Team Review").map((u) => ({
          key: `svc-fwd-${u.unit_id}`, kind: "service recommendation", no: u.request_no,
          what: u.recommended_action || u.problem_found || `Serial ${u.serial_no}`,
          by: u.customer_name, href: `/services/${u.service_id}`,
        })),
        ...reviewUnits.filter((u) => canApproveUnits && u.unit_status === "Pending Service Approval").map((u) => ({
          key: `svc-apr-${u.unit_id}`, kind: "service approval", no: u.request_no,
          what: u.recommended_action || u.problem_found || `Serial ${u.serial_no}`,
          by: u.customer_name, href: `/services/${u.service_id}`,
        })),
        // FYI-only notices: nothing to decide, just "this got rejected" — the engineer about
        // their own part request, Service Team about a recommendation they forwarded.
        ...parts.filter((r) => isEngineer && r.stage === "rejected").map((r) => ({
          key: `part-rejected-${r.id}`, kind: "parts request", no: r.request_no,
          what: r.part_name_cache || r.crm_item_name_cache || r.description || "Request",
          by: null, href: "/items/my-requests", tone: "rejected",
        })),
        ...reviewUnits.filter((u) => canForwardUnits && u.unit_status === "Rejected").map((u) => ({
          key: `svc-rej-${u.unit_id}`, kind: "service recommendation", no: u.request_no,
          what: u.recommended_action || u.problem_found || `Serial ${u.serial_no}`,
          by: null, href: `/services/${u.service_id}`, tone: "rejected",
        })),
      ];

      if (seenRef.current === null) {
        seenRef.current = new Set(pending.map((p) => p.key));
        const alwaysFresh = pending.filter((p) => p.alwaysAlert);
        if (alwaysFresh.length > 0) {
          beep();
          setAlerts((prev) => [...prev, ...alwaysFresh.map((f) => ({ ...f, id: `${f.key}-${Date.now()}` }))]);
        }
        return;
      }
      const fresh = pending.filter((p) => !seenRef.current.has(p.key));
      seenRef.current = new Set(pending.map((p) => p.key));
      if (fresh.length === 0) return;

      beep();
      setAlerts((prev) => [...prev, ...fresh.map((f) => ({ ...f, id: `${f.key}-${Date.now()}` }))]);
    } catch {
      // keep the app usable even if a poll fails
    }
  }, [canForwardUnits, canApproveUnits, isEngineer]);

  function dismiss(id) {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  useEffect(() => {
    if (!canReceiveAlerts) return;
    seenRef.current = null;
    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => clearInterval(timer);
  }, [canReceiveAlerts, poll]);

  // auto-dismiss each card 8s after it actually renders, keyed by its own id
  useEffect(() => {
    if (alerts.length === 0) return;
    const timers = alerts.map((a) => setTimeout(() => dismiss(a.id), 8000));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts.length]);

  if (!canReceiveAlerts || alerts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2.5">
      {alerts.map((a) => {
        const rejected = a.tone === "rejected";
        return (
          <div
            key={a.id}
            className={`s-pop relative overflow-hidden rounded-xl border p-3.5 shadow-2xl ${
              rejected ? "border-rose-200 bg-gradient-to-br from-white to-rose-50" : "border-violet-200 bg-gradient-to-br from-white to-violet-50"
            }`}
          >
            <span className={`absolute inset-y-0 left-0 w-1 ${rejected ? "bg-gradient-to-b from-rose-600 to-amber-500" : "bg-gradient-to-b from-violet-600 to-amber-500"}`} />
            <div className="flex items-center gap-2.5">
              <span className={`q-bell grid h-8 w-8 shrink-0 place-items-center rounded-full text-white ${rejected ? "bg-gradient-to-br from-rose-600 to-amber-500" : "bg-gradient-to-br from-violet-600 to-fuchsia-500"}`}>
                {rejected ? "⚠️" : "🔔"}
              </span>
              <span className={`text-xs font-extrabold uppercase tracking-wide ${rejected ? "text-rose-700" : "text-violet-700"}`}>
                {rejected ? `${a.kind} rejected` : `New ${a.kind} — waiting on you`}
              </span>
              <button type="button" aria-label="Dismiss" onClick={() => dismiss(a.id)} className={`ml-auto ${rejected ? "text-rose-300 hover:text-rose-600" : "text-violet-300 hover:text-violet-600"}`}>✕</button>
            </div>
            <div className="mt-1.5 text-sm text-slate-700">
              <b className="text-indcool-navy">{a.no}</b> — {a.what}
              <br />
              {rejected ? "Rejected just now." : `Raised by ${a.by || "someone"}, just now.`}
            </div>
            <div className="mt-2.5 flex gap-2">
              <button
                type="button"
                onClick={() => { navigate(a.href); dismiss(a.id); }}
                className={`flex-1 rounded-md py-1.5 text-xs font-bold text-white hover:opacity-90 ${
                  rejected ? "bg-gradient-to-br from-rose-600 to-amber-500" : "bg-gradient-to-br from-violet-600 to-fuchsia-500"
                }`}
              >
                {rejected ? "View" : "View & decide"}
              </button>
              <button type="button" onClick={() => dismiss(a.id)} className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">Later</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
