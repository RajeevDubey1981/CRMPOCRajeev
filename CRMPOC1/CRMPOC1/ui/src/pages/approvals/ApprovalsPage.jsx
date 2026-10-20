import { useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { isSystemAdminRole } from "../../utils/roles.js";
import ServiceReviewsPage from "../services/ServiceReviewsPage.jsx";
import PartsApprovals from "../item_masters/PartsApprovals.jsx";

// Same role set PartsApprovals itself has always used, independent of the "items" module permission.
const PARTS_APPROVAL_ROLES = new Set(["admin", "incool", "sub_admin", "service_manager", "service", "indcool", "indcool service", "indcool_service"]);

function roleKey(role) {
  return (role || "").trim().toLowerCase();
}

/**
 * One landing spot for everything that needs a decision: service-unit recommendations (Service tab, the
 * old Service Reviews page) and parts/item requests (Parts tab, the old Approvals tab under Item Masters).
 * Each tab still opens its own existing screen/modal to actually act — this only merges where you land.
 */
export default function ApprovalsPage() {
  const { user } = useAuth();
  const isSystemAdmin = isSystemAdminRole(user?.role);
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const canSeeService = isSystemAdmin || permissions.some((p) => p.module === "services" && p.can_view);
  const canSeeParts = PARTS_APPROVAL_ROLES.has(roleKey(user?.role));

  const [searchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") === "parts" ? "parts" : "service";
  const initialTab = requestedTab === "parts" && !canSeeParts ? "service" : requestedTab === "service" && !canSeeService ? "parts" : requestedTab;
  const [tab, setTab] = useState(initialTab);

  if (!canSeeService && !canSeeParts) {
    return <Navigate to="/dashboard" replace />;
  }

  const tabs = [
    ...(canSeeService ? [["service", "Service"]] : []),
    ...(canSeeParts ? [["parts", "Parts"]] : []),
  ];

  return (
    <div className="space-y-4">
      {tabs.length > 1 && (
        <nav className="flex flex-wrap gap-1 border-b border-slate-200 pb-2">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === key ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      )}
      {tab === "service" && canSeeService && <ServiceReviewsPage />}
      {tab === "parts" && canSeeParts && <PartsApprovals />}
    </div>
  );
}
