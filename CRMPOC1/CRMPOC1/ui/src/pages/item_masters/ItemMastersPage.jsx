import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import ItemMasterList from "./ItemMasterList.jsx";
import SparePartsCatalogue from "./SparePartsCatalogue.jsx";
import PartsApprovals from "./PartsApprovals.jsx";

const APPROVAL_ROLES = new Set(["admin", "incool", "sub_admin", "service_manager", "service", "indcool", "indcool service", "indcool_service"]);

function roleKey(role) {
  return (role || "").trim().toLowerCase();
}

export default function ItemMastersPage() {
  const { user } = useAuth();
  const canSeeApprovals = APPROVAL_ROLES.has(roleKey(user?.role));
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "approvals" && canSeeApprovals ? "approvals" : "items";
  const [tab, setTab] = useState(initialTab);

  const tabs = [
    ["items", "Items"],
    ["catalogue", "Spare parts"],
    ...(canSeeApprovals ? [["approvals", "Approvals"]] : []),
  ];

  return (
    <div className="space-y-4">
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
      {tab === "items" && <ItemMasterList />}
      {tab === "catalogue" && <SparePartsCatalogue />}
      {tab === "approvals" && canSeeApprovals && <PartsApprovals />}
    </div>
  );
}
