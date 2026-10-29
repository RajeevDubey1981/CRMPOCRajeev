import { useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import { canActOnInstallationPayments, isSystemAdminRole } from "../../utils/roles.js";
import AccountsDashboard from "./AccountsDashboard.jsx";
import AuditQueue from "./AuditQueue.jsx";
import LedgerSearch from "./LedgerSearch.jsx";
import MyVendorExpenseRequests from "./MyVendorExpenseRequests.jsx";
import ReadyToPayQueue from "./ReadyToPayQueue.jsx";

/** One landing spot for the vendor/engineer account system. Which tabs show depend on the
 * vendor_ledger/engineer_ledger permissions (Admin -> Roles) -- Accounts/Admin/Sub Admin get all three,
 * Sales typically just Vendors, Service Team/Manager just Engineers. */
export default function LedgerPage() {
  const { user } = useAuth();
  const isSystemAdmin = isSystemAdminRole(user?.role);
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const has = (module, flag) => isSystemAdmin || permissions.some((p) => p.module === module && p[flag]);

  const canSeeVendors = has("vendor_ledger", "can_view");
  const canSeeEngineers = has("engineer_ledger", "can_view");
  const canSeeDashboard = has("vendor_ledger", "can_edit") || has("engineer_ledger", "can_edit");
  const canSeeAudit = has("ledger_audit", "can_view");
  // Anyone who can raise a vendor-expense approval (Sales, Service Team) gets a "My Requests" tab --
  // same check the backend uses (orders can_view, never a vendor/engineer account itself).
  const role = (user?.role || "").toLowerCase();
  const canSeeMyRequests = role !== "vendor" && role !== "engineer" && has("orders", "can_view");
  // Ready to Pay: whoever can act somewhere in the installation/service payment chains -- the same
  // check the backend's ready-to-pay endpoint uses -- not tied to the vendor/engineer ledger
  // permissions above, since it's a different system (order payments, not ledger accounts).
  const canSeePayQueue = canActOnInstallationPayments(role);

  const [searchParams] = useSearchParams();
  const requested = searchParams.get("tab");
  const defaultTab = canSeeDashboard ? "dashboard" : canSeePayQueue ? "pay" : canSeeVendors ? "vendors" : canSeeEngineers ? "engineers" : canSeeAudit ? "audit" : "mine";
  const initialTab = ["dashboard", "pay", "vendors", "engineers", "audit", "mine"].includes(requested) ? requested : defaultTab;
  const [tab, setTab] = useState(initialTab);

  if (!canSeeVendors && !canSeeEngineers && !canSeeDashboard && !canSeeAudit && !canSeeMyRequests && !canSeePayQueue) {
    return <Navigate to="/dashboard" replace />;
  }

  const tabs = [
    ...(canSeeDashboard ? [["dashboard", "Dashboard"]] : []),
    ...(canSeePayQueue ? [["pay", "Ready to Pay"]] : []),
    ...(canSeeVendors ? [["vendors", "Vendors"]] : []),
    ...(canSeeEngineers ? [["engineers", "Engineers"]] : []),
    ...(canSeeAudit ? [["audit", "Audit"]] : []),
    ...(canSeeMyRequests ? [["mine", "My Requests"]] : []),
  ];
  const activeTab = tabs.some(([k]) => k === tab) ? tab : tabs[0]?.[0];

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
                activeTab === key ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      )}
      {activeTab === "dashboard" && canSeeDashboard && <AccountsDashboard />}
      {activeTab === "pay" && canSeePayQueue && <ReadyToPayQueue />}
      {activeTab === "vendors" && canSeeVendors && <LedgerSearch partyType="vendor" />}
      {activeTab === "engineers" && canSeeEngineers && <LedgerSearch partyType="engineer" />}
      {activeTab === "audit" && canSeeAudit && <AuditQueue />}
      {activeTab === "mine" && canSeeMyRequests && <MyVendorExpenseRequests />}
    </div>
  );
}
